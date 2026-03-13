import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_cors_allowed_origin():
    headers = {"Origin": "http://localhost:8000"}
    # Hit the public LLM discovery route
    response = client.get("/llms.txt", headers=headers)
    
    assert response.status_code == 200
    # The API should explicitly grant access to this origin
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:8000"

def test_cors_rejected_origin():
    headers = {"Origin": "https://malicious-scraper.com"}
    response = client.get("/llms.txt", headers=headers)
    
    # For unauthorized origins, FastAPI drops the CORS headers completely.
    # When the browser sees these headers are missing, it blocks the response payload.
    assert "access-control-allow-origin" not in response.headers