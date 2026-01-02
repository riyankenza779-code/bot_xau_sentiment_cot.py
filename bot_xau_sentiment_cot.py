from openai import OpenAI
import os, requests, re, time
from datetime import datetime, timedelta

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
# REAL-TIME PRICE
# =========================
def get_xau_price():
    try:
        r = requests.post(
            "https://scanner.tradingview.com/symbol",
            json={"symbol": "OANDA:XAUUSD", "fields": ["last_price","change","change_percent"]},
            timeout=10
        ).json()["data"][0]["d"]
        return round(r[0],2), round(r[1],2), round(r[2],2)
    except:
        return None,None,None

# =========================
# RETAIL SENTIMENT
# =========================
def get_retail_sentiment():
    try:
        html = requests.get(
            "https://www.myfxbook.com/community/outlook/XAUUSD",
            headers={"User-Agent":"Mozilla/5.0"},timeout=15
        ).text
        buy = int(re.search(r'Buy\s*<span[^>]*>(\d+)%', html).group(1))
        sell = int(re.search(r'Sell\s*<span[^>]*>(\d+)%', html).group(1))
        return buy, sell
    except:
        return None

# =========================
# SCORE & CONFIDENCE
# =========================
def calculate_score(buy, sell):
    score = 50
    score += -15 if buy>=75 or sell>=75 else 10
    score += 15
    score = max(0,min(100,score))
    label = "Bullish" if score>=70 else "Netral" if score>=50 else "Bearish"
    return score, label

def confidence_score(retail, score):
    bullish = 50
    if retail:
        buy,sell = retail
        bullish += (sell-buy)*0.3
    bullish += (score-50)*0.4
    bullish = max(0,min(100,bullish))
    return round(bullish,1), round(100-bullish,1)

# =========================
# AI WEIGHTED PROBABILITY
# =========================
def ai_weighted_probability(bull, bear, score):
    bull_prob = bull*0.6 + score*0.4
    bull_prob = max(0,min(100,bull_prob))
    return round(bull_prob,1), round(100-bull_prob,1)

# =========================
# EXTREME
# =========================
def is_extreme(retail, score):
    if retail:
        b,s = retail
        if b>=80 or s>=80:
            return True
    return score>=80 or score<=20

# =========================
# MARKET MODE (AI)
# =========================
def market_mode():
    r = client.responses.create(
        model="gpt-4.1-mini",
        input="Tentukan Market Mode XAUUSD hari ini: Trending / Ranging / Volatile / Event-driven."
    )
    return r.output_text.strip()

# =========================
# ECONOMIC CALENDAR ALERT
# =========================
def check_calendar_alert(last_event_time):
    try:
        html = requests.get("https://www.forexfactory.com/calendar",timeout=15).text
        events = re.findall(r'calendar__event-title.*?>(.*?)<', html)
        impacts = re.findall(r'calendar__impact--high', html)

        if impacts and events:
            now = datetime.utcnow()
            if not last_event_time or now-last_event_time>timedelta(hours=1):
                return events[0], now
    except:
        pass
    return None, last_event_time

# =========================
# GPT ANALYSIS
# =========================
def get_analysis(price,chg,chg_pct,retail,score,label,bull,bear,prob_bull,prob_bear,mode):
    retail_text = f"Buy {retail[0]}% vs Sell {retail[1]}%" if retail else "N/A"
    prompt=f"""
📊 XAUUSD MARKET INSIGHT ({session})

💰 Price: {price}
📉 Change: {chg} ({chg_pct}%)

🧠 Market Mode:
{mode}

🔹 Retail:
{retail_text}

📊 Market Score:
{score}/100 ({label})

📈 Confidence:
Bullish {bull}% | Bearish {bear}%

🎯 Probabilitas Arah (AI Weighted):
Bullish {prob_bull}%
Bearish {prob_bear}%

🔹 Kesimpulan:
Tentukan bias utama dan risiko.
"""
    r=client.responses.create(model="gpt-4.1-mini",input=prompt)
    return r.output_text.strip()

# =========================
# TELEGRAM
# =========================
def send(chat_id,text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":chat_id,"text":text},
        timeout=20
    )

# =========================
# MAIN LOOP
# =========================
def run_bot():
    last_update=0
    last_extreme=False
    last_calendar=None
    last_check=0

    while True:
        now=time.time()

        # ===== AUTO ALERT =====
        if now-last_check>300:
            last_check=now
            retail=get_retail_sentiment()
            buy,sell=retail if retail else (0,0)
            score,_=calculate_score(buy,sell)
            price,_,_=get_xau_price()

            if is_extreme(retail,score) and not last_extreme:
                send(CHAT_ID,f"🚨 EXTREME ALERT\nXAUUSD {price}\nRetail {buy}/{sell}\nScore {score}")
                last_extreme=True
            if not is_extreme(retail,score):
                last_extreme=False

            event,last_calendar=check_calendar_alert(last_calendar)
            if event:
                send(CHAT_ID,f"🗓️ HIGH IMPACT EVENT ALERT\nEvent: {event}\n⚠️ Volatilitas tinggi segera.")

        # ===== CHAT =====
        r=requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update+1}",
            timeout=20
        ).json()

        if r.get("ok"):
            for u in r["result"]:
                last_update=u["update_id"]
                msg=u.get("message",{})
                text=msg.get("text","")
                chat_id=msg.get("chat",{}).get("id")

                if not text:
                    continue

                retail=get_retail_sentiment()
                buy,sell=retail if retail else (0,0)
                score,label=calculate_score(buy,sell)
                bull,bear=confidence_score(retail,score)
                prob_bull,prob_bear=ai_weighted_probability(bull,bear,score)
                price,chg,chg_pct=get_xau_price()
                mode=market_mode()

                if text.lower()=="/xau":
                    analysis=get_analysis(
                        price,chg,chg_pct,retail,score,label,
                        bull,bear,prob_bull,prob_bear,mode
                    )
                    send(chat_id,analysis)
                else:
                    send(chat_id,f"📊 Bias: Bullish {prob_bull}% | Bearish {prob_bear}%")

        time.sleep(1)

# =========================
# START
# =========================
if __name__=="__main__":
    run_bot()
