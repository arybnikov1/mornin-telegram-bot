import os
import requests
import re
from datetime import datetime
import xml.etree.ElementTree as ET

print("### FINAL STABLE BOT.PY ###")

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
        ).json()

        desc = r["weather"][0]["description"].capitalize()
        emoji = weather_emoji(desc)
        temp = round(r["main"]["temp"])
        feels = round(r["main"]["feels_like"])

        return f"{emoji} Москва: {temp}°C, {desc}\nОщущается как {feels}°C"
    except Exception:
        return "🌡 Москва: погода недоступна"

# ---------- Rates ----------
def get_rates():
    try:
        cbr = requests.get(
            "https://www.cbr-xml-daily.ru/daily_json.js",
            timeout=10
        ).json()

        usd_rub = round(cbr["Valute"]["USD"]["Value"], 2)
        eur_rub = round(cbr["Valute"]["EUR"]["Value"], 2)

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

# ---------- Horoscope (Capricorn, guaranteed) ----------
def get_horoscope():
    texts = [
        "Сегодня Козерогам важно не спешить и действовать последовательно.",
        "День подходит для планирования и спокойных разговоров.",
        "Хороший момент, чтобы закрыть старые вопросы.",
        "Сегодня стоит доверять логике, а не эмоциям.",
        "Возможны полезные идеи, если не отвлекаться на мелочи."
    ]
    return texts[datetime.now().day % len(texts)]

# ---------- Helpers ----------
def is_sport(title: str) -> bool:
    sport_words = [
        "спорт", "матч", "сыгра", "игра", "против",
        "чемпионат", "кубок", "лига", "кхл", "нхл",
        "рпл", "футбол", "хоккей", "баскетбол",
        "теннис", "гол", "счёт", "счет"
    ]
    t = title.lower()
    return any(w in t for w in sport_words)

# ---------- News (ONLY RBC, with links) ----------
def get_news():
    try:
        rbc = requests.get(
            "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
            timeout=10
        )

        root = ET.fromstring(rbc.text)
        items = root.findall(".//item")

        news = []
        for item in items:
            if len(news) >= 5:
                break

            title = item.find("title").text.strip()
            if is_sport(title):
                continue

            link = item.find("link").text.strip()
            news.append(f"{len(news)+1}. {title}\n{link}")

        return "🗞 **Новости (РБК):**\n" + "\n\n".join(news)

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
