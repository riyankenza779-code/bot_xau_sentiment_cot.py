import time
from datetime import datetime
import requests
from openai import OpenAI

# ===============================
# IMPORT PRICE FROM WEBHOOK
# ===============================
from tv_webhook import get_price

# ===============================
# CONFIG (GANTI YANG INI SAJA)
# ===============================
TELEGRAM_TOKEN = "GANTI_DENGAN_TELEGRAM_BOT_TOKEN"
CHAT_ID = "GANTI_DENGAN_CHAT_ID"
OPENAI_API_KEY = "GANTI_DENGAN_OPENAI_API_KEY"

client = OpenAI(api_key=OPENAI_API_KEY)

CHECK_INTERVAL = 60      # detik
PRICE_SHOCK = 0.8        # %

# ===============================
# SESSION DETECTION
# ===============================
hour = datetime.utcnow().hour
if hour < 7:
    session = "Asia"
elif hour < 13:
    session = "London"
else:
    session = "New York"

# ===============================
# TELEGRAM
# ===============================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )

# ===============================
# AI CORE
# ===============================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence XAUUSD.
Tugas: menjelaskan arah & risiko dari pergerakan harga.
Jawaban ringkas, profesional, dan anti overconfidence.
Dan prediksi potensi harga bulish atau berish tentukan dengan presentase dan harga"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ===============================
# FUNDAMENTAL EVENT
# ===============================
def get_fundamental_events():
    return [
        {"event": "US CPI", "impact": "High", "time_utc": "13:30"}
    ]

# ===============================
# EVENT LOGIC
# ===============================
def event_pre_bias(price):
    return (
        "Risiko volatilitas tinggi.\n"
        "Arah valid biasanya muncul setelah reaksi awal."
    )

def post_event_analysis(pre_price, post_price):
    return ai(
        f"Harga sebelum rilis: {pre_price}\n"
        f"Harga setelah rilis: {post_price}\n\n"
        f"Tentukan arah dominan dan risiko lanjutan."
    )

# ===============================
# WATCHDOG CORE
# ===============================
def watchdog():
    last_price = None
    event_state = {}

    send_telegram("🟢 Guardian TradingView AKTIF\nHarga REAL dari chart OANDA 😎")

    while True:
        try:
            price = get_price()

            if price is None:
                time.sleep(5)
                continue

            now = datetime.utcnow()

            # PRICE SHOCK
            if last_price:
                change = (price - last_price) / last_price * 100
                if abs(change) >= PRICE_SHOCK:
                    send_telegram(
                        f"🚨 PRICE SHOCK\n"
                        f"Session: {session}\n"
                        f"Change: {change:.2f}%\n"
                        f"{last_price} → {price}"
                    )

            # EVENT HANDLING
            for e in get_fundamental_events():
                h, m = map(int, e["time_utc"].split(":"))
                event_time = now.replace(hour=h, minute=m, second=0)
                time_to_event = (event_time - now).total_seconds()

                # PRE EVENT
                if 0 <= time_to_event <= 1800 and e["event"] not in event_state:
                    send_telegram(
                        f"⏰ EVENT WARNING\n"
                        f"{e['event']} ({e['impact']})\n\n"
                        f"{event_pre_bias(price)}"
                    )
                    event_state[e["event"]] = {
                        "time": event_time,
                        "pre_price": price,
                        "post_sent": False
                    }

                # POST EVENT
                if e["event"] in event_state:
                    st = event_state[e["event"]]
                    if not st["post_sent"] and (now - st["time"]).total_seconds() >= 900:
                        send_telegram(
                            f"🧠 POST EVENT ANALYSIS\n"
                            f"{e['event']}\n\n"
                            f"{post_event_analysis(st['pre_price'], price)}"
                        )
                        st["post_sent"] = True

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as err:
            send_telegram(f"❌ GUARDIAN ERROR\n{err}")
            time.sleep(30)

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    watchdog()
