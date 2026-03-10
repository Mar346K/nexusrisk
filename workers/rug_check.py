import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

class RugChecker:
    def __init__(self):
        self.jwt = os.getenv("RUGCHECK_JWT")
        self.base_url = "https://api.rugcheck.xyz/v1"
        self.headers = {
            "Authorization": f"Bearer {self.jwt}" if self.jwt else "",
            "Accept": "application/json"
        }

    async def quick_audit(self, token_data: dict) -> dict:
        mint_address = token_data.get('mint', '')
        
        # 1. Handle empty mints securely
        if not mint_address or mint_address == "MOCK_MINT":
            return {"status": "SAFE", "score": 0}

        url = f"{self.base_url}/tokens/{mint_address}/report"
        
        try:
            # 2. Try the REAL RugCheck API first
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(url, headers=self.headers, timeout=2.5)
            )
            
            if response.status_code == 200:
                data = response.json()
                raw_score = data.get('score', 0)
                normalized_score = min(int((raw_score / 10000) * 100), 100) if raw_score > 0 else 0
                if normalized_score == 0 and raw_score > 0:
                    normalized_score = 5
                return {"status": "SAFE" if normalized_score < 50 else "DANGER", "score": normalized_score}
                
            elif response.status_code in [400, 404]:
                print(f"⚡ [A770 Override] {mint_address[:8]} is too new for cloud APIs. Routing to Local Heuristics.")
                return self._local_heuristic_scan(token_data)
                
            else:
                print(f"⚠️ [RugCheck API] Status {response.status_code} for {mint_address[:8]}")
                return self._local_heuristic_scan(token_data)

        except Exception as e:
            print(f"⚠️ [API Timeout] Falling back to A770 Heuristics for {mint_address[:8]}")
            return self._local_heuristic_scan(token_data)

    def _local_heuristic_scan(self, token_data: dict) -> dict:
        """The Bare-Metal Brain: Scores tokens using A770-Optimized Data Weights"""
        score = 10  # Base risk
        
        name = token_data.get("name", "")
        symbol = token_data.get("symbol", "")
        uri = token_data.get("uri", "")
        v_sol = int(token_data.get("virtual_sol", 0))
        
        # --- A770 OPTIMIZED WEIGHTS (WEEK 2 META) ---
        # Optimizer calculated: Website (+26), Twitter (+22), Telegram (+26) = +74 Total Penalty
        if uri == "Unknown" or not str(uri).startswith("https://"):
            score += 74
            
        # Rule 2: Suspicious Naming / Bot Generators
        if len(name) < 2 or len(symbol) < 2:
            score += 20
        elif str(name).startswith("Launch-"):
            score += 15 
            
        # Rule 3: The Block 0 Dev Bundle (Pump.fun specific math)
        if v_sol > 35_000_000_000:
            score += 50 
            
        # Cap the score between 0 and 99
        final_score = min(score, 99)
        return {"status": "SAFE" if final_score < 50 else "DANGER", "score": final_score}