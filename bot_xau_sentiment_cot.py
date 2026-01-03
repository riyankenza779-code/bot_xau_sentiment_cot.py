from openai import OpenAI
import os, requests, time
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PAIR = "OANDA:XAUUSD"
MODE = "SCALPING"      # SCALPING / INTRADAY
TF = "M5"              # M5 / M15

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
# PRICE (SIMPLIFIED OHLC)
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
# INDICATORS (LIGHTWEIGHT)
# =========================
def calc_rsi(close, open_):
    delta = close - open_
    if delta > 0:
        return min(70, 50 + abs(delta) * 5)
    else:
        return max(30, 50 - abs(delta) * 5)

def calc_macd(close, open_):
    return round(close - open_, 2)

# =========================
# RISKI-STYLE SETUP
# =========================
def detect_setup(price, open_, high, low, rsi, macd):
    range_candle = high - low

    # MOMENTUM BREAKOUT
    if price > high and rsi > 55 and macd > 0:
        entry = price
        sl = entry - range_candle * 0.8
        tp = entry + (entry - sl) * 1.8
        return "LONG", entry, sl, tp, "Momentum Breakout"

    # PULLBACK TREND
    if rsi > 45 and rsi < 55 and macd > 0:
        entry = price
        sl = low - range_candle * 0.5
        tp = entry + (entry - sl) * 1.5
        return "LONG", entry, sl, tp, "Pullback Continuation"

    # REVERSAL EXTREME
    if rsi > 70 and macd < 0:
        entry = price
        sl = high + range_candle * 0.5
        tp = entry - (sl - entry) * 1.5
        return "SHORT", entry, sl, tp, "Exhaustion Reversal"

    return None

# =========================
# AI CONFIRMATION (PROBABILITY)
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
    confidence = "HIGH" if score >= 65 else "MEDIUM" if score >= 55 else "LOW"
    return score, confidence

# =========================
# SCAN MARKET
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
    send(f"🤖 XAUUSD SCALPING BOT AKTIF\nMode: {MODE}\nTF: {TF}")

    last_scan = 0
    interval = 300 if TF == "M5" else 900

    while True:
        try:
            now = time.time()

            # ===== AUTO SCAN =====
            if now - last_scan > interval:
                last_scan = now
                price, rsi, macd, setup = scan(PAIR)

                if setup:
                    side, entry, sl, tp, reason = setup
                    prob, conf = ai_confirm(setup, rsi, macd)

                    if prob >= 55:
                        send(f"""
🎯 XAUUSD SIGNAL ({TF})

Direction: {side}
Entry: {round(entry,2)}
SL: {round(sl,2)}
TP: {round(tp,2)}

📉 RSI: {round(rsi,1)}
📊 MACD: {macd}

🧠 AI Win Probability: {prob}%
Confidence: {conf}

📌 Strategy:
Riski-style {reason}

⚠️ Risk max 1%
""")

            # ===== CHAT =====
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                timeout=20
            ).json()

            for u in r.get("result", []):
                chat_id = u["message"]["chat"]["id"]
                text = u["message"].get("text","").lower()

                if "gold" in text or "/xau" in text:
                    price, rsi, macd, _ = scan(PAIR)
                    send(f"""
📊 XAUUSD STATUS ({TF})
Price: {price}
RSI: {round(rsi,1)}
MACD: {macd}
Mode: {MODE}
""", chat_id)

            time.sleep(2)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":
    run_bot()
