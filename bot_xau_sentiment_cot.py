from openai import OpenAI
import os, requests, time
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =========================
# GLOBAL STATE (SWITCHABLE)
# =========================
ACTIVE_PAIR = "OANDA:XAUUSD"
ACTIVE_TF = "M5"           # M5 / M15
MODE = "SCALPING"

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
# PRICE (OHLC SIMPLIFIED)
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
# INDICATORS (LIGHT)
# =========================
def calc_rsi(close, open_):
    delta = close - open_
    if delta > 0:
        return min(75, 50 + abs(delta) * 5)
    else:
        return max(25, 50 - abs(delta) * 5)

def calc_macd(close, open_):
    return round(close - open_, 2)

# =========================
# RISKI-STYLE SETUP
# =========================
def detect_setup(price, open_, high, low, rsi, macd):
    rng = high - low

    # BREAKOUT
    if price > high and rsi > 55 and macd > 0:
        entry = price
        sl = entry - rng * 0.8
        tp = entry + (entry - sl) * 1.8
        return "LONG", entry, sl, tp, "Momentum Breakout"

    # PULLBACK
    if 45 <= rsi <= 55 and macd > 0:
        entry = price
        sl = low - rng * 0.5
        tp = entry + (entry - sl) * 1.5
        return "LONG", entry, sl, tp, "Pullback Continuation"

    # REVERSAL
    if rsi > 70 and macd < 0:
        entry = price
        sl = high + rng * 0.5
        tp = entry - (sl - entry) * 1.5
        return "SHORT", entry, sl, tp, "Exhaustion Reversal"

    return None

# =========================
# AI CONFIRMATION
# =========================
def ai_confirm(setup, rsi, macd):
    score = 50
    if setup:
        score += 10
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

    send(
        f"🤖 SCALPING BOT AKTIF\nPair: {ACTIVE_PAIR}\nTF: {ACTIVE_TF}"
    )

    last_scan = 0
    last_update = 0

    while True:
        try:
            interval = 300 if ACTIVE_TF == "M5" else 900
            now = time.time()

            # ===== AUTO SCAN =====
            if now - last_scan > interval:
                last_scan = now

                price, rsi, macd, setup = scan(ACTIVE_PAIR)

                if setup:
                    side, entry, sl, tp, reason = setup
                    prob, conf = ai_confirm(setup, rsi, macd)

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

📌 Strategy:
Riski-style {reason}

⚠️ Risk max 1%
""")

            # ===== TELEGRAM COMMAND =====
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                timeout=20
            ).json()

            for u in r.get("result", []):
                chat_id = u["message"]["chat"]["id"]
                text = u["message"].get("text","").lower()

                # SWITCH PAIR
                if text == "/xau":
                    ACTIVE_PAIR = "OANDA:XAUUSD"
                    send("✅ Pair diset ke XAUUSD", chat_id)
                    continue

                if text == "/btc":
                    ACTIVE_PAIR = "BINANCE:BTCUSDT"
                    send("✅ Pair diset ke BTCUSDT", chat_id)
                    continue

                # SWITCH TF
                if text == "/m5":
                    ACTIVE_TF = "M5"
                    send("⚡ Timeframe diset ke M5", chat_id)
                    continue

                if text == "/m15":
                    ACTIVE_TF = "M15"
                    send("📊 Timeframe diset ke M15", chat_id)
                    continue

                # STATUS
                if text == "/status":
                    send(
                        f"📌 STATUS BOT\nPair: {ACTIVE_PAIR}\nTF: {ACTIVE_TF}",
                        chat_id
                    )
                    continue

            time.sleep(2)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":
    run_bot()
