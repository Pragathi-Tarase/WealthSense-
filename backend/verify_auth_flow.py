import requests
import time
from db_conn import SessionLocal, engine, Base
from models_db import OTP, User, ChatMessage

# API Base URL
BASE_URL = "http://127.0.0.1:8000"

def run_verification():
    print("🚀 Starting Verification...")
    
    # 0. Cleanup (Optional, for clean test)
    # in a real test we might drop tables, but here we'll just use a random email
    import random
    rand_id = random.randint(1000, 9999)
    email = f"testuser{rand_id}@example.com"
    password = "password123"
    
    print(f"👤 Testing with User: {email}")

    # 1. Register
    print("\n[1] Registering...")
    payload = {
        "name": "Test User",
        "email": email,
        "phone": "9876543210",
        "pan": "ABCDE1234F",
        "demat": "1201234567890123",
        "password": password
    }
    try:
        r = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        print(f"Response: {r.status_code} - {r.json().get('message')}")
        if r.status_code != 200:
            print("❌ Registration Failed")
            return
            
        # Get OTP from response (Dev mode) or DB
        dev_otp = r.json().get("dev_otp")
        if not dev_otp:
            # Fetch from DB logic if dev_otp invalid
             db = SessionLocal()
             otp_record = db.query(OTP).filter(OTP.email == email).first()
             dev_otp = otp_record.otp_code
             db.close()
             print(f"   (Retrieved OTP from DB: {dev_otp})")
        else:
            print(f"   (Got Dev OTP: {dev_otp})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. Verify Email
    print("\n[2] Verifying Email...")
    try:
        r = requests.post(f"{BASE_URL}/api/auth/verify-email", json={
            "email": email,
            "otp": dev_otp
        })
        print(f"Response: {r.status_code} - {r.json().get('message')}")
        
        if r.status_code != 200:
            print("❌ Verification Failed")
            return
            
        token = r.json().get("access_token")
        print("✅ Access Token Received")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 3. Login (Double Check)
    print("\n[3] Testing Login...")
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login-email", json={
            "email": email,
            "password": password
        })
        if r.status_code == 200:
            print("✅ Login Successful")
            token = r.json().get("access_token") # Refresh token
        else:
            print(f"❌ Login Failed: {r.text}")
            return
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 4. Send Chat
    print("\n[4] Sending Chat Message...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(f"{BASE_URL}/api/chat/send", json={
            "message": "Hello WealthSense!"
        }, headers=headers)
        
        if r.status_code == 200:
            print("✅ Chat Sent")
            # print(r.json())
        else:
            print(f"❌ Chat Failed: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 5. Get History
    print("\n[5] Retrieving Chat History...")
    try:
        r = requests.get(f"{BASE_URL}/api/chat/history", headers=headers)
        if r.status_code == 200:
            msgs = r.json().get("messages", [])
            print(f"✅ History Retrieved: {len(msgs)} messages found")
            print(f"   Last Message: {msgs[-1]['content'] if msgs else 'None'}")
        else:
             print(f"❌ History Failed: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_verification()
