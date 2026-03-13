import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from api.server import app

# We use FastAPI's built-in TestClient to simulate WebSocket connections
client = TestClient(app)

def test_ws_rejects_no_key():
    # Expecting a disconnect because we didn't provide a key
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/feed"):
            pass
    assert exc_info.value.code == 1008

def test_ws_rejects_invalid_key():
    # Expecting a disconnect because the key is garbage
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/feed?api_key=hacker_fake_key"):
            pass
    assert exc_info.value.code == 1008

def test_ws_accepts_valid_key():
    # 'nxr_test_pro' is your hardcoded system test key
    # If this connects without raising an error, the bouncer let us in
    with client.websocket_connect("/ws/feed?api_key=nxr_test_pro") as websocket:
        assert websocket is not None