import requests
import logging
from datetime import datetime import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

# ─────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────
OPENWEATHER_API_KEY = "8fc0ab919ecad21ff1e59832ec6743f7"  # OpenWeatherMap key

CALLMEBOT_PHONE = "905513456995"   # Telefon numarası
CALLMEBOT_APIKEY = "6485799"       # CallMeBot API key
WAHA_URL = "https://waha-production-3ad4e.up.railway.app"
WAHA_SESSION = "default"
WHATSAPP_CHANNEL_ID = "0029Vb7lxp6CnA7pyfoVna3h@newsletter"

CITIES = [
    "Istanbul,TR",
    "Ankara,TR",
    "Izmir,TR",
    "Antalya,TR",
    "Konya,TR",
    "Bursa,TR",
    "Erzurum,TR",
    "Mersin,TR",
    "Eskisehir,TR",
]

CITY_NAMES_TR = {
    "Istanbul,TR": "İstanbul",
    "Ankara,TR": "Ankara",
    "Izmir,TR": "İzmir",
    "Antalya,TR": "Antalya",
    "Konya,TR": "Konya",
    "Bursa,TR":"Bursa",
    "Erzurum,TR":"Erzurum",
    "Mersin,TR":"Mersin",
    "Eskisehir,TR":"Eskişehir",
}
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def get_weather_emoji(description: str) -> str:
    desc = description.lower()
    if any(w in desc for w in ["clear", "sunny", "açık"]):
        return "☀️"
    elif any(w in desc for w in ["cloud", "bulut", "overcast"]):
        return "☁️"
    elif any(w in desc for w in ["rain", "yağmur", "drizzle"]):
        return "🌧️"
    elif any(w in desc for w in ["thunder", "storm", "fırtına"]):
        return "⛈️"
    elif any(w in desc for w in ["snow", "kar"]):
        return "❄️"
    elif any(w in desc for w in ["mist", "fog", "sis"]):
        return "🌫️"
    return "🌤️"


def get_advice(description: str, temp: float) -> str:
    desc = description.lower()
    if any(w in desc for w in ["rain", "drizzle", "yağmur"]):
        return "Şemsiyenizi yanınıza almayı unutmayın!"
    elif any(w in desc for w in ["thunder", "storm"]):
        return "Fırtınalı hava! Mümkünse dışarı çıkmayın."
    elif any(w in desc for w in ["snow", "kar"]):
        return "Kalın giyin, yollar kaygan olabilir."
    elif temp >= 30:
        return "Çok sıcak! Bol su için ve güneş kremi kullanın."
    elif temp <= 5:
        return "Hava çok soğuk, sıcak giyinin!"
    else:
        return "Keyifli bir gün geçirin!"


def fetch_weather(city_code: str) -> dict | None:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_code,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "tr",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "city": CITY_NAMES_TR.get(city_code, city_code),
            "temp": round(data["main"]["temp"]),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].capitalize(),
        }
    except requests.exceptions.RequestException as e:
        log.error(f"{city_code} için hava durumu alınamadı: {e}")
        return None


def format_message(weather_list: list) -> str:
   tz = pytz.timezone("Europe/Istanbul")
now = datetime.now(tz).strftime("%H:%M")
    lines = [f"Hava Durumu Raporu - {now}"]
    lines.append("─────────────────")
    for w in weather_list:
        emoji = get_weather_emoji(w["description"])
        advice = get_advice(w["description"], w["temp"])
        lines.append(
            f"{emoji} {w['city']}\n"
            f"Sicaklik: {w['temp']}C\n"
            f"Nem: %{w['humidity']}\n"
            f"Durum: {w['description']}\n"
            f"Tavsiye: {advice}"
        )
        lines.append("─────────────────")
    return "\n".join(lines)


def send_whatsapp_message(message: str) -> bool:
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": CALLMEBOT_PHONE,
        "text": message,
        "apikey": CALLMEBOT_APIKEY,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            log.info("Mesaj başarıyla gönderildi.")
            return True
        else:
            log.error(f"Mesaj gönderilemedi: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"Bağlantı hatası: {e}")
        return False


def run_bot():
    log.info("Hava durumu verisi toplanıyor...")
    weather_data = []
    for city in CITIES:
        data = fetch_weather(city)
        if data:
            weather_data.append(data)

    if not weather_data:
        log.warning("Hiçbir şehir için veri alınamadı.")
        return

    message = format_message(weather_data)
    log.info(f"Mesaj gönderiliyor...\n{message}")
    send_whatsapp_message(message)
    send_to_channel(message)
    
    def send_to_channel(message: str) -> bool:
    url = f"{WAHA_URL}/api/sendText"
    headers = {"X-Api-Key": "admin123"}
    payload = {
        "session": WAHA_SESSION,
        "chatId": WHATSAPP_CHANNEL_ID,
        "text": message,
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 201:
            log.info("Kanal mesajı başarıyla gönderildi.")
            return True
        else:
            log.error(f"Kanal mesajı gönderilemedi: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"Kanal bağlantı hatası: {e}")
        return False


if __name__ == "__main__":
    log.info("Bot başlatılıyor...")
    run_bot()  # İlk çalıştırmada hemen mesaj gönder

    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(run_bot, "cron", minute=0)
    log.info("Zamanlayıcı aktif - her saat başı çalışacak.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot durduruldu.")
