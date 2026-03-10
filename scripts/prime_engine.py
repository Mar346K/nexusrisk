import sys
import os

# Add the project root to sys.path so it can find 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from core.cache_manager import global_cache


# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000/api/v1/token"
# In scripts/prime_engine.py
# Change the header to use your Admin Secret
HEADERS = {"X-API-Key": "nxr_admin_marquis_2026"}


def run_stress_test(limit=50):
    print(f"🚀 [NexusRisk] Priming the Engine with {limit} audits...")
    
    # 1. Try to get real mints from your 128GB RAM Cache
    try:
        live_mints = list(global_cache.tokens.keys())[:limit]
    except Exception:
        live_mints = []

    if not live_mints:
        print("📝 Cache empty, using simulation batch...")
        live_mints = ["6TatPGVEym789", "UKrXUmoYSt456", "LX3EVUVzyN123"] * (limit // 3)

    for i, mint in enumerate(live_mints):
        start_time = time.time()
        try:
            response = requests.get(f"{BASE_URL}/{mint}", headers=HEADERS)
            latency = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Audit {i+1}/{len(live_mints)}: {mint[:10]}... | Risk: {data['risk_score']} | {latency}ms")
            else:
                print(f"❌ Failed {mint}: {response.json().get('detail')}")
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
        
        time.sleep(0.2) 

if __name__ == "__main__":
    run_stress_test(limit=50)