import pytest
import os
from pydantic import ValidationError

def test_config_crashes_on_missing_secrets(monkeypatch):
    # Temporarily hide the environment variables to simulate a missing .env file
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    
    # Attempting to load the settings should now trigger a violent crash
    with pytest.raises(ValidationError) as excinfo:
        from core.config import Settings
        Settings()
        
    # Verify it caught the missing Stripe key
    assert "stripe_secret_key" in str(excinfo.value)