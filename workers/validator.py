import asyncio
import sqlite3
import requests
from datetime import datetime, timedelta

class GroundTruthValidator:
    def __init__(self, db_path="trading_data.db"):
        self.db_path = db_path
        self.dexscreener_url = "https://api.dexscreener.com/latest/dex/tokens/"

    def get_pending_audits(self):
        """Finds tokens scanned over 4 hours ago that haven't been validated yet."""
        # 4 hours is enough time for a token to either establish itself or rug completely.
        cutoff_time = datetime.utcnow() - timedelta(hours=4)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT mint, risk_score FROM token_audits 
                WHERE actual_outcome = 'PENDING' AND timestamp <= ?
                LIMIT 20  -- Process in small batches to respect API limits
            """, (cutoff_time.strftime('%Y-%m-%d %H:%M:%S'),))
            return [dict(row) for row in c.fetchall()]

    async def check_live_status(self, mint: str) -> str:
        """Hits DexScreener to see if the coin is dead or alive."""
        url = f"{self.dexscreener_url}{mint}"
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url, timeout=5))
            
            if response.status_code != 200:
                return "UNKNOWN"
                
            data = response.json()
            pairs = data.get("pairs", [])
            
            # If there are no trading pairs, the liquidity was never added or completely pulled.
            if not pairs:
                return "HARD_RUG"
                
            # Grab the most active pair
            primary_pair = pairs[0]
            liquidity = float(primary_pair.get("liquidity", {}).get("usd", 0))
            price_change_6h = float(primary_pair.get("priceChange", {}).get("h6", 0))
            
            # Outcome Logic
            if liquidity < 1000:
                return "RUGGED_NO_LIQ"
            elif price_change_6h < -90:
                return "SLOW_BLEED"
            else:
                return "SURVIVED"
                
        except Exception as e:
            print(f"⚠️ [Validator] DexScreener check failed for {mint[:8]}: {e}")
            return "UNKNOWN"

    def save_outcome(self, mint: str, outcome: str):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE token_audits 
                SET actual_outcome = ?, validated_at = CURRENT_TIMESTAMP 
                WHERE mint = ?
            """, (outcome, mint))
            conn.commit()

    async def run_validation_cycle(self):
        """The main loop that runs quietly in the background."""
        while True:
            try:
                pending_tokens = self.get_pending_audits()
                if pending_tokens:
                    print(f"🔍 [Validator] Auditing the past: Checking {len(pending_tokens)} tokens from 4+ hours ago...")
                    
                    for token in pending_tokens:
                        mint = token['mint']
                        outcome = await self.check_live_status(mint)
                        
                        if outcome != "UNKNOWN":
                            self.save_outcome(mint, outcome)
                            
                        # Be polite to the free API
                        await asyncio.sleep(1)
                        
            except Exception as e:
                print(f"🚨 [Validator] Cycle Error: {e}")
                
            # Sleep for 15 minutes before checking the database again
            await asyncio.sleep(900)