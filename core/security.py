import time
from fastapi import HTTPException, Request
from collections import defaultdict

class SecurityShield:
    def __init__(self):
        # LAYER 2: API Key Sliding Window (Business Logic)
        self.key_history = defaultdict(list)
        self.window = 60  # 1 minute window

        # LAYER 1: IP Blacklist & Spam Tracking (DDoS Protection)
        self.ip_hits = {}
        self.MAX_IP_HITS_PER_MIN = 120  # Max traffic before auto-ban
        self.BAN_TIME = 600  # 10 minutes in the shadow realm

    def extract_ip(self, request: Request) -> str:
        """Safely extracts the REAL IP from Cloudflare's secure headers."""
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip
        return request.client.host if request.client else "UNKNOWN"

    def check_global_traffic(self, request: Request):
        """Layer 1: Prevents DDoS and brute-force attacks at the router level."""
        ip = self.extract_ip(request)
        
        # Uncomment this in production to strictly enforce your Cloudflare tunnel
        # if not request.headers.get("CF-Connecting-IP") and ip != "127.0.0.1":
        #     raise HTTPException(status_code=403, detail="Direct IP access forbidden.")

        now = time.time()

        # Clean up old records to prevent RAM bloat
        if ip in self.ip_hits:
            record = self.ip_hits[ip]
            if record['banned_until'] and now > record['banned_until']:
                self.ip_hits.pop(ip)  # Ban expired, forgive them
            elif now - record['start_time'] > 60:
                # A minute has passed, reset their hit count
                self.ip_hits[ip] = {'hits': 1, 'start_time': now, 'banned_until': None}
            else:
                record['hits'] += 1
        else:
            self.ip_hits[ip] = {'hits': 1, 'start_time': now, 'banned_until': None}

        record = self.ip_hits[ip]

        # Enforce active bans
        if record['banned_until'] and now < record['banned_until']:
            raise HTTPException(status_code=429, detail="IP temporarily banned for excessive malicious requests.")

        # Trigger new ban if they spam
        if record['hits'] > self.MAX_IP_HITS_PER_MIN:
            record['banned_until'] = now + self.BAN_TIME
            print(f"🚨 [SHIELD] Auto-Banned IP: {ip} for 10 minutes.")
            raise HTTPException(status_code=429, detail="Global rate limit exceeded. Try again in 10 minutes.")

    def check_rate_limit(self, api_key: str, is_pro: bool = False):
        """Layer 2: Enforces commercial SaaS quotas based on payment tier."""
        now = time.time()
        
        # Pros get 600 req/min (10/sec). Web Traders get 30 req/min (1 request every 2s).
        rate_limit = 600 if is_pro else 30
        
        # Keep only requests from the last 60 seconds
        self.key_history[api_key] = [
            t for t in self.key_history[api_key] if now - t < self.window
        ]
        
        if len(self.key_history[api_key]) >= rate_limit:
            raise HTTPException(
                status_code=429, 
                detail=f"Rate limit exceeded. Max {rate_limit} requests/min for your tier."
            )
        
        self.key_history[api_key].append(now)
        return True

shield = SecurityShield()