import os
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEATHER_KEY = os.getenv("WEATHER_KEY")
NEWS_KEY = os.getenv("NEWS_KEY")

# ---------- Погода ----------
def get_weather():
    try:
        if not WEATHER_KEY:
            return "Погода: API-ключ не задан ☁️"

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "Moscow,ru",
            "appid": WEATHER_KEY,
            "units": "metric",
            "lang": "ru"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return f"Погода недоступна ☁️ (код {response.status_code})"

        r = response.json()

        if "main" not in r:
            return "Погода временно недоступна ☁️"

        temp = round(r["main"]["temp"])
        feels = round(r["main"]["feels_like"])
        desc = r["weather"][0]["description"].capitalize()

        return f"{temp}°C, {desc}\nОщущается как {feels}°C"

    except Exception as e:
        return "Погода временно недоступна ☁️"

# ---------- Валюты ----------
def get_rates():
    fiat = requests.get(
        "https://api.exchangerate.host/latest?base=USD&symbols=RUB,EUR",
        timeout=10
    ).json()

    usd = round(fiat["rates"]["RUB"], 2)
    eur = round(usd / fiat["rates"]["EUR"], 2)

    btc = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub",
        timeout=10
    ).json()["bitcoin"]["rub"]

    return (
        f"USD — {usd} ₽\n"
        f"EUR — {eur} ₽\n"
        f"BTC — {btc:,} ₽".replace(",", " ")
    )

# ---------- Гороскоп ----------
def get_horoscope():
    r = requests.post(
        "https://aztro.sameerkumar.website/?sign=aries&day=today",
        timeout=10
    ).json()
    return r["description"]

# ---------- Новости ----------
def get_news():
    url = "https://gnews.io/api/v4/top-headlines"
    params = {
        "lang": "ru",
        "country": "ru",
        "max": 3,
        "token": NEWS_KEY
    }
    r = requests.get(url, params=params, timeout=10).json()

    titles = [f"{i+1}. {a['title']}" for i, a in enumerate(r.get("articles", []))]
    return "\n".join(titles) if titles else "Сегодня без громких новостей"

# ---------- Отправка ----------
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload, timeout=10)

# ---------- Главная логика ----------
def main():
    weather = get_weather()
    rates = get_rates()
    horoscope = get_horoscope()
    news = get_news()

    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"☀️ Доброе утро! ({today})\n\n"
        f"🌤 Москва:\n{weather}\n\n"
        f"💱 Курсы:\n{rates}\n\n"
        f"♈ Гороскоп:\n{horoscope}\n\n"
        f"🗞 Новости:\n{news}"
    )

    send_message(message)

if __name__ == "__main__":
    main()
