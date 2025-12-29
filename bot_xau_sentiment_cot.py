import os
import time
import requests
from datetime import datetime, timedelta
from openai import OpenAI

# ======================================================
# CONFIG
# ======================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

CHECK_INTERVAL = 60        # detik
DUMP_THRESHOLD = -0.8      # %
SPIKE_THRESHOLD = 0.8     # %

# ======================================================
# SESSION DETECTION
# ======================================================
hour_utc = datetime.utcnow().hour
if hour_utc < 7:
    session = "Asia"
elif hour_utc < 13:
    session = "London"
else:
    session = "New York"

# ======================================================
# TELEGRAM
# ======================================================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )
    print("TELEGRAM:", r.status_code)

# ======================================================
# PRICE SOURCE (WAJIB GANTI KE REAL)
# ======================================================
def get_price():
    # GANTI ke broker / TradingView / Metals API
    return 4550.0  # dummy

def get_daily_levels():
    return {
        "high": 4620,
        "low": 4480
    }

def get_fundamental_events():
    return [
        {"event": "US CPI", "impact": "High", "time": "Today"},
        {"event": "Fed Speaker", "impact": "Medium", "time": "Upcoming"}
    ]

def get_retail_sentiment():
    return {
        "source": "MyFxBook",
        "buy": 78,
        "sell": 22
    }

def get_bank_bias():
    return {
        "source": "COT / Bank Notes",
        "bias": "Bullish medium-term, cautious short-term"
    }

# ======================================================
# AI SYSTEM PROMPT (OTAK)
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence khusus XAUUSD.

PERAN:
- Membaca konteks market
- Membuat narasi & skenario
- Menjelaskan pergerakan ekstrem

BATASAN:
- Bukan eksekutor order
- Tidak memberi sinyal entry

GAYA:
- Tenang
- Tegas
- Masuk akal
"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# AI INTELLIGENCE
# ======================================================
def ai_intelligence(price, change):
    prompt = f"""
KONDISI MARKET:
Session: {session}
Harga sekarang: {price}
Perubahan cepat: {change:.2f}%

DATA TAMBAHAN:
- Fundamental: {get_fundamental_events()}
- Retail: {get_retail_sentiment()}
- Institutional: {get_bank_bias()}

TUGAS:
Jelaskan:
1. Apa kemungkinan penyebab pergerakan ini
2. Apakah continuation atau fake move
3. Risiko 30–60 menit ke depan
"""
    return ai(prompt)

# ======================================================
# EVENT PROXIMITY
# ======================================================
def check_event_proximity():
    now = datetime.utcnow()
    alerts = []
    for e in get_fundamental_events():
        if e["impact"] == "High" and e["time"] == "Today":
            alerts.append(e)
    return alerts

# ======================================================
# WATCHDOG CORE
# ======================================================
def watchdog():
    last_price = None
    levels = get_daily_levels()

    send_telegram("🟢 XAUUSD GUARDIAN AKTIF\nAnti MC Mode: ON 😎")

    while True:
        try:
            price = get_price()
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            if last_price:
                change = (price - last_price) / last_price * 100

                # 🚨 DUMP / SPIKE
                if change <= DUMP_THRESHOLD or change >= SPIKE_THRESHOLD:
                    direction = "DUMP" if change < 0 else "SPIKE"

                    send_telegram(
                        f"🚨 XAUUSD {direction}\n"
                        f"Waktu: {now}\n"
                        f"Perubahan: {change:.2f}%\n"
                        f"Harga: {last_price} → {price}"
                    )

                    analysis = ai_intelligence(price, change)
                    send_telegram("🧠 AI ANALYSIS\n" + analysis)

                # 📉 BREAK LOW
                if price <= levels["low"]:
                    send_telegram(
                        f"📉 BREAK DAILY LOW\n"
                        f"Level: {levels['low']}\n"
                        f"Harga: {price}"
                    )

                # 📈 BREAK HIGH
                if price >= levels["high"]:
                    send_telegram(
                        f"📈 BREAK DAILY HIGH\n"
                        f"Level: {levels['high']}\n"
                        f"Harga: {price}"
                    )

            # ⏰ EVENT WARNING
            events = check_event_proximity()
            for e in events:
                send_telegram(
                    f"⏰ EVENT WARNING\n"
                    f"{e['event']} ({e['impact']})\n"
                    f"Hari ini — volatilitas tinggi"
                )

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            send_telegram(f"❌ GUARDIAN ERROR\n{e}")
            time.sleep(60)

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    watchdog()
