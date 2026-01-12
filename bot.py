import os
import requests
import re
from datetime import datetime
import xml.etree.ElementTree as ET

print("### FINAL BOT.PY v2 ###")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEATHER_KEY = os.getenv("WEATHER_KEY")

# ---------- Weather emoji ----------
def weather_emoji(desc: str) -> str:
    d = desc.lower()
    if "снег" in d:
        return "❄️"
    if "дожд" in d:
        return "🌧"
    if "ясно" in d:
        return "☀️"
    if "облач" in d:
        return "☁️"
    if "туман" in d:
        return "🌫"
    return "🌡"


# ---------- Weather (Moscow) ----------
def get_weather():
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": "Moscow,ru",
                "appid": WEATHER_KEY,
                "units": "metric",
                "lang": "ru"
            },
            timeout=10
        )

        if r.status_code != 200:
            return "🌡 Москва: погода недоступна"

        data = r.json()
        desc = data["weather"][0]["description"].capitalize()
        emoji = weather_emoji(desc)

        temp = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])

        return f"{emoji} Москва: {temp}°C, {desc}\nОщущается как {feels}°C"

    except Exception:
        return "🌡 Москва: погода недоступна"


# ---------- Rates ----------
def get_rates():
    try:
        # USD / EUR -> RUB
        cbr = requests.get(
            "https://www.cbr-xml-daily.ru/daily_json.js",
            timeout=10
        ).json()

        usd_rub = round(cbr["Valute"]["USD"]["Value"], 2)
        eur_rub = round(cbr["Valute"]["EUR"]["Value"], 2)

        # BTC -> USD
        btc_usd = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10
        ).json()["bitcoin"]["usd"]

        return (
            f"USD — {usd_rub} ₽\n"
            f"EUR — {eur_rub} ₽\n"
            f"BTC — {btc_usd:,} $".replace(",", " ")
        )

    except Exception:
        return "Курсы недоступны 💱"


# ---------- Horoscope (Capricorn only) ----------
def get_horoscope():
    try:
        r = requests.get(
            "https://horoscopes.mail.ru/rss/capricorn/today/",
            timeout=10
        )
        root = ET.fromstring(r.text)
        text = root.find(".//item/description").text
        return text.strip()[:500]
    except Exception:
        return "Сегодня для Козерогов важно сохранять спокойствие и фокус ♑"


# ---------- Helpers ----------
def normalize_title(title: str) -> set:
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    return set(title.split())


def is_similar(a: str, b: str) -> bool:
    wa = normalize_title(a)
    wb = normalize_title(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) > 0.5


def is_sport(title: str) -> bool:
    sport_words = [
        "спорт", "матч", "сыгра", "игра", "против",
        "чемпионат", "кубок", "лига", "кхл", "нхл",
        "рпл", "футбол", "хоккей", "баскетбол",
        "теннис", "гол", "счёт", "счет"
    ]
    t = title.lower()
    return any(w in t for w in sport_words)


# ---------- News (RIA + RBC, max 5) ----------
def get_news():
    try:
        news = []
        used_titles = []

        # --- RIA ---
        ria = requests.get(
            "https://ria.ru/export/rss2/archive/index.xml",
            timeout=10
        )
        ria_root = ET.fromstring(ria.text)
        for item in ria_root.findall(".//item"):
            if len(news) >= 5:
                break

            title = item.find("title").text.strip()
            if is_sport(title):
                continue

            if any(is_similar(title, t) for t in used_titles):
                continue

            link = item.find("link").text.strip()
            used_titles.append(title)
            news.append(f"{len(news)+1}. {title}\n{link}")

        # --- RBC ---
        rbc = requests.get(
            "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
            timeout=10
        )
        r_root = ET.fromstring(rbc.text)
        for item in r_root.findall(".//item"):
            if len(news) >= 5:
                break

            title = item.find("title").text.strip()
            if is_sport(title):
                continue

            if any(is_similar(title, t) for t in used_titles):
                continue

            link = item.find("link").text.strip()
            used_titles.append(title)
            news.append(f"{len(news)+1}. {title}\n{link}")

        return "🗞 **Главные новости:**\n" + "\n\n".join(news)

    except Exception:
        return "🗞 Новости временно недоступны"


# ---------- Telegram ----------
def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        },
        timeout=10
    )


# ---------- Main ----------
def main():
    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"☀️ Доброе утро! ({today})\n\n"
        f"{get_weather()}\n\n"
        f"💱 Курсы:\n{get_rates()}\n\n"
        f"♑ Гороскоп для Козерога:\n{get_horoscope()}\n\n"
        f"{get_news()}\n\n"
        f"— Утренний бот ☕"
    )

    send_message(message)


if __name__ == "__main__":
    main()
