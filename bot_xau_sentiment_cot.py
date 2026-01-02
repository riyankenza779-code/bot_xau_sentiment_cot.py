from openai import OpenAI
import os
import requests
import re
import time
from datetime import datetime

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

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
# CONFIDENCE SCORE
# =========================
def confidence_score(retail, score):
    bullish = 50

    if retail:
        buy, sell = retail
        bullish += (sell - buy) * 0.3

    bullish += (score - 50) * 0.4
    bullish = max(0, min(100, bullish))
    bearish = 100 - bullish

    return round(bullish, 1), round(bearish, 1)

# =========================
# AI MARKET MODE
# =========================
def get_ai_market_and_event_mode():
    prompt = """
Tentukan kondisi pasar emas (XAUUSD) hari ini.

Output:
Market Mode: Trending / Ranging / Volatile / Event-driven
Event Context: Pre-Event / Event Day / Post-Event / Normal Day

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
# EXTREME ALERT
# =========================
def is_extreme_condition(retail, score):
    if retail:
        buy, sell = retail
        if buy >= 80 or sell >= 80:
            return True
    if score >= 80 or score <= 20:
        return True
    return False

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

    text = "🚨 EXTREME MARKET ALERT\n"
    for a in alerts:
        text += f"- {a}\n"
    text += "→ Risiko false move meningkat\n"

    return text

# =========================
# GPT ANALYSIS
# =========================
def get_analysis(retail, score, label, ai_modes, extreme_alert, bullish, bearish):
    if retail:
        buy, sell = retail
        retail_text = f"Buy {buy}% vs Sell {sell}%"
    else:
        retail_text = "Tidak tersedia"

    prompt = f"""
Buat analisa XAUUSD profesional & ringkas.

FORMAT:

📊 XAUUSD Market Insight ({session})

🧠 Market Mode & Event:
{ai_modes}

{extreme_alert}

🔹 Retail Sentiment:
{retail_text}

📊 Market Score:
{score}/100 — {label}

📈 Confidence:
Bullish {bullish}%
Bearish {bearish}%

🔹 Kesimpulan AI:
Sebutkan bias arah dan risiko utama.
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# =========================
# AI CHAT REPLY
# =========================
def ai_reply(user_text, context):
    prompt = f"""
Kamu adalah AI analis XAUUSD Telegram Bot.
Jawab dengan singkat, jelas, dan to the point.

DATA KONTEKS:
{context}

PERTANYAAN USER:
{user_text}
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# =========================
# TELEGRAM
# =========================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)

# =========================
# MAIN LOOP
# =========================
def run_bot():
    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}"
            r = requests.get(url, timeout=30).json()

            if not r.get("ok"):
                continue

            for update in r["result"]:
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")

                if not text:
                    continue

                retail = get_retail_sentiment()
                buy, sell = retail if retail else (0, 0)
                score, label = calculate_score(buy, sell)
                bullish, bearish = confidence_score(retail, score)
                ai_modes = get_ai_market_and_event_mode()
                extreme_alert = get_extreme_alert(retail, score)

                context = f"""
Retail: Buy {buy}% Sell {sell}%
Market Score: {score}
Bullish: {bullish}%
Bearish: {bearish}%
Session: {session}
"""

                if text.lower() == "/xau":
                    if is_extreme_condition(retail, score):
                        send_message(chat_id, "⚠️ Market ekstrem terdeteksi. Gunakan risk kecil.")

                    analysis = get_analysis(
                        retail, score, label,
                        ai_modes, extreme_alert,
                        bullish, bearish
                    )
                    send_message(chat_id, analysis)
                else:
                    reply = ai_reply(text, context)
                    send_message(chat_id, reply)

            time.sleep(1)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":
    run_bot()
