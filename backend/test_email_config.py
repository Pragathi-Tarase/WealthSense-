
import smtplib
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

print(f"Testing Email Config:")
print(f"Host: {EMAIL_HOST}")
print(f"Port: {EMAIL_PORT}")
print(f"User: {EMAIL_USER}")
print(f"Password starts with: {EMAIL_PASSWORD[:2]}..." if EMAIL_PASSWORD else "None")

try:
    print(f"Connecting to {EMAIL_HOST}:{EMAIL_PORT}...")
    server = smtplib.SMTP(EMAIL_HOST, int(EMAIL_PORT))
    server.starttls()
    print("Logging in...")
    server.login(EMAIL_USER, EMAIL_PASSWORD)
    print("✅ Login Successful!")
    server.quit()
except Exception as e:
    print(f"❌ Connection Failed: {e}")
