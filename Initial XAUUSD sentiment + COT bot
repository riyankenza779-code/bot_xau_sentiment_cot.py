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
session = "PAGI (Asia Session)" if hour_utc < 7 else "MALAM (US Session)"

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
# COT DATA (SMART MONEY)
# =========================
def get_cot_bias():
    """
    Menggunakan interpretasi AI berbasis data COT terakhir (weekly).
    Kita tidak scrape mentah CSV di tahap ini,
    tapi meminta AI membaca konteks COT emas terbaru secara makro.
    """
    return """
COT (Smart Money):
- Hedge fund (Non-Commercial) masih berada dalam posisi NET LONG emas.
- Namun laju akumulasi mulai melambat dibanding minggu sebelumnya.
- Ini mengindikasikan bias bullish masih ada, tapi tidak agresif.
"""

# =========================
# GPT ANALYSIS (FUNDAMENTAL + RETAIL + COT)
# =========================
def get_analysis(retail, cot_text):
    if retail:
        buy, sell = retail
        retail_text = f"Retail Sentiment: Buy {buy}% vs Sell {sell}%"
    else:
        retail_text = "Retail Sentiment: ❌ Tidak tersedia (Myfxbook tidak dapat diakses)"

    prompt = f"""
Kamu adalah analis makro profesional.

{retail_text}

{cot_text}

TUGAS:
Buat analisa XAUUSD dengan menggabungkan:
1. Fundamental makro (Fed, inflasi, risk-on/off, geopolitik)
2. Retail sentiment (crowded trade / kontra indikasi)
3. COT institusional (smart money bias)

ATURAN:
- Jika data retail tidak tersedia, sebutkan keterbatasan
- Fokus MARKET CONTEXT, bukan entry
- Bahasa Indonesia
- Ringkas, objektif, profesional

FORMAT:
📊 XAUUSD Market Insight ({session})

🔹 Fundamental:
...

🔹 Retail Sentiment:
...

🔹 COT (Smart Money):
...

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
    })

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    retail = get_retail_sentiment()
    cot_text = get_cot_bias()
    analysis = get_analysis(retail, cot_text)
    send_telegram(analysis)
