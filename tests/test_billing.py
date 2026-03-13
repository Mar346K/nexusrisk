import pytest
import os
import core.billing as billing_module

# OVERRIDE the database path for tests only
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_nexus_vault.db")
billing_module.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
def setup_test_database():
    """Runs before every test: creates a clean DB. Runs after: destroys it."""
    # Wipe any lingering DB to ensure a clean schema
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    billing_module.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass # Windows might hold the file lock briefly

def test_api_key_hashing():
    raw_key = "nxr_live_test123"
    hashed = billing_module.hash_api_key(raw_key)
    
    assert hashed != raw_key
    assert len(hashed) == 64  # SHA-256 output is 64 hex characters
    assert billing_module.hash_api_key(raw_key) == hashed  # Deterministic check

@pytest.mark.asyncio
async def test_api_key_lifecycle_async():
    email = "test_ops@nexusrisk.ai"
    stripe_id = "cus_mock_999"

    # 1. Generate Key (Async)
    new_key = await billing_module.generate_api_key_async(email, stripe_id)
    assert new_key.startswith("nxr_live_")
    
    # 2. Validate Active Key (Async)
    is_valid = await billing_module.is_key_valid_async(new_key)
    assert is_valid is True
    
    # 3. Validate Fake Key (Async)
    is_fake_valid = await billing_module.is_key_valid_async("nxr_fake_key_000")
    assert is_fake_valid is False