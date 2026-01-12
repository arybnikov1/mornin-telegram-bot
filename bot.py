import os
import sys
import requests
import logging
from datetime import datetime
from typing import Optional
from time import sleep
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
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('morning_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------- Проверка переменных окружения ----------
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

# ---------- Retry wrapper ----------
def retry_request(func, *args, **kwargs):
    """Выполняет функцию с повторными попытками при ошибке"""
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"Все попытки исчерпаны для {func.__name__}: {e}")
                raise
            logger.warning(f"Попытка {attempt + 1} не удалась для {func.__name__}: {e}")
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
    if "туман" in d or "fog" in d or "mist" in d:
        return "🌫"
    if "гроз" in d or "thunder" in d:
        return "⛈"
    return "🌡"

# ---------- Weather ----------
def get_weather() -> str:
    try:
        logger.info("Получение погоды...")
        
        def fetch_weather():
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
        
        r = retry_request(fetch_weather)

        desc = r["weather"][0]["description"].capitalize()
        emoji = weather_emoji(desc)
        temp = round(r["main"]["temp"])
        feels = round(r["main"]["feels_like"])
        city_name = r["name"]

        logger.info(f"Погода получена: {temp}°C")
        return f"{emoji} {city_name}: {temp}°C, {desc}\nОщущается как {feels}°C"
    
    except Exception as e:
        logger.error(f"Ошибка получения погоды: {e}")
        return f"🌡 {CITY.split(',')[0]}: погода недоступна"

# ---------- Rates ----------
def format_number(num: float, decimals: int = 2) -> str:
    """Форматирует число с пробелами между тысячами"""
    formatted = f"{num:,.{decimals}f}".replace(",", " ")
    return formatted

def get_rates() -> str:
    try:
        logger.info("Получение курсов валют...")
        
        # Курсы рубля
        def fetch_cbr():
            return requests.get(
                "https://www.cbr-xml-daily.ru/daily_json.js",
                timeout=REQUEST_TIMEOUT
            ).json()
        
        cbr = retry_request(fetch_cbr)
        usd_rub = cbr["Valute"]["USD"]["Value"]
        eur_rub = cbr["Valute"]["EUR"]["Value"]

        # Bitcoin
        def fetch_btc():
            return requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
                timeout=REQUEST_TIMEOUT
            ).json()
        
        btc_data = retry_request(fetch_btc)
        btc_usd = btc_data["bitcoin"]["usd"]

        logger.info(f"Курсы получены: USD={usd_rub:.2f}")
        
        return (
            f"USD — {format_number(usd_rub)} ₽\n"
            f"EUR — {format_number(eur_rub)} ₽\n"
            f"BTC — {format_number(btc_usd, 0)} $"
        )
    
    except Exception as e:
        logger.error(f"Ошибка получения курсов: {e}")
        return "Курсы недоступны 💱"

# ---------- Horoscope ----------
def get_horoscope() -> str:
    """Получает реальный гороскоп с horo.mail.ru на русском языке"""
    # Соответствие знаков зодиака URL на horo.mail.ru
    zodiac_mapping = {
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
    
    sign_url = zodiac_mapping.get(ZODIAC_SIGN, "capricorn").lower()
    
    try:
        logger.info(f"Получение гороскопа для {ZODIAC_SIGN}...")
        
        def fetch_horoscope():
            response = requests.get(
                f"https://horo.mail.ru/prediction/{sign_url}/today/",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response.raise_for_status()
            return response.text
        
        html = retry_request(fetch_horoscope)
        
        # Парсим HTML для извлечения текста гороскопа
        # Ищем блок с основным текстом
        import re
        
        # Ищем текст гороскопа в разных возможных блоках
        patterns = [
            r'<div class="article__text[^>]*>(.*?)</div>',
            r'<div class="articleplaintext[^>]*>(.*?)</div>',
            r'<p class="Text[^>]*>(.*?)</p>',
        ]
        
        horoscope_text = None
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                # Берём первый найденный блок с текстом
                raw_text = matches[0]
                # Убираем HTML теги
                clean_text = re.sub(r'<[^>]+>', '', raw_text)
                # Убираем лишние пробелы и переносы
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                if len(clean_text) > 50:  # Проверяем, что это осмысленный текст
                    horoscope_text = clean_text
                    break
        
        if not horoscope_text:
            logger.warning("Не удалось распарсить гороскоп, пробуем альтернативный метод")
            # Пробуем найти любой длинный текст в параграфах
            all_paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            for para in all_paragraphs:
                clean = re.sub(r'<[^>]+>', '', para)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 100:
                    horoscope_text = clean
                    break
        
        if horoscope_text:
            logger.info(f"Гороскоп получен для {ZODIAC_SIGN}")
            return horoscope_text
        else:
            logger.error("Не удалось извлечь текст гороскопа")
            return "Гороскоп временно недоступен ⭐"
    
    except Exception as e:
        logger.error(f"Ошибка получения гороскопа: {e}")
        return "Гороскоп временно недоступен ⭐"

# ---------- Helpers ----------
def is_sport(title: str) -> bool:
    sport_words = [
        "спорт", "матч", "сыгра", "игра", "против",
        "чемпионат", "кубок", "лига", "кхл", "нхл",
        "рпл", "футбол", "хоккей", "баскетбол",
        "теннис", "гол", "счёт", "счет", "победа",
        "поражение", "ничья"
    ]
    t = title.lower()
    return any(w in t for w in sport_words)

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown (не MarkdownV2)"""
    # Для обычного Markdown нужно экранировать только эти символы
    special_chars = ['_', '*', '[', '`']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# ---------- News ----------
def get_news() -> str:
    try:
        logger.info("Получение новостей...")
        
        def fetch_news():
            return requests.get(
                "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
                timeout=REQUEST_TIMEOUT
            )
        
        rbc = retry_request(fetch_news)
        
        # Безопасный парсинг XML
        root = ET.fromstring(rbc.content)
        items = root.findall(".//item")

        news = []
        for item in items:
            if len(news) >= MAX_NEWS_COUNT:
                break

            title_elem = item.find("title")
            link_elem = item.find("link")
            
            if title_elem is None or link_elem is None:
                continue
                
            title = title_elem.text.strip() if title_elem.text else ""
            link = link_elem.text.strip() if link_elem.text else ""
            
            if not title or not link or is_sport(title):
                continue

            # Форматируем: жирный заголовок + ссылка на новой строке
            safe_title = escape_markdown(title)
            news.append(f"*{safe_title}*\n{link}")

        if not news:
            return "🗞 Новостей пока нет"

        logger.info(f"Получено {len(news)} новостей")
        return "🗞 **Новости \\(РБК\\):**\n\n" + "\n\n".join(news)

    except Exception as e:
        logger.error(f"Ошибка получения новостей: {e}")
        return "🗞 Новости временно недоступны"

# ---------- Telegram ----------
def send_message(text: str) -> bool:
    """Отправляет сообщение в Telegram. Возвращает True при успехе."""
    try:
        logger.info("Отправка сообщения в Telegram...")
        
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            logger.info("Сообщение успешно отправлено")
            return True
        else:
            logger.error(f"Telegram API вернул ошибку: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        # Логируем текст сообщения для отладки
        logger.error(f"Текст сообщения (первые 500 символов): {text[:500]}")
        return False

# ---------- Main ----------
def main():
    logger.info("=== Запуск утреннего бота ===")
    
    # Проверяем переменные окружения
    check_env()
    
    today = datetime.now().strftime("%d\\.%m\\.%Y")
    
    # Собираем части сообщения
    weather = get_weather()
    rates = get_rates()
    horoscope = get_horoscope()
    news = get_news()
    
    # Формируем итоговое сообщение
    message = (
        f"☀️ *Доброе утро\\!* \\({today}\\)\n\n"
        f"{escape_markdown(weather)}\n\n"
        f"💱 *Курсы:*\n{escape_markdown(rates)}\n\n"
        f"♑ *Гороскоп для {escape_markdown(ZODIAC_SIGN)}:*\n{escape_markdown(horoscope)}\n\n"
        f"{news}\n"
    )

    # Отправляем сообщение
    success = send_message(message)
    
    if success:
        logger.info("=== Бот успешно завершил работу ===")
    else:
        logger.error("=== Бот завершился с ошибками ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
