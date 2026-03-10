
import sqlite3
import smtplib
import os
import time
from email.message import EmailMessage
from dotenv import load_dotenv

print("?? [System] Notify script is initializing...")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "nexus_vault.db")

GMAIL_USER = "nexusriskapi@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD") 
API_DOCS_URL = "https://cleanup-aerial-marriage-clay.trycloudflare.com/docs"

def send_welcome_email(customer_email, api_key):
    msg = EmailMessage()
    msg.set_content(f"Welcome to NexusRisk API!\n\nYour key: {api_key}\nDocs: {API_DOCS_URL}")
    msg["Subject"] = "Your NexusRisk API Key"
    msg["From"] = GMAIL_USER
    msg["To"] = customer_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"? Email Failed: {e}")
        return False

def main_loop():
    print("?? [Notify] Monitoring Nexus Vault...")
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT key_id, owner_email FROM api_keys WHERE emailed = 0")
            rows = cursor.fetchall()
            
            for key_id, email in rows:
                print(f"?? Sending key to {email}...")
                if send_welcome_email(email, key_id):
                    cursor.execute("UPDATE api_keys SET emailed = 1 WHERE key_id = ?", (key_id,))
                    conn.commit()
                    print(f"? Success for {email}")
            
            conn.close()
        except Exception as e:
            print(f"?? Loop Error: {e}")
        time.sleep(10)

if __name__ == "__main__":
    main_loop()

