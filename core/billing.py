import sqlite3
import secrets
import datetime

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "nexus_vault.db")

def init_db():
    """Initializes a healthy, hardened database."""
    # The timeout=20 tells SQLite to wait if the file is busy instead of crashing
    conn = sqlite3.connect(DB_PATH, timeout=20) 
    cursor = conn.cursor()
    
    # WAL mode is much more stable for high-speed apps
    cursor.execute("PRAGMA journal_mode=WAL;") 
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id TEXT PRIMARY KEY,
            owner_email TEXT,
            stripe_customer_id TEXT,
            status TEXT,
            emailed INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_api_key(email: str, stripe_id: str):
    """Generates a unique API key and saves it to the vault."""
    new_key = f"nxr_live_{secrets.token_urlsafe(32)}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO api_keys (key_id, owner_email, stripe_customer_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (new_key, email, stripe_id, 'active', datetime.datetime.now())
    )
    conn.commit()
    conn.close()
    return new_key

def is_key_valid(key: str):
    """Checks if a key exists and is currently active."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM api_keys WHERE key_id = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result is not None and result[0] == 'active'

# Initialize the DB immediately when this script is first run
if __name__ == "__main__":
    init_db()
    print(f"✅ Nexus Vault Database initialized at {DB_PATH}")