import os
import time
import requests
from datetime import datetime
from openai import OpenAI

# ======================================================
# CONFIG
# ======================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

CHECK_INTERVAL = 60        # detik
PRICE_SHOCK = 0.8          # %

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
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

# ======================================================
# DATA SOURCE (GANTI KE REAL)
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
# AI CORE
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence XAUUSD.

TUGAS:
- Menilai risiko arah (bukan tebak angka)
- Menjelaskan reaksi market
- Anti sensasional & anti overconfidence

Jawaban ringkas, tegas, profesional.
"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# EVENT PRE-BIAS (ARAH RISIKO)
# ======================================================
def event_pre_bias(price, levels):
    if price >= levels["high"] * 0.995:
        return (
            "Harga dekat resistance.\n"
            "➡️ Jika CPI lebih rendah dari ekspektasi → potensi SPIKE XAUUSD.\n"
            "➡️ Jika CPI lebih tinggi → risiko REVERSAL tajam."
        )
    elif price <= levels["low"] * 1.005:
        return (
            "Harga dekat support.\n"
            "➡️ Jika CPI lebih tinggi → potensi DUMP lanjutan.\n"
            "➡️ Jika CPI lebih rendah → short covering risk."
        )
    else:
        return (
            "Harga di tengah range.\n"
            "➡️ Risiko whipsaw dua arah.\n"
            "➡️ Arah valid biasanya muncul 15–30 menit pasca rilis."
        )

# ======================================================
# POST EVENT ANALYSIS
# ======================================================
def post_event_analysis(pre_price, post_price):
    change = (post_price - pre_price) / pre_price * 100
    prompt = f"""
EVENT TELAH RILIS (XAUUSD).

Harga sebelum rilis: {pre_price}
Harga setelah rilis: {post_price}
Perubahan: {change:.2f}%

ANALISA:
- Arah dominan (bullish / bearish / fake move)
- Risiko lanjutan 30–60 menit
- Sikap terbaik (follow / wait / fade)
"""
    return ai(prompt)

# ======================================================
# WATCHDOG CORE (NO SPAM)
# ======================================================
def watchdog():
    last_price = None
    levels = get_daily_levels()
    event_state = {}   # anti spam & state event

    send_telegram("🟢 XAUUSD GUARDIAN AKTIF\nMode: ANTI MC 😎")

    while True:
        try:
            price = get_price()
            now = datetime.utcnow()

            # ===============================
            # PRICE SHOCK ALERT
            # ===============================
            if last_price:
                change = (price - last_price) / last_price * 100
                if abs(change) >= PRICE_SHOCK:
                    send_telegram(
                        f"🚨 PRICE SHOCK\n"
                        f"Session: {session}\n"
                        f"Change: {change:.2f}%\n"
                        f"Price: {last_price} → {price}"
                    )

            # ===============================
            # EVENT LOGIC (NO SPAM)
            # ===============================
            for e in get_fundamental_events():
                h, m = map(int, e["time_utc"].split(":"))
                event_time = now.replace(hour=h, minute=m, second=0)
                time_to_event = (event_time - now).total_seconds()

                # PRE-EVENT (ONCE)
                if 0 <= time_to_event <= 1800 and e["event"] not in event_state:
                    bias = event_pre_bias(price, levels)
                    send_telegram(
                        f"⏰ EVENT WARNING\n"
                        f"{e['event']} ({e['impact']})\n"
                        f"Dalam < 30 menit\n\n"
                        f"PRE-EVENT BIAS:\n{bias}\n\n"
                        f"⚠️ Jangan entry sebelum reaksi jelas"
                    )
                    event_state[e["event"]] = {
                        "time": event_time,
                        "pre_price": price,
                        "post_sent": False
                    }

                # POST-EVENT (ONCE, 15 MENIT)
                if e["event"] in event_state:
                    state = event_state[e["event"]]
                    if not state["post_sent"] and (now - state["time"]).total_seconds() >= 900:
                        analysis = post_event_analysis(state["pre_price"], price)
                        send_telegram(
                            f"🧠 POST-EVENT ANALYSIS\n"
                            f"{e['event']}\n\n{analysis}"
                        )
                        state["post_sent"] = True

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as err:
            send_telegram(f"❌ GUARDIAN ERROR\n{err}")
            time.sleep(60)

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    watchdog()
