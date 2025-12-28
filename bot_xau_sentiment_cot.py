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
# LEVEL 2 — SCORING
# =========================
def calculate_score(buy, sell):
    score = 50
    if buy >= 75 or sell >= 75:
        score -= 15
    else:
        score += 10
    score += 15  # COT bias (net long, cautious)
    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Netral"
    else:
        label = "Bearish Bias"
    return score, label

# =========================
# LEVEL 4 & 5 — AI-BASED MODE
# =========================
def get_ai_market_and_event_mode():
    prompt = """
Tentukan kondisi pasar emas (XAUUSD) HARI INI secara profesional.

KELUARAN WAJIB:
1) Market Mode: Trending / Ranging / Volatile / Event-driven
2) Event Context: Pre-Event / Event Day / Post-Event / Normal Day

PERTIMBANGAN:
- Fed & suku bunga
- Inflasi AS (CPI/PCE)
- Data tenaga kerja (NFP)
- Geopolitik
- Apakah mendekati / hari-H / pasca FOMC

FORMAT JAWABAN (PERSIS):
Market Mode: <isi>
Event Context: <isi>
"""
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return resp.output_text.strip()

# =========================
# GPT ANALYSIS (LEVEL 1–5)
# =========================
def get_analysis(retail, score, label, ai_modes):
    if retail:
        buy, sell = retail
        alert = " ⚠️ (Crowded Trade)" if buy >= 75 or sell >= 75 else ""
        retail_text = f"Buy {buy}% vs Sell {sell}%{alert}"
    else:
        retail_text = "Tidak tersedia (Myfxbook tidak dapat diakses)"

    prompt = f"""
Kamu adalah analis makro profesional (desk riset).

{ai_modes}

DATA TAMBAHAN:
- Retail Sentiment: {retail_text}
- Market Score: {score}/100 ({label})
- COT: Hedge fund masih net long emas, namun momentum melambat.

TUGAS:
Buat laporan XAUUSD ringkas, kontekstual, dan tegas.
Sesuaikan bahasa dengan Market Mode & Event Context.

FORMAT:
📊 XAUUSD Market Insight ({session})

🧠 Market Mode & Event:
{ai_modes}

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
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return resp.output_text

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )

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

    ai_modes = get_ai_market_and_event_mode()
    analysis = get_analysis(retail, score, label, ai_modes)
    send_telegram(analysis)
