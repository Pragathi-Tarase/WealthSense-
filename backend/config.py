import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file if it exists
if load_dotenv():
    print("[Config] .env file loaded successfully.")
else:
    print("[Config] No .env file found or failed to load. Using hardware/env defaults.")

# JWT Configuration
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
OTP_EXPIRY_SECONDS = int(os.environ.get("OTP_EXPIRY_SECONDS", "300"))

# App Secrets
APP_SECRET_KEY = os.environ.get(
    "APP_SECRET_KEY",
    "7dbdd1794bb7bbfa99a2b167c79cb1154753c13dbf1fb734855de99077abe077e603e89a19fbcbbff3c5bd83b5cec84d61e63ff2ecb994df754b0292bee8dbd1",
)
SESSION_SECRET = os.environ.get(
    "SESSION_SECRET",
    "6249278396b6e5af09828520bf59511955173bebf1fa4225fddb2cdd4b152b3f",
)

# Dev Flags
# Dev Flags
DEV_SHOW_OTP = os.environ.get("DEV_SHOW_OTP", "").lower() == "true"
ALLOW_ANY_EMAIL = os.environ.get("ALLOW_ANY_EMAIL", "").lower() == "true"

# Frontend Base URL
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://127.0.0.1:8000")

# MongoDB Configuration
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "wealthsense")

# API Keys
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "9IIR8AU4911R8FVM")
NEWSAPI_API_KEY = os.environ.get("NEWSAPI_API_KEY", "pub_9d29784c88d64861b24efc0876e11f18")

# OAuth Broker Credentials
KITE_API_KEY = os.environ.get("KITE_API_KEY", "5cxnwkpqkv3pgd5e")
KITE_API_SECRET = os.environ.get("KITE_API_SECRET", "toj7rx7shwn1rmhqwvdw5cuoybumvsbf")

# AI Settings
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Email Service Configuration
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "WealthSense")

# Database Configuration
# Default to MAMP MySQL (root/root on port 8889)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "mysql+pymysql://root:root@localhost:8889/wealthsense"
)
