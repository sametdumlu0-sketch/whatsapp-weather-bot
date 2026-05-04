import requests
import logging
import pytz
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# ─────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────
OPENWEATHER_API_KEY = "8fc0ab919ecad21ff1e59832ec6743f7"  # OpenWeatherMap key

CALLMEBOT_PHONE  = "905513456995"  # Telefon numarası
CALLMEBOT_APIKEY = "6485799"       # CallMeBot API key

WAHA_URL            = "https://waha-production-3ad4e.up.railway.app"
WAHA_SESSION        = "default"
WAHA_API_KEY        = "admin123"
WHATSAPP_CHANNEL_ID = "0029Vb7lxp6CnA7pyfoVna3h@lid"

CITIES = [
    "Istanbul,TR",
    "Ankara,TR",
    "Izmir,TR",
    "Antalya,TR",
    "Konya,TR",
    "Bursa,TR",
    
]

CITY_NAMES_TR = {
    "Istanbul,TR":   "İstanbul",
    "Ankara,TR":     "Ankara",
    "Izmir,TR":      "İzmir",
    "Antalya,TR":    "Antalya",
    "Konya,TR":      "Konya",
    "Bursa,TR":      "Bursa",
    
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

TZ = pytz.timezone("Europe/Istanbul")


def get_weather_emoji(description: str) -> str:
    desc = description.lower()
    if any(w in desc for w in ["clear", "sunny", "açık"]):
        return "☀️"
    elif any(w in desc for w in ["rain", "yağmur", "drizzle", "sağanak"]):
        return "🌧️"
    elif any(w in desc for w in ["thunder", "storm", "fırtına"]):
        return "⛈️"
    elif any(w in desc for w in ["snow", "kar"]):
        return "❄️"
    elif any(w in desc for w in ["mist", "fog", "sis"]):
        return "🌫️"
    elif any(w in desc for w in ["cloud", "bulut", "overcast", "kapalı"]):
        return "☁️"
    return "🌤️"


def get_advice(description: str, temp: float) -> str:
    desc = description.lower()
    if any(w in desc for w in ["rain", "drizzle", "yağmur", "sağanak"]):
        return "☂️ Şemsiyenizi yanınıza almayı unutmayın!"
    elif any(w in desc for w in ["thunder", "storm", "fırtına"]):
        return "⚡ Fırtınalı hava! Mümkünse dışarı çıkmayın."
    elif any(w in desc for w in ["snow", "kar"]):
        return "🧣 Kalın giyin, yollar kaygan olabilir."
    elif temp >= 35:
        return "🥵 Aşırı sıcak! Dışarı çıkmaktan kaçının."
    elif temp >= 30:
        return "🌞 Çok sıcak! Bol su için ve güneş kremi kullanın."
    elif temp <= 0:
        return "🥶 Dondurucu soğuk! Çok iyi giyinin."
    elif temp <= 5:
        return "🧥 Hava çok soğuk, sıcak giyinin!"
    else:
        return "😊 Hava güzel, keyifli bir gün geçirin!"


def fetch_weather(city_code: str) -> dict | None:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q":      city_code,
        "appid":  OPENWEATHER_API_KEY,
        "units":  "metric",
        "lang":   "tr",
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "city":        CITY_NAMES_TR.get(city_code, city_code),
            "temp":        round(data["main"]["temp"]),
            "feels_like":  round(data["main"]["feels_like"]),
            "humidity":    data["main"]["humidity"],
            "description": data["weather"][0]["description"].capitalize(),
        }
    except requests.exceptions.RequestException as e:
        log.error(f"{city_code} için hava durumu alınamadı: {e}")
        return None


def format_message(weather_list: list) -> str:
    now   = datetime.now(TZ).strftime("%H:%M")
    tarih = datetime.now(TZ).strftime("%d.%m.%Y")

    lines = []
    lines.append("🌍 *HAVA DURUMU RAPORU*")
    lines.append(f"📅 {tarih}  —  ⏰ {now} (TR)")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    for w in weather_list:
        emoji  = get_weather_emoji(w["description"])
        advice = get_advice(w["description"], w["temp"])
        lines.append(f"\n{emoji}  *{w['city'].upper()}*")
        lines.append(f"   🌡️  Sıcaklık   : *{w['temp']}°C*  (Hissedilen: {w['feels_like']}°C)")
        lines.append(f"   💧  Nem         : *%{w['humidity']}*")
        lines.append(f"   📋  Durum       : {w['description']}")
        lines.append(f"   💡  _{advice}_")
        lines.append("──────────────────────")

    lines.append("\n_🤖 Weather Bot AI — Saatlik Otomatik Güncelleme_")
    return "\n".join(lines)


def send_to_phone(message: str) -> bool:
    """CallMeBot ile kişisel telefona mesaj gönder."""
    url = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone":  CALLMEBOT_PHONE,
        "text":   message,
        "apikey": CALLMEBOT_APIKEY,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            log.info("Telefon mesajı başarıyla gönderildi.")
            return True
        else:
            log.error(f"Telefon mesajı gönderilemedi: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"Telefon bağlantı hatası: {e}")
        return False


def send_to_channel(message: str) -> bool:
    """WAHA ile WhatsApp kanalına mesaj gönder."""
    url     = f"{WAHA_URL}/api/sendText"
    headers = {"X-Api-Key": WAHA_API_KEY}
    payload = {
        "session": WAHA_SESSION,
        "chatId":  WHATSAPP_CHANNEL_ID,
        "text":    message,
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code in (200, 201):
            log.info("Kanal mesajı başarıyla gönderildi.")
            return True
        else:
            log.error(f"Kanal mesajı gönderilemedi: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        log.error(f"Kanal bağlantı hatası: {e}")
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
    log.info(f"Mesaj oluşturuldu:\n{message}")

    send_to_phone(message)
    send_to_channel(message)


if __name__ == "__main__":
    log.info("Bot başlatılıyor...")
    run_bot()  # İlk çalıştırmada hemen mesaj gönder

    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(run_bot, "cron", minute=0)  # Her saat başı
    log.info("Zamanlayıcı aktif — her saat başı çalışacak.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot durduruldu.")
