
import sqlite3
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nexus_vault.db")

conn = sqlite3.connect(DB_PATH)
try:
    conn.execute("""
        INSERT INTO api_keys (key_id, owner_email, status, emailed, created_at) 
        VALUES ("nxr_test_123", "marquis_test@gmail.com", "active", 0, "2026-02-22")
    """)
    conn.commit()
    print("?? Test customer injected successfully!")
except Exception as e:
    print(f"? Error: {e}")
finally:
    conn.close()

