import sqlite3
import time
from datetime import datetime

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "trading_data.db")

def generate_report(iteration):
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Missing DB at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    
    try:
        # Check for the correct table name we found earlier
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='token_audits'")
        if not cursor.fetchone():
            print("⏳ Table 'token_audits' not found yet. Hit the API to birth it!")
            return

        cursor.execute("SELECT COUNT(*) FROM token_audits WHERE risk_score < 50")
        confirmed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM token_audits WHERE risk_score >= 50")
        rejected = cursor.fetchone()[0]
        
        total = confirmed + rejected
        
        print(f"\n--- 📊 NEXUSRISK 10-MIN AUDIT (Check {iteration}) ---")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ CONFIRMED (Safe): {confirmed}")
        print(f"❌ REJECTED (Rug): {rejected}")
        print(f"📈 Total: {total}")
        
        if total > 0:
            rug_rate = round((rejected / total) * 100, 1)
            print(f"📣 Marketing Hook: 'NexusRisk has successfully filtered {rug_rate}% of detected rugs in the last 10 minutes.'")
        
        print("------------------------------------------------------\n")
    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🧐 [NexusRisk] Performance Analyst is now ON DUTY (10-minute heartbeat).")
    check_count = 1
    while True: # Run indefinitely so you don't have to restart it
        generate_report(check_count)
        check_count += 1
        time.sleep(600) # 600 seconds = 10 minutes