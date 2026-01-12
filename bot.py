import os
import requests
from datetime import datetime
import xml.etree.ElementTree as ET

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEATHER_KEY = os.getenv("WEATHER_KEY")

# ---------- Weather emoji ----------
def weather_emoji(desc):
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


# ---------- Weather (Moscow строго) ----------
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

        usd = round(cbr["Valute"]["USD"]["Value"], 2)
        eur = round(cbr["Valute"]["EUR"]["Value"], 2)

        btc = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "rub"},
            timeout=10
        ).json()["bitcoin"]["rub"]

        return (
            f"USD — {usd} ₽\n"
            f"EUR — {eur} ₽\n"
            f"BTC — {btc:,} ₽".replace(",", " ")
        )
    except Exception:
        return "Курсы недоступны 💱"


# ---------- Horoscope (Mail.ru RSS) ----------
def get_horoscope():
    try:
        r = requests.get(
            "https://horoscopes.mail.ru/rss/overview/",
            timeout=10
        )
        root = ET.fromstring(r.text)
        text = root.find(".//item/description").text
        return text.strip()[:500]
    except Exception:
        return "Сегодня стоит доверять интуиции ✨"


# ---------- News: 3 news + links ----------
def get_news():
    try:
        r = requests.get(
            "https://news.yandex.ru/index.rss",
            timeout=10
        )
        root = ET.fromstring(r.text)
        items = root.findall(".//item")[:3]

        news_lines = []
        for i, item in enumerate(items, 1):
            title = item.find("title").text
            link = item.find("link").text
            news_lines.append(f"{i}. {title}\n{link}")

        return "\n\n".join(news_lines)

    except Exception:
        return "Новости недоступны 🗞"


# ---------- Telegram ----------
def send_message(text):
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "🔄 Обновить сейчас",
                "url": f"https://t.me/{BOT_TOKEN.split(':')[0]}"
            }
        ]]
    }

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": text,
            "reply_markup": keyboard
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
        f"♈ Гороскоп:\n{get_horoscope()}\n\n"
        f"🗞 Новости дня:\n{get_news()}\n\n"
        f"— Утренний бот ☕"
    )

    send_message(message)


if __name__ == "__main__":
    main()
