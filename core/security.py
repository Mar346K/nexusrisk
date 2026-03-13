import time
from fastapi import HTTPException, Request
from cachetools import TTLCache
import structlog

# Initialize the structured logger
logger = structlog.get_logger()

class SecurityShield:
    def __init__(self):
        # LAYER 2: API Key Sliding Window (Business Logic)
        # Cap at 10,000 active keys, auto-evict memory after 60 seconds of inactivity
        self.key_history = TTLCache(maxsize=10000, ttl=60)
        self.window = 60  # 1 minute window

        # LAYER 1: IP Blacklist & Spam Tracking (DDoS Protection)
        # Cap at 10,000 active IPs, auto-evict memory after 10 minutes
        self.ip_hits = TTLCache(maxsize=10000, ttl=600)
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
            # Structured JSON Security Audit Log
            logger.warning(
                "ip_auto_banned", 
                ip_address=ip, 
                duration_sec=self.BAN_TIME, 
                reason="rate_limit_exceeded"
            )
            raise HTTPException(status_code=429, detail="Global rate limit exceeded. Try again in 10 minutes.")

    def check_rate_limit(self, api_key: str, is_pro: bool = False):
        """Layer 2: Enforces commercial SaaS quotas based on payment tier."""
        now = time.time()
        
        # Pros get 600 req/min (10/sec). Web Traders get 30 req/min (1 request every 2s).
        rate_limit = 600 if is_pro else 30
        
        # Initialize the list for this key if it doesn't exist in the cache yet
        if api_key not in self.key_history:
            self.key_history[api_key] = []

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