import time
from datetime import datetime
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import threading

# ======================================================
# CONFIG — GANTI INI SAJA
# ======================================================
TELEGRAM_TOKEN = "ISI_TELEGRAM_BOT_TOKEN"
CHAT_ID = "ISI_CHAT_ID"
OPENAI_API_KEY = "ISI_OPENAI_API_KEY"

CHECK_INTERVAL = 60      # detik
PRICE_SHOCK = 0.6        # % per menit

# ======================================================
# INIT
# ======================================================
client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

latest_price = None
latest_time = None

# ======================================================
# SESSION DETECTION
# ======================================================
def get_session():
    h = datetime.utcnow().hour
    if h < 7:
        return "Asia"
    elif h < 13:
        return "London"
    else:
        return "New York"

# ======================================================
# TELEGRAM
# ======================================================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

# ======================================================
# AI CORE
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence XAUUSD.
Tugas:
- Menentukan arah dominan (bullish / bearish / whipsaw)
- Menilai risiko lanjutan
- Berdasarkan pergerakan harga REAL
Jawaban singkat, tegas, profesional.
"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# FUNDAMENTAL EVENT (EDIT JIKA PERLU)
# ======================================================
def get_fundamental_events():
    return [
        {"event": "US CPI", "impact": "High", "time_utc": "13:30"}
    ]

def post_event_analysis(pre, post):
    return ai(
        f"Harga sebelum event: {pre}\n"
        f"Harga sekarang: {post}\n\n"
        f"Tentukan arah dominan dan risiko lanjutan."
    )

# ======================================================
# TRADINGVIEW WEBHOOK
# ======================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    global latest_price, latest_time
    data = request.json
    try:
        latest_price = float(data["price"])
        latest_time = data.get("time", "unknown")
        print(f"[TV] Price update: {latest_price} @ {latest_time}")
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[WEBHOOK ERROR]", e)
        return jsonify({"status": "error"}), 400

# ======================================================
# WATCHDOG CORE
# ======================================================
def watchdog():
    global latest_price

    last_price = None
    event_state = {}

    send_telegram("🟢 XAUUSD GUARDIAN AKTIF\nHarga AUTO dari TradingView 1m 😎")

    while True:
        try:
            if latest_price is None:
                time.sleep(3)
                continue

            price = latest_price
            now = datetime.utcnow()
            session = get_session()

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
                        f"{last_price:.2f} → {price:.2f}"
                    )

            # ===============================
            # EVENT LOGIC
            # ===============================
            for e in get_fundamental_events():
                h, m = map(int, e["time_utc"].split(":"))
                event_time = now.replace(hour=h, minute=m, second=0)
                dt = (event_time - now).total_seconds()

                # PRE EVENT
                if 0 <= dt <= 1800 and e["event"] not in event_state:
                    send_telegram(
                        f"⏰ EVENT WARNING\n"
                        f"{e['event']} ({e['impact']})\n"
                        f"Harga saat ini: {price:.2f}\n"
                        f"Tunggu reaksi market."
                    )
                    event_state[e["event"]] = {
                        "time": event_time,
                        "pre": price,
                        "done": False
                    }

                # POST EVENT
                if e["event"] in event_state:
                    st = event_state[e["event"]]
                    if not st["done"] and (now - st["time"]).total_seconds() >= 900:
                        send_telegram(
                            f"🧠 POST EVENT ANALYSIS\n"
                            f"{e['event']}\n\n"
                            f"{post_event_analysis(st['pre'], price)}"
                        )
                        st["done"] = True

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as err:
            send_telegram(f"❌ GUARDIAN ERROR\n{err}")
            time.sleep(30)

# ======================================================
# RUN ALL-IN-ONE
# ======================================================
if __name__ == "__main__":
    threading.Thread(target=watchdog, daemon=True).start()
    print("🟢 Guardian + Webhook RUNNING (port 5000)")
    app.run(host="0.0.0.0", port=5000)
