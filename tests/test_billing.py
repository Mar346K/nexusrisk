import pytest
import os
import core.billing as billing_module

# OVERRIDE the database path for tests only
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_nexus_vault.db")
billing_module.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
def setup_test_database():
    """Runs before every test: creates a clean DB. Runs after: destroys it."""
    billing_module.init_db()
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_api_key_lifecycle():
    email = "test_ops@nexusrisk.ai"
    stripe_id = "cus_mock_999"

    # 1. Generate Key
    new_key = billing_module.generate_api_key(email, stripe_id)
    assert new_key.startswith("nxr_live_")
    
    # 2. Validate Active Key
    assert billing_module.is_key_valid(new_key) is True
    
    # 3. Validate Fake Key
    assert billing_module.is_key_valid("nxr_fake_key_000") is False