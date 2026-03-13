import pytest
import asyncio
from core.security import SecurityShield
from core.config import settings

@pytest.mark.asyncio
async def test_redis_connection():
    shield = SecurityShield()
    # Test if we can ping our Redis instance
    # This proves the 'Sync' is alive
    is_alive = await shield.redis.ping()
    assert is_alive is True

@pytest.mark.asyncio
async def test_distributed_rate_limit():
    shield = SecurityShield()
    test_ip = "1.2.3.4"
    
    # Simulate a hit
    await shield.redis.delete(f"limit:{test_ip}") # Clean start
    
    # Fire 5 hits
    for _ in range(5):
        count = await shield.redis.incr(f"limit:{test_ip}")
    
    assert count == 5