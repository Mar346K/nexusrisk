import sqlite3
import aiosqlite
import secrets
import datetime
import os
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "nexus_vault.db")

# A system-wide salt prevents rainbow-table attacks. 
# In production, set this in your .env file.
API_SALT = os.getenv("API_SALT", "nexus_strict_ops_salt").encode()

def init_db():
    """Initializes a healthy, hardened database."""
    conn = sqlite3.connect(DB_PATH, timeout=20) 
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode=WAL;") 
    
    # Schema updated: key_id is now key_hash
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash TEXT PRIMARY KEY,
            owner_email TEXT,
            stripe_customer_id TEXT,
            status TEXT,
            emailed INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_api_key(raw_key: str) -> str:
    """Cryptographically hashes the key so it is never stored in plaintext."""
    return hashlib.sha256(API_SALT + raw_key.encode()).hexdigest()

async def generate_api_key_async(email: str, stripe_id: str) -> str:
    """Generates a unique API key, hashes it, and saves it to the vault asynchronously."""
    new_key = f"nxr_live_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(new_key)
    
    async with aiosqlite.connect(DB_PATH, timeout=20) as db:
        await db.execute(
            "INSERT INTO api_keys (key_hash, owner_email, stripe_customer_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (hashed_key, email, stripe_id, 'active', datetime.datetime.now().isoformat())
        )
        await db.commit()
        
    # We return the raw key ONLY ONCE to the user.
    return new_key

async def is_key_valid_async(key: str) -> bool:
    """Asynchronously checks if a key exists and is currently active using its hash."""
    if not key:
        return False
        
    hashed_key = hash_api_key(key)
    
    async with aiosqlite.connect(DB_PATH, timeout=20) as db:
        async with db.execute("SELECT status FROM api_keys WHERE key_hash = ?", (hashed_key,)) as cursor:
            result = await cursor.fetchone()
            return result is not None and result[0] == 'active'

if __name__ == "__main__":
    init_db()
    print(f"✅ Nexus Vault Database initialized securely at {DB_PATH}")