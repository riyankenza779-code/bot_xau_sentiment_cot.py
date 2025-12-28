from openai import OpenAI
import os
import requests
import re
import json
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "sentiment_state.json"

# =========================
# SESSION
# =========================
hour_utc = datetime.utcnow().hour
session = "PAGI – Asia Session" if hour_utc < 7 else "MALAM – US Session"

# =========================
# RETAIL SENTIMENT
# =========================
def get_retail_sentiment():
    try:
        url = "https://www.myfxbook.com/community/outlook/XAUUSD"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None

        html = r.text
        buy = re.search(r'Buy\s*<span[^>]*>(\d+)%', html)
        sell = re.search(r'Sell\s*<span[^>]*>(\d+)%', html)

        if not buy or not sell:
            return None

        buy = int(buy.group(1))
        sell = int(sell.group(1))
        if buy + sell != 100:
            return None

        return buy, sell
    except Exception:
        return None

# =========================
# LOAD / SAVE STATE (LEVEL 3)
# =========================
def load_previous_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_state(buy, sell):
    with open(STATE_FILE, "w") as f:
        json.dump({"buy": buy, "sell": sell}, f)

# =========================
# SCORING (LEVEL 2)
# =========================
def calculate_score(buy, sell):
    score = 50

    if buy >= 75 or sell >= 75:
        score -= 15
    else:
        score += 10

    score += 15  # COT bullish bias
    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Netral"
    else:
        label = "Bearish Bias"

    return score, label

# =========================
# DELTA SENTIMENT (LEVEL 3)
# =========================
def get_delta_text(current, previous):
    if not previous:
        return "Belum ada data pembanding (run pertama)."

    delta = current - previous

    if abs(delta) >= 10:
        return f"⚠️ Perubahan agresif: {previous}% → {current}% ({delta:+d}%)"
    elif abs(delta) >= 5:
        return f"Perubahan moderat: {previous}% → {current}% ({delta:+d}%)"
    else:
        return f"Perubahan kecil: {previous}% → {current}% ({delta:+d}%)"

# =========================
# GPT ANALYSIS
# =========================
def get_analysis(retail, delta_text, score, label):
    if retail:
        buy, sell = retail
        alert = " ⚠️ (Crowded Trade)" if buy >= 75 or sell >= 75 else ""
        retail_text = f"Buy {buy}% vs Sell {sell}%{alert}"
    else:
        retail_text = "Tidak tersedia (Myfxbook tidak dapat diakses)"

    prompt = f"""
Kamu adalah analis makro profesional.

DATA:
- Retail Sentiment: {retail_text}
- Delta Retail: {delta_text}
- Market Score: {score}/100 ({label})
- COT: Hedge fund masih net long emas (bias bullish namun melambat)

TUGAS:
Buat analisa XAUUSD yang menekankan perubahan SENTIMENT, bukan hanya levelnya.

ATURAN:
- Bahasa Indonesia
- Fokus market context
- Ringkas, tegas
- Tanpa entry

FORMAT:
📊 XAUUSD Market Insight ({session})

🔹 Fundamental:
...

🔹 Retail Sentiment:
{retail_text}

🔹 Perubahan Sentiment:
{delta_text}

🔹 COT (Smart Money):
...

📊 Market Score:
{score}/100 — {label}

🔹 AI Conclusion:
...
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return response.output_text

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    }, timeout=20)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    retail = get_retail_sentiment()
    prev = load_previous_state()

    if retail:
        buy, sell = retail
        score, label = calculate_score(buy, sell)

        prev_buy = prev["buy"] if prev else None
        delta_text = get_delta_text(buy, prev_buy)

        save_state(buy, sell)
    else:
        score, label = 50, "Netral (Data Terbatas)"
        delta_text = "Delta tidak tersedia karena data retail gagal diambil."

    analysis = get_analysis(retail, delta_text, score, label)
    send_telegram(analysis)
