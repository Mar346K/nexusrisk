# scripts/onboard_test_user.py
from core.database import db

# Register your simulation key so the Admin dashboard sees "1" Beta User
db.add_new_user("nxr_test_user_001", "marquis_test@example.com", plan="beta_tester")
print("✅ Test user onboarded. Refresh Admin Portal!")