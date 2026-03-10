
import sqlite3
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nexus_vault.db")
conn = sqlite3.connect(DB_PATH)
try:
    conn.execute("""
        INSERT OR REPLACE INTO api_keys (key_id, owner_email, status, emailed) 
        VALUES ("nxr_test_123", "test@nexusrisk.ai", "active", 1)
    """)
    conn.commit()
    print("?? Test Key Authorized in Nexus Vault!")
except Exception as e:
    print(f"? Error: {e}")
finally:
    conn.close()

