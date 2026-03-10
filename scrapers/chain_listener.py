import asyncio
import os
import base64
import struct
import time
from collections import deque
from solana.rpc.websocket_api import connect
from solders.pubkey import Pubkey
from dotenv import load_dotenv

# --- NEW: PERSISTENCE IMPORT ---
from core.database import TradingDatabase
db = TradingDatabase()

load_dotenv()

PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

class MintCache:
    def __init__(self, max_size=1000):
        self.seen_mints = set()
        self.history = deque()
        self.max_size = max_size

    def is_new(self, mint_address):
        if mint_address in self.seen_mints:
            return False
        self.seen_mints.add(mint_address)
        self.history.append(mint_address)
        if len(self.history) > self.max_size:
            oldest = self.history.popleft()
            self.seen_mints.remove(oldest)
        return True

class ListenerHealth:
    def __init__(self):
        self.dot_count = 0
        self.total_mints_seen = 0
        self.pump_fun_hits = 0
        self.start_time = time.time()
        self.logs_since_last_push = 0 # Track for DB updates
        self.mints_since_last_push = 0

    def report(self):
        elapsed = time.time() - self.start_time
        # PUSH TO DATABASE FOR LIFETIME TRACKING
        db.update_lifetime_stats(self.logs_since_last_push, self.mints_since_last_push)
        
        # NEW: Ping the service status so Admin shows "online"
        db.ping_service("firehose", "streaming") 
        
        self.logs_since_last_push = 0
        self.mints_since_last_push = 0

        print(f"\n\n--- 🛡️ SYSTEM HEALTH REPORT ---")
        print(f"⏱️ Uptime: {elapsed:.1f}s | Hardware: Intel Arc A770")
        print(f"📊 Logs Scanned: {self.dot_count}")
        print(f"🎯 Pump.fun Hits: {self.pump_fun_hits}")
        print(f"🔥 New Mints Found: {self.total_mints_seen}")
        print(f"📡 DATA PERSISTED TO C: DRIVE")
        print(f"-----------------------------------\n")

def extract_metadata(logs):
    """Hardened binary decoding to prevent Rust 'TryFromSliceError' panics."""
    for log in logs:
        if "Program data: " in log:
            try:
                # 1. Decode base64
                data_bytes = base64.b64decode(log.split("Program data: ")[1])
                
                # 🛡️ THE RUST PANIC FIX: Ensure exact byte length (56+ bytes)
                # Discriminator(8) + Mint(32) + vToken(8) + vSol(8) = 56
                if len(data_bytes) < 56:
                    continue 

                # 2. Safely extract Mint (8-40)
                mint_bytes = data_bytes[8:40]
                mint = str(Pubkey.from_bytes(mint_bytes))
                
                # 3. Extract Virtual Reserves
                v_token_reserves = struct.unpack('<Q', data_bytes[40:48])[0]
                v_sol_reserves = struct.unpack('<Q', data_bytes[48:56])[0]
                
                # 4. Handle Naming (Avoid generic 'SOL' symbols)
                data_str = data_bytes.decode('utf-8', errors='ignore')
                if "https://ipfs.io/ipfs/" in data_str:
                    uri = "https://ipfs.io/ipfs/" + data_str.split("https://ipfs.io/ipfs/")[1].split()[0]
                    name = f"Pump-{uri[-6:]}"
                    symbol = "PUMP"
                else:
                    uri = "Unknown"
                    name = f"Launch-{mint[:6]}"
                    symbol = f"TKN-{mint[:4]}"

                return {
                    "mint": mint, "name": name, "symbol": symbol, "uri": uri,
                    "virtual_token": v_token_reserves, "virtual_sol": v_sol_reserves
                }
            except Exception: continue
    return None

async def monitor_new_tokens(queue):
    health = ListenerHealth()
    dedupe = MintCache()
    wss_url = os.getenv("SOLANA_RPC_URL").replace("https://", "wss://")
    retry_delay = 1 
    
    while True:
        try:
            async with connect(wss_url, ping_interval=20, ping_timeout=20) as websocket:
                await websocket.logs_subscribe()
                await websocket.recv() 
                print(f"🛰️ [Connected] Monitoring live stream...")
                
                async for msg in websocket:
                    try:
                        val = msg[0].result.value
                        logs = val.logs
                        health.dot_count += 1
                        health.logs_since_last_push += 1
                        
                        if any(PUMP_FUN_PROGRAM in log for log in logs):
                            health.pump_fun_hits += 1
                            if any("Instruction: Create" in log for log in logs):
                                token_data = extract_metadata(logs)
                                if token_data and dedupe.is_new(token_data['mint']):
                                    health.total_mints_seen += 1
                                    health.mints_since_last_push += 1
                                    print(f"\n🔥 [MINT] {token_data['name']} | {token_data['mint'][:10]}...")
                                    await queue.put(token_data)
                                    
                        if health.dot_count % 1000 == 0: 
                            health.report()
                    except Exception: continue
        except Exception as e:
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

if __name__ == "__main__":
    test_queue = asyncio.Queue()
    try:
        asyncio.run(monitor_new_tokens(test_queue))
    except KeyboardInterrupt:
        print("\nStopping Listener...")