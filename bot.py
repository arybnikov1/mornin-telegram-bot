import os
import requests
from datetime import datetime

print("### FINAL VERSION OF BOT.PY ###")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEATHER_KEY = os.getenv("WEATHER_KEY")
NEWS_KEY = os.getenv("NEWS_KEY")


# ---------- Погода ----------
def get_weather():
    try:
        if not WEATHER_KEY:
            return "Погода недоступна ☁️"

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
            return "Погода недоступна ☁️"

        data = r.json()
        if "main" not in data:
            return "Погода недоступна ☁️"

        temp = round(data["main"]["temp"])
        feels = round(data["main"]["feels_like"])
        desc = data["weather"][0]["description"].capitalize()

        return f"{temp}°C, {desc}\nОщущается как {feels}°C"
    except Exception:
        return "Погода недоступна ☁️"


# ---------- Курсы ----------
def get_rates():
    try:
        cbr = requests.get(
            "https://www.cbr-xml-daily.ru/daily_json.js",
            timeout=10
        ).json()

        usd = round(cbr["Valute"]["USD"]["Value"], 2)
        eur = round(cbr["Valute"]["EUR"]["Value"], 2)

        btc_resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "rub"},
            timeout=10
        ).json()

        btc = btc_resp["bitcoin"]["rub"]

        return (
            f"USD — {usd} ₽\n"
            f"EUR — {eur} ₽\n"
            f"BTC — {btc:,} ₽".replace(",", " ")
        )
    except Exception:
        return "Курсы недоступны 💱"


# ---------- Гороскоп (стабильный вариант) ----------
def get_horoscope():
    try:
        r = requests.get(
            "https://ignio.com/rss/daily/com.xml",
            timeout=10
        )

        if r.status_code != 200:
            return "Сегодня полагайся на интуицию ✨"

        text = r.text
        start = text.find("<description>") + 13
        end = text.find("</description>")

        horoscope = text[start:end]
        horoscope = horoscope.replace("<![CDATA[", "").replace("]]>", "").strip()

        return horoscope[:400] + "…"
    except Exception:
        return "Сегодня хороший день для спокойных решений ✨"


# ---------- Новости ----------
def get_news():
    try:
        r = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={
                "lang": "ru",
                "country": "ru",
                "max": 3,
                "token": NEWS_KEY
            },
            timeout=10
        ).json()

        articles = r.get("articles", [])
        if not articles:
            return "Сегодня без громких новостей"

        return "\n".join(
            f"{i+1}. {a['title']}" for i, a in enumerate(articles)
        )
    except Exception:
        return "Новости недоступны 🗞"


# ---------- Telegram ----------
def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )


# ---------- Main ----------
def main():
    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"☀️ Доброе утро! ({today})\n\n"
        f"🌤 Москва:\n{get_weather()}\n\n"
        f"💱 Курсы:\n{get_rates()}\n\n"
        f"♈ Гороскоп:\n{get_horoscope()}\n\n"
        f"🗞 Новости:\n{get_news()}"
    )

    send_message(message)


if __name__ == "__main__":
    main()
