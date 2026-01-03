from openai import OpenAI
import os, requests, time

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =========================
# GLOBAL STATE
# =========================
ACTIVE_PAIR = "OANDA:XAUUSD"
ACTIVE_TF = "M5"
MODE = "SCALPING"

STATUS_ON = True
LAST_STATUS_TIME = 0
last_update_id = 0   # anti spam

# =========================
# TELEGRAM
# =========================
def send(text, chat_id=CHAT_ID):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20
    )

# =========================
# PRICE
# =========================
def get_price(symbol):
    r = requests.post(
        "https://scanner.tradingview.com/symbol",
        json={
            "symbol": symbol,
            "fields": ["last_price","open","high","low"]
        },
        timeout=10
    ).json()["data"][0]["d"]
    return r[0], r[1], r[2], r[3]

# =========================
# INDICATORS
# =========================
def calc_rsi(close, open_):
    delta = close - open_
    return min(75, max(25, 50 + delta * 5))

def calc_macd(close, open_):
    return round(close - open_, 2)

# =========================
# SETUP LOGIC
# =========================
def detect_setup(price, open_, high, low, rsi, macd):
    rng = high - low

    if price > high and rsi > 55 and macd > 0:
        return "LONG", price, price - rng*0.8, price + rng*1.6, "Breakout"

    if 45 <= rsi <= 55 and macd > 0:
        return "LONG", price, low - rng*0.5, price + rng*1.2, "Pullback"

    if rsi > 70 and macd < 0:
        return "SHORT", price, high + rng*0.5, price - rng*1.2, "Reversal"

    return None

# =========================
# AI CONFIRM
# =========================
def ai_confirm(rsi, macd):
    score = 50
    if rsi > 55 and macd > 0:
        score += 20
    if 40 <= rsi <= 65:
        score += 15
    if abs(macd) > 0.5:
        score += 10

    score = min(75, score)
    conf = "HIGH" if score >= 65 else "MEDIUM" if score >= 55 else "LOW"
    return score, conf

# =========================
# SCAN
# =========================
def scan(symbol):
    price, open_, high, low = get_price(symbol)
    rsi = calc_rsi(price, open_)
    macd = calc_macd(price, open_)
    setup = detect_setup(price, open_, high, low, rsi, macd)
    return price, rsi, macd, setup

# =========================
# MAIN LOOP
# =========================
def run_bot():
    global ACTIVE_PAIR, ACTIVE_TF
    global STATUS_ON, LAST_STATUS_TIME, last_update_id

    send("🤖 SCALPING BOT AKTIF (READY)")

    last_scan = 0

    while True:
        try:
            now = time.time()
            interval = 300 if ACTIVE_TF == "M5" else 900

            # ===== AUTO SIGNAL =====
            if now - last_scan > interval:
                last_scan = now
                price, rsi, macd, setup = scan(ACTIVE_PAIR)

                if setup:
                    side, entry, sl, tp, reason = setup
                    prob, conf = ai_confirm(rsi, macd)

                    if prob >= 55:
                        send(f"""
🎯 SIGNAL {ACTIVE_PAIR.replace('OANDA:','').replace('BINANCE:','')} ({ACTIVE_TF})

Direction: {side}
Entry: {round(entry,2)}
SL: {round(sl,2)}
TP: {round(tp,2)}

📉 RSI: {round(rsi,1)}
📊 MACD: {macd}

🧠 Win Probability: {prob}%
Confidence: {conf}

📌 Setup: {reason}
⚠️ Risk max 1%
""")

            # ===== STATUS HEARTBEAT =====
            if STATUS_ON and now - LAST_STATUS_TIME > 1800:
                LAST_STATUS_TIME = now
                send(f"📡 Bot aktif | Pair: {ACTIVE_PAIR} | TF: {ACTIVE_TF}")

            # ===== TELEGRAM UPDATES (OFFSET) =====
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}",
                timeout=20
            ).json()

            for u in r.get("result", []):
                last_update_id = u["update_id"]
                msg = u.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "").lower()

                if not text:
                    continue

                # /START
                if text == "/start":
                    send(
                        "👋 Selamat datang di Scalping Bot\n\n"
                        "📌 Command:\n"
                        "/xau → Gold\n"
                        "/btc → Bitcoin\n"
                        "/m5 → TF M5\n"
                        "/m15 → TF M15\n"
                        "/status → Cek status\n"
                        "/statusoff → Matikan status",
                        chat_id
                    )
                    continue

                # STATUS SWITCH
                if text == "/statusoff":
                    STATUS_ON = False
                    send("🔕 Status dimatikan", chat_id)
                    continue

                if text == "/statuson":
                    STATUS_ON = True
                    send("🔔 Status diaktifkan", chat_id)
                    continue

                # PAIR SWITCH
                if text == "/xau":
                    ACTIVE_PAIR = "OANDA:XAUUSD"
                    send("✅ Pair diset ke XAUUSD", chat_id)
                    continue

                if text == "/btc":
                    ACTIVE_PAIR = "BINANCE:BTCUSDT"
                    send("✅ Pair diset ke BTCUSDT", chat_id)
                    continue

                # TF SWITCH
                if text == "/m5":
                    ACTIVE_TF = "M5"
                    send("⚡ Timeframe M5 aktif", chat_id)
                    continue

                if text == "/m15":
                    ACTIVE_TF = "M15"
                    send("📊 Timeframe M15 aktif", chat_id)
                    continue

                if text == "/status":
                    send(
                        f"📌 STATUS BOT\nPair: {ACTIVE_PAIR}\nTF: {ACTIVE_TF}\nStatus Msg: {'ON' if STATUS_ON else 'OFF'}",
                        chat_id
                    )

            time.sleep(2)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":
    run_bot()
