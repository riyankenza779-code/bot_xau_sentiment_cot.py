from openai import OpenAI
import os, requests, time, math
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

PAIR = "OANDA:XAUUSD"
MODE = "SCALPING"  # SCALPING / INTRADAY

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
# PRICE + OHLC 15M
# =========================
def get_ohlc_15m(symbol):
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
def rsi(close, prev_close):
    gain = max(0, close - prev_close)
    loss = max(0, prev_close - close)
    if loss == 0:
        return 70
    rs = gain / loss
    return round(100 - (100 / (1 + rs)), 1)

def macd(close, open_):
    return round(close - open_, 2)

# =========================
# ENTRY LOGIC
# =========================
def generate_signal(price, open_, high, low, rsi_v, macd_v):
    # ---- BREAKOUT ----
    if price > high and rsi_v > 60 and macd_v > 0:
        entry = price
        sl = entry - (high - low)
        tp = entry + (entry - sl) * 2
        return "LONG", entry, sl, tp, "Breakout Bullish"

    # ---- REVERSAL ----
    if rsi_v < 30 and macd_v < 0:
        entry = price
        sl = low - (high - low) * 0.3
        tp = entry + (entry - sl) * 2
        return "LONG", entry, sl, tp, "Reversal Oversold"

    if rsi_v > 70 and macd_v < 0:
        entry = price
        sl = high + (high - low) * 0.3
        tp = entry - (sl - entry) * 2
        return "SHORT", entry, sl, tp, "Reversal Overbought"

    return None

# =========================
# AUTONOMOUS SCAN
# =========================
def scan_market(symbol):
    price, open_, high, low = get_ohlc_15m(symbol)
    prev_close = open_
    rsi_v = rsi(price, prev_close)
    macd_v = macd(price, open_)

    signal = generate_signal(price, open_, high, low, rsi_v, macd_v)

    return price, rsi_v, macd_v, signal

# =========================
# MAIN LOOP
# =========================
def run_bot():
    send("🤖 XAUUSD SCALPING BOT 15M AKTIF")

    last_signal_time = 0

    while True:
        try:
            now = time.time()

            # ---- AUTO SCAN SETIAP 15 MENIT ----
            if now - last_signal_time > 900:
                last_signal_time = now

                price, rsi_v, macd_v, signal = scan_market(PAIR)

                if signal:
                    side, entry, sl, tp, reason = signal

                    msg = f"""
🎯 XAUUSD SIGNAL ({MODE} 15M)

Direction: {side}
Entry: {round(entry,2)}
Stop Loss: {round(sl,2)}
Take Profit: {round(tp,2)}

📉 RSI: {rsi_v}
📊 MACD: {macd_v}

📌 Setup:
{reason}

⚠️ Risk max 1–2%
"""
                    send(msg)

            # ---- TELEGRAM CHAT ----
            r = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                timeout=20
            ).json()

            for u in r.get("result", []):
                chat_id = u["message"]["chat"]["id"]
                text = u["message"].get("text", "").lower()

                if "/xau" in text or "gold" in text:
                    price, rsi_v, macd_v, _ = scan_market(PAIR)
                    send(
                        f"""📊 XAUUSD STATUS (15M)
Price: {price}
RSI: {rsi_v}
MACD: {macd_v}
Mode: {MODE}
""",
                        chat_id
                    )

                if text == "/btc":
                    price, _, _, _ = scan_market("BINANCE:BTCUSDT")
                    send(f"₿ BTCUSDT Price: {price}", chat_id)

            time.sleep(2)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":
    run_bot()
