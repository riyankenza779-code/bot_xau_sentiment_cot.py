from openai import OpenAI
import os
import requests
import re
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# =========================
# SESSION
# =========================
hour_utc = datetime.utcnow().hour
session = "PAGI – Asia Session" if hour_utc < 7 else "MALAM – US Session"

# =========================
# RETAIL SENTIMENT (MYFXBOOK)
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
# SCORING SYSTEM (LEVEL 2)
# =========================
def calculate_score(buy, sell):
    score = 50  # base neutral

    # Retail contra logic
    if buy >= 75:
        score -= 15
    elif sell >= 75:
        score -= 15
    else:
        score += 10

    # Smart money bias (COT static for now)
    score += 15  # hedge fund net long bias

    # Clamp score
    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Netral"
    else:
        label = "Bearish Bias"

    return score, label

# =========================
# GPT ANALYSIS
# =========================
def get_analysis(retail, score, label):
    if retail:
        buy, sell = retail
        alert = ""
        if buy >= 75 or sell >= 75:
            alert = " ⚠️ (Crowded Trade)"

        retail_text = f"Buy {buy}% vs Sell {sell}%{alert}"
    else:
        retail_text = "Tidak tersedia (Myfxbook tidak dapat diakses)"

    prompt = f"""
Kamu adalah analis makro profesional.

TUGAS:
Buat analisa XAUUSD dengan gaya laporan desk riset.

DATA:
- Retail Sentiment: {retail_text}
- Market Score: {score}/100 ({label})
- COT: Hedge fund masih net long emas (bias bullish namun melambat)

ATURAN:
- Fokus market context
- Bahasa Indonesia
- Ringkas, tegas, profesional
- Tanpa rekomendasi entry

FORMAT:
📊 XAUUSD Market Insight ({session})

🔹 Fundamental:
...

🔹 Retail Sentiment:
{retail_text}

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

    if retail:
        buy, sell = retail
        score, label = calculate_score(buy, sell)
    else:
        score, label = 50, "Netral (Data Terbatas)"

    analysis = get_analysis(retail, score, label)
    send_telegram(analysis)
