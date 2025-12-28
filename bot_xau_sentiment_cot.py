from openai import OpenAI
import os, requests, re, json
from datetime import datetime, date

# =========================
# INIT
# =========================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

MEMORY_FILE = "bias_memory.json"
JOURNAL_FILE = "decision_journal.json"

# =========================
# SESSION CONTEXT
# =========================
hour_utc = datetime.utcnow().hour
if hour_utc < 7:
    session = "Asia Session"
elif hour_utc < 13:
    session = "London Session"
else:
    session = "New York Session"

# =========================
# UTIL MEMORY
# =========================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

bias_memory = load_json(MEMORY_FILE, {})
journal = load_json(JOURNAL_FILE, [])

# =========================
# PHASE 1 — RETAIL SENTIMENT
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

        buy, sell = int(buy.group(1)), int(sell.group(1))
        if buy + sell != 100:
            return None

        return buy, sell
    except:
        return None

# =========================
# PHASE 1 — ADAPTIVE SCORE
# =========================
def calculate_score(buy, sell):
    score = 50

    # Retail crowding
    if buy >= 75 or sell >= 75:
        score -= 15
    else:
        score += 10

    # Smart money bias (static macro assumption)
    score += 15

    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Neutral / Mixed"
    else:
        label = "Bearish Bias"

    return score, label

# =========================
# PHASE 2 — MARKET REGIME
# =========================
def get_market_regime():
    prompt = """
Klasifikasikan market emas (XAUUSD) hari ini.

Output:
Regime:
- Trend Continuation
- Accumulation
- Distribution
- Manipulation / Stop-Hunt

Berbasis konteks makro & perilaku harga.
Format:
Regime: ...
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# =========================
# PHASE 1–2 — MARKET MODE & EVENT
# =========================
def get_market_mode_and_event():
    prompt = """
Tentukan kondisi pasar emas (XAUUSD) hari ini.

Output:
Market Mode: Trending / Ranging / Volatile / Event-driven
Event Context: Pre-Event / Event Day / Post-Event / Normal Day

Pertimbangkan Fed, CPI, NFP, geopolitik.
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
# PHASE 1 — EXTREME ALERT
# =========================
def get_extreme_alert(retail, score):
    alerts = []

    if retail:
        buy, sell = retail
        if buy >= 80:
            alerts.append("Retail Buy ≥ 80% → Crowded Long")
        if sell >= 80:
            alerts.append("Retail Sell ≥ 80% → Crowded Short")

    if score >= 80:
        alerts.append("Market Score ≥ 80 → Overheated")
    if score <= 20:
        alerts.append("Market Score ≤ 20 → Capitulation Risk")

    if not alerts:
        return ""

    text = "🚨 EXTREME MARKET ALERT\n"
    for a in alerts:
        text += f"- {a}\n"
    text += "→ Risiko false move & volatility spike\n"
    return text

# =========================
# PHASE 3 — CONFIDENCE WEIGHT
# =========================
def confidence_level(score, extreme_alert):
    if extreme_alert:
        return "LOW — Stand Aside"
    if score >= 70:
        return "HIGH — Selective"
    if score >= 50:
        return "MEDIUM — Observe"
    return "LOW — Defensive"

# =========================
# PHASE 4 — MEMORY UPDATE
# =========================
def update_bias_memory(score, label):
    today = str(date.today())
    bias_memory[today] = {
        "score": score,
        "bias": label
    }
    save_json(MEMORY_FILE, bias_memory)

def update_journal(summary):
    journal.append({
        "date": str(date.today()),
        "session": session,
        "note": summary
    })
    save_json(JOURNAL_FILE, journal)

# =========================
# FINAL ANALYSIS
# =========================
def build_report(retail, score, label, mode_event, regime, extreme, confidence):
    if retail:
        buy, sell = retail
        retail_text = f"Buy {buy}% vs Sell {sell}%"
    else:
        retail_text = "Unavailable"

    report = f"""
📊 XAUUSD Market Intelligence ({session})

🧠 Market Context:
{mode_event}

🧭 Market Regime:
{regime}

{extreme}

🔹 Retail Sentiment:
{retail_text}

🔹 Smart Money (COT):
Hedge funds masih net-long, momentum melambat

📊 Market Score:
{score}/100 — {label}

⚖️ Confidence Level:
{confidence}

🧠 AI Guidance:
Fokus pada konteks & risiko.
NO TRADE adalah keputusan valid.
"""
    return report.strip()

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    retail = get_retail_sentiment()

    if retail:
        buy, sell = retail
        score, label = calculate_score(buy, sell)
    else:
        score, label = 50, "Neutral (Limited Data)"

    mode_event = get_market_mode_and_event()
    regime = get_market_regime()
    extreme = get_extreme_alert(retail, score)
    confidence = confidence_level(score, extreme)

    update_bias_memory(score, label)

    report = build_report(
        retail, score, label,
        mode_event, regime,
        extreme, confidence
    )

    update_journal(f"Score {score}, Confidence {confidence}")
    send_telegram(report)
