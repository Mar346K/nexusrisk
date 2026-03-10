import requests
import json

# Your secure admin endpoint
url = "http://127.0.0.1:8000/api/v1/admin/accuracy"

# Passing your admin key in the header
headers = {
    "X-API-Key": "nxr_admin_marquis_2026"  # Make sure this matches the key in your server.py!
}

try:
    print("📡 Pinging Texas Node for Accuracy Stats...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("\n🏆 --- A770 GROUND TRUTH REPORT ---")
        print(f"Total Tokens Graded:   {data['total_audits_graded']}")
        print(f"Correct Predictions:   {data['correct_predictions']}")
        print(f"System Accuracy:       {data['system_accuracy_percentage']}%")
        print("------------------------------------\n")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

except Exception as e:
    print(f"Connection failed. Is the server running? Error: {e}")