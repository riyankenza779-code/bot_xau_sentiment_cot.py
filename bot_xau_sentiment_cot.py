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
# PRICE & MARKET DATA (GANTI KE REAL)
# ======================================================
def get_price():
    return 4550.0  # dummy

def get_daily_levels():
    return {"high": 4620, "low": 4480}

def get_fundamental_events():
    return [
        {"event": "US CPI", "impact": "High", "time_utc": "13:30"}
    ]

def get_retail_sentiment():
    return {"buy": 78, "sell": 22}

def get_bank_bias():
    return {"bias": "Bullish medium-term, cautious short-term"}

# ======================================================
# AI SYSTEM PROMPT
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence khusus XAUUSD.

FOKUS:
- Membaca konteks event & harga
- Menilai risiko arah, bukan menebak angka
- Anti sensasional & anti overconfidence

Jawab ringkas, profesional, dan kontekstual.
"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# EVENT PRE-BIAS
# ======================================================
def event_pre_bias(price, levels):
    if price > levels["high"] * 0.995:
        return "Bias bullish jika data USD melemah. Risiko spike XAUUSD."
    elif price < levels["low"] * 1.005:
        return "Bias bearish jika data USD kuat. Risiko dump XAUUSD."
    else:
        return (
            "Netral. Risiko whipsaw dua arah.\n"
            "Tunggu reaksi 15–30 menit pasca rilis."
        )

# ======================================================
# POST-EVENT ANALYSIS
# ======================================================
def post_event_analysis(pre_price, post_price):
    change = (post_price - pre_price) / pre_price * 100
    prompt = f"""
EVENT TELAH RILIS.

Harga sebelum rilis: {pre_price}
Harga setelah rilis: {post_price}
Perubahan: {change:.2f}%

TUGAS:
- Apakah reaksi ini valid atau fake move?
- Risiko lanjutan 30–60 menit ke depan
- Sikap terbaik (follow / wait / fade)
"""
    return ai(prompt)

# ======================================================
# WATCHDOG CORE
# ======================================================
def watchdog():
    last_price = None
    levels = get_daily_levels()
    last_event_alert = None

    send_telegram("🟢 XAUUSD GUARDIAN AKTIF\nMode: ANTI MC 😎")

    while True:
        try:
            price = get_price()
            now = datetime.utcnow()

            # ===============================
            # PRICE MOVEMENT ALERT
            # ===============================
            if last_price:
                change = (price - last_price) / last_price * 100

                if abs(change) >= SPIKE_THRESHOLD:
                    send_telegram(
                        f"🚨 PRICE SHOCK\n"
                        f"Change: {change:.2f}%\n"
                        f"Price: {last_price} → {price}"
                    )

            # ===============================
            # EVENT PRE-BIAS ALERT
            # ===============================
            for e in get_fundamental_events():
                h, m = map(int, e["time_utc"].split(":"))
                event_time = now.replace(hour=h, minute=m, second=0)

                if 0 <= (event_time - now).total_seconds() <= 1800:
                    if last_event_alert != e["event"]:
                        bias = event_pre_bias(price, levels)
                        send_telegram(
                            f"⏰ EVENT WARNING\n"
                            f"{e['event']} ({e['impact']})\n"
                            f"Dalam < 30 menit\n\n"
                            f"Pre-Event Bias:\n{bias}\n\n"
                            f"⚠️ Hindari entry sebelum reaksi jelas"
                        )
                        last_event_alert = e["event"]
                        pre_event_price = price

                # ===============================
                # POST-EVENT ANALYSIS (15 MENIT)
                # ===============================
                if last_event_alert == e["event"]:
                    if (now - event_time).total_seconds() >= 900:
                        analysis = post_event_analysis(pre_event_price, price)
                        send_telegram(
                            f"🧠 POST-EVENT ANALYSIS\n"
                            f"{e['event']}\n\n{analysis}"
                        )
                        last_event_alert = None

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
