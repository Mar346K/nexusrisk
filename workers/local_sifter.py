import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class LocalSifter:
    def __init__(self):
        self.rpc_url = os.getenv("SOLANA_RPC_URL")
        self.api_key = self.rpc_url.split('=')[-1] if '=' in self.rpc_url else ""
        # Blacklist of known bad funding sources or "rug" clusters
        self.blacklist = set() 

    async def get_wallet_reputation(self, dev_wallet):
        """
        Analyzes the developer's past 10 transactions for suspicious patterns.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                dev_wallet,
                {"limit": 10}
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.rpc_url, json=payload) as resp:
                    data = await resp.json()
                    signatures = data.get('result', [])
                    
                    if not signatures:
                        return {"status": "GHOST", "score": 0, "reason": "Fresh wallet (High Risk)"}

                    # Heuristic Analysis
                    tx_count = len(signatures)
                    recent_activity = signatures[0].get('blockTime', 0)
                    time_diff = (signatures[0].get('blockTime', 0) - signatures[-1].get('blockTime', 0))

                    # FLAG: Serial Creator (More than 5 launches in short time)
                    if tx_count >= 10 and time_diff < 3600: # 10 tx in 1 hour
                        return {"status": "SUSPICIOUS", "score": 80, "reason": "Serial Launcher Pattern"}

                    # FLAG: New Wallet funded just now
                    if tx_count < 3:
                        return {"status": "RISKY", "score": 60, "reason": "Low transaction history"}

                    return {"status": "NEUTRAL", "score": 20, "reason": "Standard activity detected"}

        except Exception as e:
            print(f"⚠️ [Sifter Error] Could not audit dev {dev_wallet[:6]}: {e}")
            return {"status": "ERROR", "score": 50, "reason": "API Timeout"}

    def is_blacklisted(self, address):
        return address in self.blacklist