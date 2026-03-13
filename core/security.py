import time
import structlog
import redis.asyncio as redis
from fastapi import HTTPException, Request
from core.config import settings

logger = structlog.get_logger()

class SecurityShield:
    def __init__(self):
        # Establish the distributed connection
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        self.MAX_IP_HITS_PER_MIN = 120
        self.BAN_TIME = 600 
    
    def extract_ip(self, request: Request) -> str:
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip
        return request.client.host if request.client else "UNKNOWN"

    async def check_global_traffic(self, request: Request):
        """Layer 1: Distributed DDoS Protection via Redis"""
        ip = self.extract_ip(request)
        key = f"limit:ip:{ip}"
        ban_key = f"ban:ip:{ip}"

        if await self.redis.get(ban_key):
            raise HTTPException(status_code=429, detail="Global rate limit exceeded.")

        hits = await self.redis.incr(key)
        if hits == 1:
            await self.redis.expire(key, 60)

        if hits > self.MAX_IP_HITS_PER_MIN:
            await self.redis.set(ban_key, "banned", ex=self.BAN_TIME)
            logger.warning("distributed_ip_ban", ip=ip, hits=hits)
            raise HTTPException(status_code=429, detail="Global rate limit exceeded.")

    async def check_rate_limit(self, api_key: str, is_pro: bool = False):
        """Layer 2: Distributed API Quotas via Redis"""
        rate_limit = 600 if is_pro else 30
        key = f"limit:key:{api_key}"

        # Atomic increment and quota check
        requests = await self.redis.incr(key)
        if requests == 1:
            await self.redis.expire(key, 60)
        
        if requests > rate_limit:
            raise HTTPException(
                status_code=429, 
                detail=f"Tier limit exceeded. Max {rate_limit} req/min."
            )
        return True

shield = SecurityShield()