import os
import requests
import re
from datetime import datetime
import xml.etree.ElementTree as ET

print("### FINAL BOT.PY ###")

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


# ---------- Helpers for news ----------
def normalize_title(title: str) -> set:
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    return set(title.split())


def is_similar(a: str, b: str) -> bool:
    wa = normalize_title(a)
    wb = normalize_title(b)
    if not wa or not wb:
        return False
    intersection = wa & wb
    similarity = len(intersection) / min(len(wa), len(wb))
    return similarity > 0.5


# ---------- News (RIA + Yandex + RBC, no duplicates) ----------
def get_news():
    try:
        news_blocks = []
        used_titles = []

        # --- Main news: RIA ---
        ria = requests.get(
            "https://ria.ru/export/rss2/archive/index.xml",
            timeout=10
        )
        ria_root = ET.fromstring(ria.text)
        ria_item = ria_root.find(".//item")

        ria_title = ria_item.find("title").text
        ria_link = ria_item.find("link").text
        used_titles.append(ria_title)

        news_blocks.append(
            f"🟢 **Главная новость дня:**\n**{ria_title}**\n{ria_link}"
        )

        # --- Yandex: 2–3 ---
        yandex = requests.get(
            "https://news.yandex.ru/index.rss",
            timeout=10
        )
        y_root = ET.fromstring(yandex.text)
        y_items = y_root.findall(".//item")

        yandex_news = []
        for item in y_items:
            if len(yandex_news) >= 3:
                break

            title = item.find("title").text
            link = item.find("link").text

            if any(is_similar(title, t) for t in used_titles):
                continue

            used_titles.append(title)
            yandex_news.append(f"{len(yandex_news)+1}. {title}\n{link}")

        if yandex_news:
            news_blocks.append(
                "🗞 **Ещё новости:**\n" + "\n\n".join(yandex_news)
            )

        # --- RBC: business ---
        rbc = requests.get(
            "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
            timeout=10
        )
        r_root = ET.fromstring(rbc.text)
        r_items = r_root.findall(".//item")

        rbc_news = []
        for item in r_items:
            if len(rbc_news) >= 3:
                break

            title = item.find("title").text
            link = item.find("link").text

            if any(is_similar(title, t) for t in used_titles):
                continue

            used_titles.append(title)
            rbc_news.append(f"{len(rbc_news)+1}. {title}\n{link}")

        if rbc_news:
            news_blocks.append(
                "💼 **РБК — бизнес и экономика:**\n" + "\n\n".join(rbc_news)
            )

        return "\n\n".join(news_blocks)

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
        f"♈ Гороскоп:\n{get_horoscope()}\n\n"
        f"{get_news()}\n\n"
        f"— Утренний бот ☕"
    )

    send_message(message)


if __name__ == "__main__":
    main()
