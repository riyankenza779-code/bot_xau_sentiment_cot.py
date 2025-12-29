import os
import time
import requests
from datetime import datetime

# ======================================================
# TELEGRAM CONFIG
# ======================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ======================================================
# PRICE SOURCE (WAJIB GANTI KE DATA REAL)
# ======================================================
def get_price():
    """
    GANTI dengan source REAL:
    - Broker API (MT5, cTrader, dll)
    - TradingView webhook
    - Gold / Metals price API
    """
    # ===== DUMMY (UNTUK TEST SAJA) =====
    return 4550.0

# ======================================================
# TELEGRAM SENDER
# ======================================================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10
    )
    print("TELEGRAM:", r.status_code, r.text)

# ======================================================
# WATCHDOG SETTINGS
# ======================================================
CHECK_INTERVAL = 60        # detik (1 menit)
DUMP_THRESHOLD = -0.8      # % drop
SPIKE_THRESHOLD = 0.8     # % spike

# ======================================================
# WATCHDOG CORE
# ======================================================
def watchdog():
    last_price = None

    send_telegram(
        "🟢 XAUUSD WATCHDOG AKTIF\n"
        "Monitoring real-time dimulai\n"
        "Status: ANTI MC MODE 😎"
    )

    while True:
        try:
            price = get_price()
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            if last_price is not None:
                change_pct = (price - last_price) / last_price * 100

                # 🚨 DUMP ALERT
                if change_pct <= DUMP_THRESHOLD:
                    send_telegram(
                        f"🚨 XAUUSD DUMP ALERT\n"
                        f"Time: {now}\n"
                        f"Drop: {change_pct:.2f}%\n"
                        f"Price: {last_price} → {price}\n"
                        f"⚠️ Volatilitas ekstrem terdeteksi"
                    )

                # 🚀 SPIKE ALERT
                elif change_pct >= SPIKE_THRESHOLD:
                    send_telegram(
                        f"🚀 XAUUSD SPIKE ALERT\n"
                        f"Time: {now}\n"
                        f"Spike: +{change_pct:.2f}%\n"
                        f"Price: {last_price} → {price}\n"
                        f"⚠️ Momentum agresif terdeteksi"
                    )

            last_price = price
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            send_telegram(f"❌ WATCHDOG ERROR\n{e}")
            time.sleep(60)

# ======================================================
# MAIN
# ======================================================
if __name__ == "__main__":
    watchdog()
