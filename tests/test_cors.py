from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from api.server import app

client = TestClient(app)

@patch('api.server.shield.check_global_traffic', new_callable=AsyncMock)
def test_cors_allowed_origin(mock_shield):
    headers = {
        "Origin": "https://nexusrisk.ai",
        "Access-Control-Request-Method": "GET"
    }
    response = client.options("/llms.txt", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

@patch('api.server.shield.check_global_traffic', new_callable=AsyncMock)
def test_cors_rejected_origin(mock_shield):
    headers = {"Origin": "https://malicious-scraper.com"}
    response = client.get("/llms.txt", headers=headers)
    # The malicious scraper should NOT get the allow-origin header
    assert "access-control-allow-origin" not in response.headers