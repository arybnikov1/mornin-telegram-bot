import os
import sys
import requests
import logging
from datetime import datetime
from time import sleep
from typing import Callable
import xml.etree.ElementTree as ET

# ---------- Настройки ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEATHER_KEY = os.getenv("WEATHER_KEY")
CITY = os.getenv("CITY", "Moscow,ru")
ZODIAC_SIGN = os.getenv("ZODIAC_SIGN", "Козерог")

REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_NEWS_COUNT = 5

# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("morning_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- Проверка ENV ----------
def check_env():
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not CHAT_ID:
        missing.append("CHAT_ID")
    if not WEATHER_KEY:
        missing.append("WEATHER_KEY")

    if missing:
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}")
        sys.exit(1)

# ---------- Retry ----------
def retry_request(func: Callable):
    for attempt in range(MAX_RETRIES):
        try:
            return func()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Все попытки исчерпаны: {e}")
                raise
            logger.warning(f"Ошибка, повтор {attempt + 1}: {e}")
            sleep(RETRY_DELAY)

# ---------- Weather emoji ----------
def weather_emoji(desc: str) -> str:
    d = desc.lower()
    if "снег" in d or "snow" in d:
        return "❄️"
    if "дожд" in d or "rain" in d:
        return "🌧"
    if "ясно" in d or "clear" in d:
        return "☀️"
    if "облач" in d or "cloud" in d:
        return "☁️"
    if "туман" in d or "fog" in d:
        return "🌫"
    if "гроз" in d or "thunder" in d:
        return "⛈"
    return "🌡"

# ---------- Weather ----------
def get_weather() -> str:
    try:
        logger.info("Получение погоды...")

        def fetch():
            return requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": CITY,
                    "appid": WEATHER_KEY,
                    "units": "metric",
                    "lang": "ru"
                },
                timeout=REQUEST_TIMEOUT
            ).json()

        r = retry_request(fetch)

        desc = r["weather"][0]["description"].capitalize()
        emoji = weather_emoji(desc)
        temp = round(r["main"]["temp"])
        feels = round(r["main"]["feels_like"])
        city = r["name"]

        return f"{emoji} {city}: {temp}°C, {desc}\nОщущается как {feels}°C"

    except Exception as e:
        logger.error(f"Ошибка погоды: {e}")
        return f"🌡 {CITY.split(',')[0]}: погода недоступна"

# ---------- Rates ----------
def format_number(num: float, decimals: int = 2) -> str:
    return f"{num:,.{decimals}f}".replace(",", " ")

def get_rates() -> str:
    try:
        logger.info("Получение курсов...")

        def fetch_cbr():
            return requests.get(
                "https://www.cbr-xml-daily.ru/daily_json.js",
                timeout=REQUEST_TIMEOUT
            ).json()

        cbr = retry_request(fetch_cbr)
        usd = cbr["Valute"]["USD"]["Value"]
        eur = cbr["Valute"]["EUR"]["Value"]

        def fetch_btc():
            return requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
                timeout=REQUEST_TIMEOUT
            ).json()

        btc = retry_request(fetch_btc)["bitcoin"]["usd"]

        return (
            f"USD — {format_number(usd)} ₽\n"
            f"EUR — {format_number(eur)} ₽\n"
            f"BTC — {format_number(btc, 0)} $"
        )

    except Exception as e:
        logger.error(f"Ошибка курсов: {e}")
        return "Курсы недоступны 💱"

# ---------- Horoscope (Aztro API) ----------
def get_horoscope() -> str:
    try:
        logger.info(f"Получение гороскопа для {ZODIAC_SIGN}...")

        zodiac_map = {
            "Овен": "aries",
            "Телец": "taurus",
            "Близнецы": "gemini",
            "Рак": "cancer",
            "Лев": "leo",
            "Дева": "virgo",
            "Весы": "libra",
            "Скорпион": "scorpio",
            "Стрелец": "sagittarius",
            "Козерог": "capricorn",
            "Водолей": "aquarius",
            "Рыбы": "pisces"
        }

        sign = zodiac_map.get(ZODIAC_SIGN, "capricorn")

        def fetch():
            r = requests.post(
                f"https://aztro.sameerkumar.website/?sign={sign}&day=today",
                timeout=REQUEST_TIMEOUT
            )
            r.raise_for_status()
            return r.json()

        data = retry_request(fetch)
        text = data.get("description")

        if not text:
            raise ValueError("Пустой ответ API")

        return text

    except Exception as e:
        logger.error(f"Ошибка гороскопа: {e}")
        return "Сегодня день для спокойных и взвешенных решений ⭐"

# ---------- Helpers ----------
def is_sport(title: str) -> bool:
    words = [
        "спорт", "матч", "игра", "чемпионат", "кубок",
        "футбол", "хоккей", "баскетбол", "теннис",
        "победа", "поражение", "счёт", "счет"
    ]
    t = title.lower()
    return any(w in t for w in words)

def escape_markdown(text: str) -> str:
    for ch in ["_", "*", "[", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return text

# ---------- News ----------
def get_news() -> str:
    try:
        logger.info("Получение новостей...")

        def fetch():
            return requests.get(
                "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
                timeout=REQUEST_TIMEOUT
            )

        r = retry_request(fetch)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")

        news = []
        for item in items:
            if len(news) >= MAX_NEWS_COUNT:
                break

            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()

            if not title or not link or is_sport(title):
                continue

            news.append(f"*{escape_markdown(title)}*\n{link}")

        if not news:
            return "🗞 Новостей пока нет"

        return "🗞 *Новости (РБК):*\n\n" + "\n\n".join(news)

    except Exception as e:
        logger.error(f"Ошибка новостей: {e}")
        return "🗞 Новости временно недоступны"

# ---------- Telegram ----------
def send_message(text: str) -> bool:
    try:
        logger.info("Отправка сообщения...")

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=REQUEST_TIMEOUT
        )
        r.raise_for_status()
        return r.json().get("ok", False)

    except Exception as e:
        logger.error(f"Ошибка Telegram: {e}")
        return False

# ---------- Main ----------
def main():
    logger.info("=== Запуск утреннего бота ===")
    check_env()

    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"☀️ *Доброе утро!* ({today})\n\n"
        f"{get_weather()}\n\n"
        f"💱 *Курсы:*\n{get_rates()}\n\n"
        f"♑ *Гороскоп для {ZODIAC_SIGN}:*\n{get_horoscope()}\n\n"
        f"{get_news()}\n"
    )

    if send_message(message):
        logger.info("=== Бот успешно завершил работу ===")
    else:
        logger.error("=== Ошибка отправки сообщения ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
