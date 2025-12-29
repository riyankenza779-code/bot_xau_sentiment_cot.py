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
# SCORING
# =========================
def calculate_score(buy, sell):
    score = 50
    if buy >= 75 or sell >= 75:
        score -= 15
    else:
        score += 10
    score += 15  # COT bias
    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Netral"
    else:
        label = "Bearish Bias"
    return score, label

# =========================
# LEVEL 4–5: AI MARKET & EVENT MODE
# =========================
def get_ai_market_and_event_mode():
    prompt = """
Tentukan kondisi pasar emas (XAUUSD) HARI INI tanggal 29 Desember 2025 update setiap hari setiap saat ketika ada perubahan https://id.tradingview.com

Output:
Market Mode: Trending / Ranging / Volatile / Event-driven
Event Context: Pre-Event / Event Day / Post-Event / Normal Day

Pertimbangkan Fed, inflasi, NFP, geopolitik, FOMC.

Format:
Market Mode: ...
Event Context: ...
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# =========================
# LEVEL 8: EXTREME ALERT
# =========================
def get_extreme_alert(retail, score):
    alerts = []

    if retail:
        buy, sell = retail
        if buy >= 80:
            alerts.append("Retail Buy ≥ 80% → Extreme Crowded Long")
        if sell >= 80:
            alerts.append("Retail Sell ≥ 80% → Extreme Crowded Short")

    if score >= 80:
        alerts.append("Market Score ≥ 80 → Overheated Bullish")
    if score <= 20:
        alerts.append("Market Score ≤ 20 → Capitulation Risk")

    if not alerts:
        return ""

    alert_text = "🚨 EXTREME MARKET ALERT\n"
    for a in alerts:
        alert_text += f"- {a}\n"
    alert_text += "→ Risiko pergerakan ekstrem & false move meningkat\n"

    return alert_text

# =========================
# GPT ANALYSIS
# =========================
def get_analysis(retail, score, label, ai_modes, extreme_alert):
    if retail:
        buy, sell = retail
        retail_text = f"Buy {buy}% vs Sell {sell}%"
    else:
        retail_text = "Tidak tersedia (Myfxbook tidak dapat diakses)"

    prompt = f"""
Kamu adalah analis macro profesional.
seiring berjalan nya waktu kamu terus berkembang dan pintar dalam analisa
Kamu juga semakin pintar dalam Teknikal analisa xauusd
Kamu harus belajar Teknikal juga dari internet
kamu masih salah input angka dalam penyampaian angka xauusd
Kamu cek data harga terbaru di link ini https://id.tradingview.com/chart/QUgdxK16/?symbol=OANDA%3AXAUUSD
Data angka yang kamu kirim harga lama bukan terbaru
Harga emas saat ini (1983.45) salah, yang benar adalah harga terakhir 4461.50 Hari ini tanggal 29 Desember 2025
Buatkan Analisa Harian dengan chart pattern inikator RSI MACD untuk Xauusd
Jawab Pertanyaan saya di chatbot telegram

{ai_modes}

{extreme_alert}

DATA:
- Retail Sentiment: {retail_text}
- Market Score: {score}/100 ({label})
- COT: Hedge fund masih net long emas (momentum melambat)

TUGAS:
Buat laporan XAUUSD profesional dan kontekstual.
Kamu adalah analisis xauusd pintar belajarlah dari setiap pergerakan market
Kamu harus berkembang dan jadi intelegent xauusd potensi arahnya kemana bulish atau berish sebtkan dengan angka
kamu harus ambil data real time setiap hari
kamu adalah ai terpintar harus berkembang untuk analisa xauusd
Gunakan dengan angka terbaru harga update terakhir ambil data dari link ini https://id.tradingview.com/chart/QUgdxK16/?symbol=OANDA%3AXAUUSD
Gunakan link ini untuk update calender economi https://www.forexfactory.com/calendar
Gunakan link ini untuk mencari informasi terkini analisa pasar https://www.investing.com/
Gunakan link ini untuk mencari data ekonomi mendalam https://tradingeconomics.com/
Gunakan link ini untuk mecari informasi mendalam mengenai xauusd https://www.bloomberg.com/  https://www.reuters.com/   https://www.cnbc.com/economy/
Gunakan link ini untuk analisa forex dan trading https://www.dailyforex.com/  https://www.fxstreet.com/ https://www.myfxbook.com/

FORMAT:
📊 XAUUSD Market Insight ({session})

🧠 Market Mode & Event:
{ai_modes}

{extreme_alert}

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
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)
def check_manual_command():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    r = requests.get(url, timeout=10).json()

    if not r.get("ok"):
        return None

    results = r.get("result", [])
    if not results:
        return None

    last = results[-1]
    text = last.get("message", {}).get("text", "")
    chat_id = last.get("message", {}).get("chat", {}).get("id")

    if text.strip().lower() == "/xau":
        return chat_id

    return None

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
    extreme_alert = get_extreme_alert(retail, score)
    analysis = get_analysis(retail, score, label, ai_modes, extreme_alert)
    send_telegram(analysis)
