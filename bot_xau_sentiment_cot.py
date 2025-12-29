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
OANDA_API_KEY = os.environ.get("OANDA_API_KEY")
OANDA_ENV = os.environ.get("OANDA_ENV", "practice")  # practice / live

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
    requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )

# ======================================================
# OANDA REAL PRICE (XAUUSD)
# ======================================================
def get_price():
    if OANDA_ENV == "live":
        base_url = "https://api-fxtrade.oanda.com"
    else:
        base_url = "https://api-fxpractice.oanda.com"

    url = f"{base_url}/v3/instruments/XAU_USD/pricing"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"instruments": "XAU_USD"}

    r = requests.get(url, headers=headers, params=params, timeout=10)
    data = r.json()

    bid = float(data["prices"][0]["bids"][0]["price"])
    ask = float(data["prices"][0]["asks"][0]["price"])
    return (bid + ask) / 2

# ======================================================
# MARKET CONTEXT
# ======================================================
def get_daily_levels():
    # placeholder — bisa diganti high/low broker
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

FOKUS:
- Membaca reaksi harga real
- Menilai risiko arah (bukan tebak angka)
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
# EVENT PRE-BIAS
# ======================================================
def event_pre_bias(price, levels):
    if price >= levels["high"] * 0.995:
        return (
            "Harga dekat resistance.\n"
            "➡️ CPI lemah → potensi SPIKE XAUUSD.\n"
            "➡️ CPI kuat → risiko REVERSAL tajam."
        )
    elif price <= levels["low"] * 1.005:
        return (
            "Harga dekat support.\n"
            "➡️ CPI kuat → potensi DUMP lanjutan.\n"
            "➡️ CPI lemah → short covering risk."
        )
    else:
        return (
            "Harga di tengah range.\n"
            "➡️ Risiko whipsaw dua arah.\n"
            "➡️ Arah valid muncul 15–30 menit pasca rilis."
        )

# ======================================================
# POST EVENT ANALYSIS
# ======================================================
def post_event_analysis(pre_price, post_price):
    change = (post_price - pre_price) / pre_price * 100
    prompt = f"""
EVENT TELAH RILIS (XAUUSD)

Harga sebelum rilis: {pre_price:.2f}
Harga setelah rilis: {post_price:.2f}
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
    event_state = {}

    send_telegram("🟢 XAUUSD GUARDIAN AKTIF\nHarga REAL OANDA • Anti MC 😎")

    while True:
        try:
            price = get_price()
            now = datetime.utcnow()

            # ===============================
            # PRICE SHOCK
            # ===============================
            if last_price:
                change = (price - last_price) / last_price * 100
                if abs(change) >= PRICE_SHOCK:
                    send_telegram(
                        f"🚨 PRICE SHOCK\n"
                        f"Session: {session}\n"
                        f"Change: {change:.2f}%\n"
                        f"Price: {last_price:.2f} → {price:.2f}"
                    )

            # ===============================
            # EVENT LOGIC (PRE + POST)
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
                        f"⚠️ Tunggu reaksi market"
                    )
                    event_state[e["event"]] = {
                        "time": event_time,
                        "pre_price": price,
                        "post_sent": False
                    }

                # POST-EVENT (15 MENIT)
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
