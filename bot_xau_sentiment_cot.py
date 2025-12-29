from openai import OpenAI
import os
from datetime import datetime

# ======================================================
# INIT
# ======================================================
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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
# SYSTEM PROMPT (OTAK AI)
# ======================================================
SYSTEM_PROMPT = """
Kamu adalah AI Market Intelligence khusus XAUUSD.

PERAN UTAMA:
- Menganalisa KONTEKS market
- Membentuk NARASI market
- Menyusun SKENARIO masa depan
- Membaca PERILAKU sesi

BATASAN:
- BUKAN eksekutor order
- BUKAN sistem alert realtime
- BUKAN scalping bot

ATURAN:
- Gunakan data yang diberikan
- Jangan mengarang sumber
- Jangan meminta data ke user
- Berpikir sebagai analis institusi

GAYA:
- Tenang
- Tegas
- Masuk akal
- Tidak sensasional
"""

def ai(prompt: str) -> str:
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=SYSTEM_PROMPT + "\n" + prompt
    )
    return r.output_text.strip()

# ======================================================
# INTELLIGENCE MODULES
# ======================================================

def market_narrative(price, fundamental, retail, bank):
    """
    Menjawab: hari ini market sedang apa & siapa dominan
    """
    return ai(f"""
DATA:
Price: {price}
Fundamental: {fundamental}
Retail Sentiment: {retail}
Institutional Bias: {bank}
Session: {session}

TUGAS:
Buat MARKET NARRATIVE XAUUSD hari ini.

FOKUS:
- Siapa yang dominan (retail / institusi / event)
- Karakter pergerakan (tenang, agresif, manipulatif)
- Risiko utama yang perlu diwaspadai
""")

def scenario_tree(price, narrative, fundamental):
    """
    Multi masa depan, bukan satu arah
    """
    return ai(f"""
DATA:
Price: {price}
Market Narrative: {narrative}
Fundamental Context: {fundamental}

TUGAS:
Susun SCENARIO TREE XAUUSD.

FORMAT WAJIB:
Primary Scenario (dengan probabilitas %):
Secondary Scenario (dengan probabilitas %):
Tail Risk Scenario (dengan probabilitas %):

Sebutkan arah dan range harga.
""")

def session_behavior(price, narrative):
    """
    Perilaku khas sesi berjalan
    """
    return ai(f"""
DATA:
Session: {session}
Price Action: {price}
Market Narrative: {narrative}

TUGAS:
Analisa PERILAKU SESI {session} untuk XAUUSD.

FOKUS:
- Apakah sesi ini cenderung range, continuation, atau reversal
- Implikasi ke bias intraday
""")

# ======================================================
# PUBLIC INTERFACE
# ======================================================
def run_intelligence(price, fundamental, retail, bank):
    """
    Fungsi utama yang DIPANGGIL oleh:
    - watchdog (setelah alert)
    - report harian
    - manual trigger
    """
    narrative = market_narrative(price, fundamental, retail, bank)
    scenario = scenario_tree(price, narrative, fundamental)
    behavior = session_behavior(price, narrative)

    return {
        "session": session,
        "market_narrative": narrative,
        "scenario_tree": scenario,
        "session_behavior": behavior,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }

# ======================================================
# TEST MODE (OPTIONAL)
# ======================================================
if __name__ == "__main__":
    # dummy data untuk test otak
    price = {
        "current": 4550,
        "high": 4620,
        "low": 4480,
        "trend": "Higher High / Higher Low",
        "volatility": "High"
    }

    fundamental = [
        {"event": "US CPI", "impact": "High", "time": "Today"},
        {"event": "Fed Speaker", "impact": "Medium", "time": "Upcoming"}
    ]

    retail = {
        "source": "MyFxBook",
        "buy": 78,
        "sell": 22
    }

    bank = {
        "source": "COT / Bank Notes",
        "bias": "Bullish medium-term, cautious short-term"
    }

    intel = run_intelligence(price, fundamental, retail, bank)

    print("=== MARKET NARRATIVE ===")
    print(intel["market_narrative"])
    print("\n=== SCENARIO TREE ===")
    print(intel["scenario_tree"])
    print("\n=== SESSION BEHAVIOR ===")
    print(intel["session_behavior"])
