import requests
import sqlite3
import time
from datetime import datetime

# --- CONFIGURATION ---
DB_PATH = "data/training_data.sqlite"  # <--- Updated to save in the data folder
SEARCH_TERMS = ["pump", "sol", "doge", "cat", "pepe", "moon", "ai", "meme"]

def setup_database():
    """Creates a dedicated SQLite database strictly for training the NexusRisk A770 Engine."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS token_anatomy (
                mint TEXT PRIMARY KEY,
                name TEXT,
                symbol TEXT,
                has_website INTEGER,
                has_twitter INTEGER,
                has_telegram INTEGER,
                liquidity_usd REAL,
                market_cap_usd REAL,
                age_hours REAL,
                is_safe INTEGER 
            )
        """)
        conn.commit()

def fetch_and_label_tokens():
    """Scrapes DexScreener, analyzes the anatomy, and labels them as Safe (1) or Rug (0)."""
    print("🚀 Starting NexusRisk Historical Data Miner...")
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        total_processed = 0
        total_safe = 0
        total_rugs = 0

        for term in SEARCH_TERMS:
            print(f"\n📡 Scraping DexScreener for keyword: '{term}'...")
            url = f"https://api.dexscreener.com/latest/dex/search?q={term}"
            
            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                
                pairs = data.get('pairs', [])
                if not pairs:
                    continue
                    
                for pair in pairs:
                    # Only analyze Solana Pump.fun tokens
                    if pair.get('chainId') != 'solana':
                        continue
                        
                    mint = pair['baseToken']['address']
                    name = pair['baseToken']['name']
                    symbol = pair['baseToken']['symbol']
                    
                    # Extract Social/Metadata Anatomy
                    info = pair.get('info', {})
                    websites = info.get('websites', [])
                    socials = info.get('socials', [])
                    
                    has_website = 1 if len(websites) > 0 else 0
                    has_twitter = 1 if any(s.get('type') == 'twitter' for s in socials) else 0
                    has_telegram = 1 if any(s.get('type') == 'telegram' for s in socials) else 0
                    
                    # Extract Financials
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                    fdv = float(pair.get('fdv', 0))
                    
                    # Calculate Age
                    created_at = pair.get('pairCreatedAt', 0)
                    if created_at == 0:
                        continue
                    age_hours = (time.time() * 1000 - created_at) / (1000 * 60 * 60)
                    
                    # 🎯 THE GROUND TRUTH LABELING LOGIC
                    # If it's older than 2 hours and still has over $15k in liquidity, it survived the gauntlet.
                    # Otherwise, it's a dead coin / rug pull.
                    is_safe = 1 if (age_hours > 2 and liquidity > 15000) else 0
                    
                    if is_safe:
                        total_safe += 1
                    else:
                        total_rugs += 1

                    # Save to the training database
                    try:
                        c.execute("""
                            INSERT OR IGNORE INTO token_anatomy 
                            (mint, name, symbol, has_website, has_twitter, has_telegram, liquidity_usd, market_cap_usd, age_hours, is_safe)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (mint, name, symbol, has_website, has_twitter, has_telegram, liquidity, fdv, age_hours, is_safe))
                        total_processed += 1
                    except Exception as e:
                        pass
                        
                conn.commit()
                time.sleep(1) # Respect API rate limits
                
            except Exception as e:
                print(f"⚠️ Error fetching {term}: {e}")
                
        print("\n🏆 --- DATA MINING COMPLETE ---")
        print(f"Total Tokens Ingested: {total_processed}")
        print(f"Verified Safe Coins:   {total_safe}")
        print(f"Verified Rug Pulls:    {total_rugs}")
        print("--------------------------------")

if __name__ == "__main__":
    setup_database()
    fetch_and_label_tokens()