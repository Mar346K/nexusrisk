import requests

url = "https://cleanup-aerial-marriage-clay.trycloudflare.com/api/v1/token/3kdDAMH2Yq..."
headers = {"X-API-Key": "nxr_live_xxxxxxx"}

response = requests.get(url, headers=headers)
print(response.json())