import pytest
import time
from fastapi import HTTPException
from core.security import SecurityShield

class MockRequest:
    """Mocks a FastAPI Request object to inject simulated Cloudflare IPs"""
    def __init__(self, ip):
        self.headers = {"CF-Connecting-IP": ip}
        self.client = None

def test_ip_blacklisting():
    shield = SecurityShield()
    req = MockRequest("192.168.1.1")

    # Simulate 120 rapid requests (the exact limit)
    for _ in range(120):
        shield.check_global_traffic(req)

    # The 121st request should trigger the auto-ban
    with pytest.raises(HTTPException) as excinfo:
        shield.check_global_traffic(req)

    assert excinfo.value.status_code == 429
    assert "Global rate limit exceeded" in excinfo.value.detail

def test_tier_rate_limiting():
    shield = SecurityShield()
    api_key = "nxr_test_key"

    # Standard Web tier limit is 30/min. Fire 30 requests.
    for _ in range(30):
        shield.check_rate_limit(api_key, is_pro=False)

    # 31st request should fail
    with pytest.raises(HTTPException) as excinfo:
        shield.check_rate_limit(api_key, is_pro=False)

    assert excinfo.value.status_code == 429
    assert "Max 30 requests" in excinfo.value.detail

def test_memory_management_bounds():
    shield = SecurityShield()
    
    # The cache is capped at 10,000 items. Let's push 10,005 unique IPs.
    for i in range(10005):
        req = MockRequest(f"10.0.0.{i}")
        shield.check_global_traffic(req)
        
    # The length of the cache MUST not exceed 10000, proving we are immune to OOM memory leaks.
    assert len(shield.ip_hits) <= 10000