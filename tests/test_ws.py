import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from api.server import app

client = TestClient(app)

def test_ws_rejects_no_key():
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/feed"):
            pass

@patch('api.server.is_key_valid_async', new_callable=AsyncMock)
def test_ws_rejects_invalid_key(mock_is_valid):
    # Mock the DB so we don't crash in GitHub's sterile environment
    mock_is_valid.return_value = False
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/feed?api_key=hacker_fake_key"):
            pass

def test_ws_accepts_valid_key():
    # We use a system key here to naturally bypass the DB check
    with client.websocket_connect("/ws/feed?api_key=nxr_test_pro") as websocket:
        assert websocket is not None