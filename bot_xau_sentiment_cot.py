from openai import OpenAI
import os, requests, re
from datetime import datetime

# ======================================================
# INIT
# ======================================================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ======================================================
# SESSION DETECTION
# ======================================================
hour_utc = datetime.utcnow().hour
if hour_utc < 7:
    session = "Asia"
elif hour_utc < 13:
    session = "London"
else:
    session = "New York"

# ======================================================
# SYSTEM PROMPT (FASE 1)
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence khusus XAUUSD.

PERAN:
- Menganalisa konteks market
- Membentuk narasi & skenario
- BUKAN memberi sinyal trading
- BUKAN eksekutor order

ATURAN:
- Gunakan data yang diberikan
- Jangan mengarang sumber
- Jangan meminta data ke user
- Fokus pada pemahaman market

GAYA:
- Jelas
- Masuk akal
- Profesional
"""

def ai(prompt):
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# DATA SOURCE (REAL – SEDERHANA DULU)
# ======================================================
def get_fundamental_calendar():
    # ganti dengan calendar real kamu
    return [
        {"event": "US CPI", "impact": "High", "time": "Today"},
        {"event": "Fed Speaker", "impact": "Medium", "time": "Upcoming"}
    ]

def get_price_data():
    # ganti dengan API real (broker / TradingView)
    return {
        "current": 4550,
        "high": 4620,
        "low": 4480,
        "trend_structure": "Higher High / Higher Low",
        "volatility": "High",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }

def get_retail_sentiment():
    try:
        url = "https://www.myfxbook.com/community/outlook/XAUUSD"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return None
        buy = re.search(r'Buy\s*<span[^>]*>(\d+)%', r.text)
        sell = re.search(r'Sell\s*<span[^>]*>(\d+)%', r.text)
        if not buy or not sell:
            return None
        return {
            "source": "MyFxBook",
            "buy": int(buy.group(1)),
            "sell": int(sell.group(1))
        }
    except:
        return None

def get_bank_bias():
    # konteks institusional sederhana (placeholder)
    return {
        "source": "COT / Bank Notes",
        "bias": "Bullish medium-term, cautious short-term"
    }

# ======================================================
# FASE 1 — AI MODULES
# ======================================================
def ai_market_narrative(price, fundamental, retail, bank, session):
    return ai(f"""
DATA:
Price: {price}
Fundamental: {fundamental}
Retail: {retail}
Institution: {bank}
Session: {session}

TUGAS:
Jelaskan NARASI market XAUUSD hari ini.
Fokus pada:
- Siapa yang dominan
- Karakter pergerakan
- Risiko utama
""")

def ai_scenario_tree(price, narrative, fundamental):
    return ai(f"""
DATA:
Price: {price}
Market Narrative: {narrative}
Fundamental Context: {fundamental}

TUGAS:
Buat SCENARIO TREE pergerakan XAUUSD.

FORMAT WAJIB:
Primary Scenario (dengan %):
Secondary Scenario (dengan %):
Tail Risk Scenario (dengan %):

Sebutkan arah & range harga.
""")

def ai_session_behavior(price, narrative, session):
    return ai(f"""
DATA:
Session: {session}
Price: {price}
Market Narrative: {narrative}

TUGAS:
Analisa perilaku harga khas sesi ini
dan implikasinya ke XAUUSD.
""")

# ======================================================
# REPORT BUILDER
# ======================================================
def build_report(narrative, scenario, session_behavior):
    return f"""
📊 XAUUSD MARKET INTELLIGENCE — FASE 1
Session: {session}

🧠 Market Narrative:
{narrative}

🌳 Scenario Tree:
{scenario}

🕒 Session Behavior:
{session_behavior}

⚠️ Catatan:
Laporan ini bersifat INTELLIGENCE.
Belum ada sinyal trading atau eksekusi.
""".strip()

# ======================================================
# TELEGRAM
# ======================================================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    price = get_price_data()
    fundamental = get_fundamental_calendar()
    retail = get_retail_sentiment()
    bank = get_bank_bias()

    narrative = ai_market_narrative(price, fundamental, retail, bank, session)
    scenario = ai_scenario_tree(price, narrative, fundamental)
    session_behavior = ai_session_behavior(price, narrative, session)

    report = build_report(narrative, scenario, session_behavior)
    send_telegram(report)
