import sys
import os

# 1. FIX PATH: Add the project root (C:\AI\nexusrisk) to Python's search list
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import TradingDatabase
from datetime import datetime

def onboard_test_user():
    print("🛠️ [NexusRisk] Initializing Database Connection...")
    db = TradingDatabase()
    
    # 2. DEFINE THE TEST USER
    # This matches the TEST_USER_KEY in your server.py
    test_key = "nxr_test_user_001"
    test_email = "marquis_dev@nexusrisk.ai"
    
    print(f"👤 Registering User: {test_email}...")
    
    try:
        # 3. INSERT INTO DATABASE
        # We use the existing add_new_user method to ensure consistency with Stripe
        db.add_new_user(
            api_key=test_key,
            email=test_email,
            plan="BETA_DEVELOPER_ACCESS"
        )
        
        # 4. SET INITIAL PING
        # This makes the dashboard show they were "Active" recently
        db.ping_service("arc_a770", "idle", queue_depth=0)
        
        print(f"\n✅ SUCCESS: '{test_key}' is now authorized.")
        print("📊 Refresh your Admin Portal to see 'Beta Users: 1'.")
        
    except Exception as e:
        print(f"❌ FAILED to onboard user: {e}")

if __name__ == "__main__":
    onboard_test_user()