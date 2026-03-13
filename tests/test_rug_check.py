import pytest
from workers.rug_check import RugChecker

def test_local_heuristic_scan_safe():
    checker = RugChecker()
    # Mock a clean token
    token_data = {
        "name": "GoodCoin",
        "symbol": "GOOD",
        "uri": "https://example.com/metadata.json",
        "virtual_sol": 10_000_000_000
    }
    result = checker._local_heuristic_scan(token_data)
    
    assert result["score"] == 10  # Base risk only
    assert result["status"] == "SAFE"

def test_local_heuristic_scan_danger():
    checker = RugChecker()
    # Mock a highly suspicious token
    token_data = {
        "name": "A",                  # < 2 chars -> +20 points
        "symbol": "A",                # < 2 chars
        "uri": "Unknown",             # No valid URI -> +74 points
        "virtual_sol": 40_000_000_000 # > 35b limit -> +50 points
    }
    result = checker._local_heuristic_scan(token_data)
    
    assert result["score"] == 99      # Should cap at 99
    assert result["status"] == "DANGER"

@pytest.mark.asyncio
async def test_quick_audit_empty_mint():
    checker = RugChecker()
    # An empty or mock mint should immediately return SAFE (score 0)
    result = await checker.quick_audit({"mint": ""})
    assert result["score"] == 0
    assert result["status"] == "SAFE"