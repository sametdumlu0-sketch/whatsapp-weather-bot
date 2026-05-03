import requests
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# ─────────────────────────────────────────
#  AYARLAR — sadece bu bölümü düzenle
# ─────────────────────────────────────────
OPENWEATHER_API_KEY = "8fc0ab919ecad21ff1e59832ec6743f7"   # OpenWeatherMap key buraya

WAHA_URL = "http://localhost:3000"     # WAHA sunucu adresi
WAHA_SESSION = "default"              # WAHA oturum adı
WHATSAPP_CHANNEL_ID = "KANAL_ID"      # WhatsApp kanal ID'si buraya

CITIES = [
    "Istanbul,TR",
    "Ankara,TR",
    "Izmir,TR",
    "Antalya,TR",
    "Konya,TR",
]

CITY_NAMES_TR = {
    "Istanbul,TR": "İstanbul",
    "Ankara,TR": "Ankara",
    "Izmir,TR": "İzmir",
    "Antalya,TR": "Antalya",
    "Konya,TR": "Konya",
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
log = logging.getLogger(_name_)


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
        return "☂️ Şemsiyenizi yanınıza almayı unutmayın!"
    elif any(w in desc for w in ["thunder", "storm"]):
        return "⚡ Fırtınalı hava! Mümkünse dışarı çıkmayın."
    elif any(w in desc for w in ["snow", "kar"]):
        return "🧣 Kalın giyin, yollar kaygan olabilir."
    elif temp >= 30:
        return "🌞 Çok sıcak! Bol su için ve güneş kremi kullanın."
    elif temp <= 5:
        return "🧥 Hava çok soğuk, sıcak giyinin!"
    else:
        return "😊 Hava güzel, keyifli bir gün geçirin!"


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


def format_message(weather_list: list[dict]) -> str:
    now = datetime.now().strftime("%H:%M")
    lines = [f"🗓️ Hava Durumu Raporu — {now}\n"]
    for w in weather_list:
        emoji = get_weather_emoji(w["description"])
        advice = get_advice(w["description"], w["temp"])
        lines.append(
            f"{emoji} {w['city']}\n"
            f"🌡️ Sıcaklık: {w['temp']}°C\n"
            f"💧 Nem: %{w['humidity']}\n"
            f"📋 Durum: {w['description']}\n"
            f"💡 {advice}\n"
        )
    lines.append("─────────────────")
    lines.append("Veriler OpenWeatherMap tarafından sağlanmaktadır.")
    return "\n".join(lines)


def send_to_whatsapp(message: str) -> bool:
    url = f"{WAHA_URL}/api/sendText"
    payload = {
        "session": WAHA_SESSION,
        "chatId": WHATSAPP_CHANNEL_ID,
        "text": message,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        log.info("Mesaj başarıyla WhatsApp kanalına gönderildi.")
        return True
    except requests.exceptions.RequestException as e:
        log.error(f"WhatsApp mesajı gönderilemedi: {e}")
        return False


def run_bot():
    log.info("Hava durumu verisi toplanıyor...")
    weather_data = []
    for city in CITIES:
        data = fetch_weather(city)
        if data:
            weather_data.append(data)

    if not weather_data:
        log.warning("Hiçbir şehir için veri alınamadı, mesaj gönderilmedi.")
        return

    message = format_message(weather_data)
    log.info(f"Oluşturulan mesaj:\n{message}")
    send_to_whatsapp(message)


if __name__ == "__main__":
    log.info("Bot başlatılıyor...")
    run_bot()  # İlk çalıştırmada hemen bir mesaj gönder

    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(run_bot, "cron", minute=0)  # Her saat başı
    log.info("Zamanlayıcı aktif — her saat başı çalışacak.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot durduruldu.")
