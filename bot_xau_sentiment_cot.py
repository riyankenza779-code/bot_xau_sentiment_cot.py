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
# PRICE SOURCE (WAJIB GANTI KE REAL)
# ======================================================
def get_price():
    """
    GANTI ke API real:
    - MT5
    - TradingView webhook
    - Metals API
    """
    return 4550.0  # dummy

def get_daily_levels():
    """
    GANTI ke data real broker
    """
    return {
        "high": 4620,
        "low": 4480
    }

# ======================================================
# FUNDAMENTAL EVENTS (CONTOH)
# ======================================================
def get_today_events():
    return [
        {"event": "US CPI", "impact": "High", "time_utc": "13:30"},
        {"event": "Fed Speaker", "impact": "Medium", "time_utc": "18:00"}
    ]

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
# AI AUTO ANALYSIS
# ======================================================
def ai_analysis(price, change):
    prompt = f"""
Kamu adalah AI Market Intelligence XAUUSD.

KONDISI:
Harga saat ini: {price}
Perubahan cepat: {change:.2f}%

TUGAS:
Jelaskan secara singkat:
- kemungkinan penyebab pergerakan
- apakah ini continuation atau fake move
- risiko lanjutan dalam waktu dekat

Jawab ringkas & tegas.
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# ======================================================
# EVENT PROXIMITY CHECK
# ======================================================
def check_event_proximity():
    now = datetime.utcnow()
    alerts = []

    for e in get_today_events():
        h, m = map(int, e["time_utc"].split(":"))
        event_time = now.replace(hour=h, minute=m, second=0)

        if 0 <= (event_time - now).total_seconds() <= 1800:
            alerts.append(e)

    return alerts

# ======================================================
# WATCHDOG CORE
# ======================================================
def watchdog():
    last_price = None
    levels = get_daily_levels()

    send_telegram("🟢 XAUUSD WATCHDOG AKTIF\nAnti MC Mode: ON 😎")

    while True:
        try:
            price = get_price()
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # ===============================
            # PRICE CHANGE ALERT
            # ===============================
            if last_price:
                change = (price - last_price) / last_price * 100

                if change <= DUMP_THRESHOLD or change >= SPIKE_THRESHOLD:
                    direction = "DUMP" if change < 0 else "SPIKE"

                    send_telegram(
                        f"🚨 XAUUSD {direction} ALERT\n"
                        f"Time: {now}\n"
                        f"Change: {change:.2f}%\n"
                        f"Price: {last_price} → {price}"
                    )

                    # 🔥 AI AUTO ANALYSIS
                    analysis = ai_analysis(price, change)
                    send_telegram(f"🧠 AI QUICK ANALYSIS\n{analysis}")

            # ===============================
            # LEVEL BREAK ALERT
            # ===============================
            if price >= levels["high"]:
                send_telegram(
                    f"📈 XAUUSD BREAK HIGH\n"
                    f"Daily High: {levels['high']}\n"
                    f"Current: {price}\n"
                    f"⚠️ Potensi continuation / trap"
                )

            if price <= levels["low"]:
                send_telegram(
                    f"📉 XAUUSD BREAK LOW\n"
                    f"Daily Low: {levels['low']}\n"
                    f"Current: {price}\n"
                    f"⚠️ Stop hunt / panic risk"
                )

            # ===============================
            # EVENT PROXIMITY ALERT
            # ===============================
            events = check_event_proximity()
            for e in events:
                send_telegram(
                    f"⏰ EVENT WARNING\n"
                    f"{e['event']} ({e['impact']})\n"
                    f"Dalam < 30 menit\n"
                    f"⚠️ Volatilitas XAUUSD meningkat"
                )

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            send_telegram(f"❌ WATCHDOG ERROR\n{e}")
            time.sleep(60)

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    watchdog()
