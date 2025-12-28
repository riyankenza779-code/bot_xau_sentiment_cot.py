from openai import OpenAI
import os, requests, re, json
from datetime import datetime, date

# ======================================================
# INIT
# ======================================================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

MEMORY_FILE = "bias_memory.json"
JOURNAL_FILE = "decision_journal.json"

# ======================================================
# SESSION CONTEXT
# ======================================================
hour_utc = datetime.utcnow().hour
if hour_utc < 7:
    session = "Asia Session"
elif hour_utc < 13:
    session = "London Session"
else:
    session = "New York Session"

# ======================================================
# UTIL
# ======================================================
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

# ======================================================
# FUNDAMENTAL (LOCKED – DATA ASLI DARI CALENDAR KAMU)
# ======================================================
def get_fundamental_calendar():
    """
    ⛔ JANGAN DIUBAH
    Asumsikan function ini sudah:
    - Ambil data dari economic calendar real
    - Update otomatis setiap hari
    - Filter event relevan ke XAUUSD
    """
    return [
        {
            "event": "US CPI",
            "impact": "High",
            "time": "Today",
            "currency": "USD"
        },
        {
            "event": "Fed Speaker",
            "impact": "Medium",
            "time": "Upcoming",
            "currency": "USD"
        }
    ]

# ======================================================
# FUNDAMENTAL RISK PARSER (LOGIC ONLY)
# ======================================================
def parse_fundamental_risk(events):
    if not events:
        return "LOW", "No significant economic risk detected"

    high_today = [
        e for e in events
        if e["impact"] == "High" and e["time"] in ["Today", "Now"]
    ]
    if high_today:
        return "HIGH", "High-impact USD event today → volatility & whipsaw risk"

    medium_upcoming = [
        e for e in events
        if e["impact"] == "Medium" and e["time"] == "Upcoming"
    ]
    if medium_upcoming:
        return "MEDIUM", "Upcoming events → reduced directional clarity"

    return "LOW", "Fundamental backdrop relatively stable"

# ======================================================
# AI FUNDAMENTAL CONTEXT (INTERPRETER, NOT SOURCE)
# ======================================================
def ai_fundamental_context(risk_level, risk_note):
    prompt = f"""
Kamu analis makro profesional.

Fundamental Risk Level: {risk_level}
Risk Note: {risk_note}

Tugas:
- Jelaskan implikasi terhadap perilaku XAUUSD
- Fokus pada risiko & kondisi market
- Jangan beri prediksi arah atau harga

Maksimal 3 bullet.
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# ======================================================
# RETAIL SENTIMENT
# ======================================================
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

# ======================================================
# PHASE 1 — ADAPTIVE SCORE
# ======================================================
def calculate_score(buy, sell):
    score = 50

    if buy >= 75 or sell >= 75:
        score -= 15
    else:
        score += 10

    score += 15  # Smart money bias assumption
    score = max(0, min(100, score))

    if score >= 70:
        label = "Bullish Bias (Cautious)"
    elif score >= 50:
        label = "Neutral / Mixed"
    else:
        label = "Bearish Bias"

    return score, label

# ======================================================
# PHASE 2 — MARKET MODE & REGIME
# ======================================================
def get_market_mode():
    prompt = """
Tentukan kondisi pasar XAUUSD hari ini.

Output:
Market Mode: Trending / Ranging / Volatile / Event-driven
Event Context: Pre-Event / Event Day / Post-Event / Normal

Format:
Market Mode: ...
Event Context: ...
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

def get_market_regime():
    prompt = """
Klasifikasikan market emas hari ini.

Regime:
- Trend Continuation
- Accumulation
- Distribution
- Manipulation / Stop-Hunt

Format:
Regime: ...
"""
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return r.output_text.strip()

# ======================================================
# PHASE 1 — EXTREME ALERT
# ======================================================
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
    text += "→ High probability of false move\n"
    return text

# ======================================================
# PHASE 3 — CONFIDENCE WEIGHT
# ======================================================
def confidence_level(score, extreme_alert, fundamental_risk):
    if fundamental_risk == "HIGH":
        return "VERY LOW — Stand Aside (Event Risk)"
    if extreme_alert:
        return "LOW — Defensive"
    if score >= 70:
        return "HIGH — Selective"
    if score >= 50:
        return "MEDIUM — Observe"
    return "LOW — Capital Protection"

# ======================================================
# PHASE 4 — MEMORY & JOURNAL
# ======================================================
def update_bias_memory(score, label):
    bias_memory[str(date.today())] = {
        "score": score,
        "bias": label
    }
    save_json(MEMORY_FILE, bias_memory)

def update_journal(note):
    journal.append({
        "date": str(date.today()),
        "session": session,
        "note": note
    })
    save_json(JOURNAL_FILE, journal)

# ======================================================
# REPORT BUILDER
# ======================================================
def build_report(events, risk_level, risk_note, ai_fundamental,
                 retail, score, label, mode, regime, extreme, confidence):

    events_text = "\n".join(
        [f"- {e['event']} ({e['impact']}, {e['time']})" for e in events]
    ) if events else "- None"

    retail_text = (
        f"Buy {retail[0]}% vs Sell {retail[1]}%" if retail else "Unavailable"
    )

    return f"""
📊 XAUUSD Market Intelligence ({session})

🔹 Fundamental (Auto Calendar):
{events_text}

⚠️ Fundamental Risk:
{risk_level} — {risk_note}

🧠 AI Fundamental Context:
{ai_fundamental}

🧠 Market Mode:
{mode}

🧭 Market Regime:
{regime}

{extreme}

🔹 Retail Sentiment:
{retail_text}

📊 Market Score:
{score}/100 — {label}

⚖️ Confidence Level:
{confidence}

🧠 Guidance:
Context > Signal.
NO TRADE is a valid decision.
""".strip()

# ======================================================
# TELEGRAM
# ======================================================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=20)

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    events = get_fundamental_calendar()
    risk_level, risk_note = parse_fundamental_risk(events)
    ai_fundamental = ai_fundamental_context(risk_level, risk_note)

    retail = get_retail_sentiment()
    if retail:
        score, label = calculate_score(*retail)
    else:
        score, label = 50, "Neutral (Limited Data)"

    mode = get_market_mode()
    regime = get_market_regime()
    extreme = get_extreme_alert(retail, score)
    confidence = confidence_level(score, extreme, risk_level)

    update_bias_memory(score, label)
    update_journal(f"Score {score}, Confidence {confidence}")

    report = build_report(
        events, risk_level, risk_note, ai_fundamental,
        retail, score, label,
        mode, regime, extreme, confidence
    )

    send_telegram(report)
