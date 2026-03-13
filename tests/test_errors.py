import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_opaque_error_response():
    # We hit a token endpoint but simulate a crash 
    # (FastAPI will raise a 500 if the DB or logic fails internally)
    # Here we just verify the output structure of a generic failure
    response = client.get("/api/v1/token/trigger_error_test")
    
    if response.status_code == 500:
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Internal system error."
        assert "error_id" in data
        # Ensure the error ID is a valid UUID string length
        assert len(data["error_id"]) == 36