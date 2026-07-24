from fastapi import FastAPI, Request, HTTPException, Body, Header
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional
from datetime import datetime, timedelta
from config import DEV_SHOW_OTP
import random
import jwt
import os
import requests
# import traceback (removed)
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from services.kyc_service import kyc_service
from services.otp_service import otp_service
from services.email_service import email_service
# Database imports
from db_conn import engine, SessionLocal, Base
from models_db import User, OTP
from sqlalchemy.orm import Session
from fastapi import Depends

from routes import news, chat, market, stocks, user, depository, dashboard, predictions
import bcrypt
import secrets


# =========================
# CONFIG
# =========================

from config import APP_SECRET_KEY, JWT_ALGORITHM, KITE_API_KEY, KITE_API_SECRET

APP_NAME = "WealthSense"
JWT_SECRET = APP_SECRET_KEY
JWT_ALGO = JWT_ALGORITHM
JWT_EXP_MINUTES = 60

KITE_LOGIN_URL = "https://kite.trade/connect/login?v=3"
KITE_TOKEN_URL = "https://api.kite.trade/session/token"

# =========================
# IDENTITY REGISTRY (KYC Simulation)
# =========================
# Format: { PAN_NUMBER: DEMAT_ACCOUNT_NUMBER }
USER_REGISTRY = {
    # --- ADD YOUR REAL CREDENTIALS HERE FOR TESTING ---
    # "ABCDE1234F": "1201010101010101", 
    
    "ABCDE1234F": "1201010101010101",
    "WSENS9876K": "1204567812345678",
    "SHREY1234M": "1601010101010101",
    "IQNPM6228K": "1208816002409452"
}

# =========================
# OTP STORE (In-Memory)
# =========================

# =========================
# APP INIT
# =========================

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTER INTEGRATION
# =========================
app.include_router(news.router)
app.include_router(chat.router)
app.include_router(market.router)
app.include_router(stocks.router)
app.include_router(user.router)
app.include_router(depository.router)
app.include_router(dashboard.router)
app.include_router(predictions.router)


# =========================
# IN-MEMORY STORES (DEV)
# =========================

otp_store: Dict[str, Dict] = {}
auth_state_store: Dict[str, Dict] = {}

# =========================
# MODELS
# =========================

class OTPRequest(BaseModel):
    pan: str
    demat: str

class OTPVerify(BaseModel):
    pan: str
    otp: str

# =========================
# UTILS
# =========================

def verify_pan(pan: str) -> bool:
    # Basic PAN format: 5 letters, 4 digits, 1 letter (10 total)
    return len(pan) == 10 and pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()

def verify_demat(demat: str) -> bool:
    return demat.isdigit() and len(demat) == 16

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def create_jwt(payload: dict) -> str:
    data = payload.copy()
    data["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXP_MINUTES)
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGO)

# =========================
# ROOT
# =========================

@app.get("/")
def root():
    return RedirectResponse(url="/index.html")

# =========================
# AUTH — OTP SEND
# =========================

@app.post("/api/auth/otp/send")
def send_otp(payload: OTPRequest):
    pan = payload.pan.upper().strip()
    demat = payload.demat.strip()

    if not verify_pan(pan):
        raise HTTPException(
            status_code=400,
            detail="Invalid PAN format. Must be 10 characters (e.g. ABCDE1234F)"
        )

    if not verify_demat(demat):
        raise HTTPException(
            status_code=400,
            detail="Invalid Demat number format (must be 16 digits)"
        )

    # --- IDENTITY VERIFICATION via KYC Service ---
    # Case 1: Existing local registry check (fallback)
    registered_demat = USER_REGISTRY.get(pan)
    if registered_demat and registered_demat != demat:
         raise HTTPException(
            status_code=403,
            detail="PAN found but Demat ID mismatch. Identity verification failed."
        )
    
    # Case 2: Deep check via External KYC (Digio)
    if not registered_demat:
        # If not in local list, attempt real-world KYC verification
        if not kyc_service.verify_pan_demat(pan, demat):
            raise HTTPException(
                status_code=403,
                detail="This PAN/Demat combination is not verified or does not exist in our records."
            )

    otp = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=5)

    # Retrieve name from vault if possible
    user_name = "User"
    vault_data = kyc_service._load_vault()
    for user in vault_data.get("verified_users", []):
        if user.get("pan") == pan:
            user_name = user.get("name", "User")
            break

    otp_store[pan] = {
        "otp": otp,
        "demat": demat,
        "name": user_name,
        "expires": expiry
    }

    # REAL DELIVERY (Twilio/Mock)
    otp_service.send_otp(pan, otp)

    response = {
        "status": "otp_sent"
    }
    
    # In dev mode, include OTP in response for easy testing
    from config import DEV_SHOW_OTP
    if DEV_SHOW_OTP:
        response["dev_otp"] = otp  # Only in development!
        response["message"] = f"OTP sent! (Dev Mode: {otp})"
    
    return response

# =========================
# AUTH — OTP VERIFY
# =========================

@app.post("/api/auth/otp/verify")
def verify_otp(payload: OTPVerify):
    pan = payload.pan.upper().strip()
    otp = payload.otp.strip()

    record = otp_store.get(pan)

    if not record:
        raise HTTPException(
            status_code=400,
            detail="OTP not found or expired"
        )

    if datetime.utcnow() > record["expires"]:
        otp_store.pop(pan, None)
        raise HTTPException(
            status_code=400,
            detail="OTP expired"
        )

    if record["otp"] != otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    # SUCCESS — issue JWT
    jwt_token = create_jwt({
        "provider": "pan_demat",
        "pan": pan,
        "email": f"{pan.lower()}@wealthsense.local", # Use PAN as unique email identifier
        "demat": record["demat"],
        "name": record.get("name", "User")
    })

    otp_store.pop(pan, None)

    return {
        "access_token": jwt_token,
        "pan": pan,
        "demat": record["demat"]
    }

# =========================
# PROTECTED TEST ROUTE
# =========================

@app.get("/api/me")
def get_me(token: str):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# =========================
# USER REGISTRATION SYSTEM (DB BACKED)
# =========================

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    pan: str
    demat: str
    password: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    otp: str

class EmailLoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/register")
async def register_user(req: RegistrationRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email OTP verification
    """
    email = req.email.lower()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user and existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate PAN format
        if not verify_pan(req.pan):
            raise HTTPException(status_code=400, detail="Invalid PAN format")
        
        # Validate Demat format
        if not verify_demat(req.demat):
            raise HTTPException(status_code=400, detail="Invalid Demat number")
        
        # Generate OTP
        otp_code = generate_otp()
        expiry = datetime.utcnow() + timedelta(minutes=10)
        
        # Store or Update OTP in DB
        otp_entry = db.query(OTP).filter(OTP.email == email).first()
        if otp_entry:
            otp_entry.otp_code = otp_code
            otp_entry.expires_at = expiry
        else:
            otp_entry = OTP(email=email, otp_code=otp_code, expires_at=expiry)
            db.add(otp_entry)
        
        # If user doesn't exist at all, create a temporary unverified record (optional strategy)
        # Or just wait until verification to create the User.
        # Strategy: Create unverified user now to store details.
        if not existing_user:
            hashed_pw = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
            new_user = User(
                name=req.name,
                email=email,
                phone=req.phone,
                pan=req.pan.upper(),
                demat=req.demat,
                password_hash=hashed_pw,
                is_verified=False
            )
            db.add(new_user)
        else:
            # Update provisional details in case they changed them before verifying
            existing_user.name = req.name
            existing_user.phone = req.phone
            existing_user.pan = req.pan.upper()
            existing_user.demat = req.demat
            existing_user.password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
        
        db.commit()
        
        # Send OTP email
        success = email_service.send_otp_email(email, otp_code, req.name)
        
        if not success and not DEV_SHOW_OTP:
             # In production we might rollback, but for now we proceed
             pass

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    return {
        "status": "otp_sent",
        "message": f"Verification code sent to {email}",
        "email": email,
        "dev_otp": otp_code if DEV_SHOW_OTP else None
    }

@app.post("/api/auth/verify-email")
async def verify_email_otp(req: EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Verify email with OTP and activate user account
    """
    email = req.email.lower()
    
    # Check OTP
    otp_record = db.query(OTP).filter(OTP.email == email).first()
    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP found. Please register again.")
    
    if datetime.utcnow() > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Please register again")
    
    if otp_record.otp_code != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Activate User
    user = db.query(User).filter(User.email == email).first()
    if not user:
         raise HTTPException(status_code=400, detail="User record not found")
    
    user.is_verified = True
    
    # Cleanup OTP
    db.delete(otp_record)
    db.commit()
    
    # Send welcome email
    email_service.send_welcome_email(email, user.name)
    
    # Create JWT token
    token = create_jwt({
        "id": user.id,
        "email": email,
        "name": user.name,
        "demat": user.demat,
        "pan": user.pan,
        "provider": "email"
    })
    
    print(f"[Registration] [OK] User verified: {email}")
    
    return {
        "status": "verified",
        "message": "Account created successfully",
        "access_token": token,
        "user": {
            "name": user.name,
            "email": email,
            "demat": user.demat
        }
    }

@app.post("/api/auth/login-email")
async def login_with_email(req: EmailLoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password
    """
    email = req.email.lower()
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not user.is_verified:
         raise HTTPException(status_code=401, detail="Email not verified. Please complete signup.")
    
    # Verify password
    if not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    token = create_jwt({
        "id": user.id,
        "email": email,
        "name": user.name,
        "demat": user.demat,
        "pan": user.pan,
        "provider": "email"
    })
    
    print(f"[Login] [OK] Email login: {email}")
    
    return {
        "access_token": token,
        "user": {
            "name": user.name,
            "email": email,
            "demat": user.demat
        }
    }

# =========================
# ZERODHA OAUTH INTEGRATION
# =========================

@app.get("/auth/broker/zerodha")
async def initiate_zerodha_oauth(authorization: Optional[str] = Header(None)):
    """
    Initiate Zerodha OAuth flow. User must be logged in first.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Please login first before connecting broker")
    
    try:
        # Verify user is authenticated
        token = authorization.split()[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_email = payload.get("email")
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        auth_state_store[state] = {
            "user_email": user_email,
            "created_at": datetime.utcnow()
        }
        
        # Redirect to Zerodha login
        redirect_url = (
            f"{KITE_LOGIN_URL}"
            f"&api_key={KITE_API_KEY}"
            f"&state={state}"
        )
        
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")


@app.get("/auth/broker/callback")
async def zerodha_oauth_callback(
    request_token: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None
):
    """
    OAuth callback from Zerodha after user authorizes the app.
    Exchanges request_token for access_token and stores it.
    """
    # Validate callback
    if status != "success" or not request_token:
        return RedirectResponse(
            url="/dashboard.html#error=broker_auth_failed&detail=Authorization_cancelled_or_failed"
        )
    
    # Verify state (CSRF protection)
    if state not in auth_state_store:
        return RedirectResponse(
            url="/dashboard.html#error=invalid_state&detail=Security_verification_failed"
        )
    
    user_email = auth_state_store[state]["user_email"]
    del auth_state_store[state]  # Cleanup
    
    try:
        # Exchange request_token for access_token
        import hashlib
        checksum = hashlib.sha256(
            (KITE_API_KEY + request_token + KITE_API_SECRET).encode()
        ).hexdigest()
        
        token_response = requests.post(
            KITE_TOKEN_URL,
            data={
                "api_key": KITE_API_KEY,
                "request_token": request_token,
                "checksum": checksum
            },
            timeout=10
        )
        
        token_data = token_response.json()
        
        if token_response.status_code != 200 or token_data.get("status") != "success":
            error_msg = token_data.get("message", "Token exchange failed")
            return RedirectResponse(
                url=f"/dashboard.html#error=token_exchange_failed&detail={error_msg}"
            )
        
        # Extract tokens
        access_token = token_data["data"]["access_token"]
        user_id = token_data["data"]["user_id"]
        user_name = token_data["data"]["user_name"]
        
        # Store in user database
        from services.user_service import UserService
        user = UserService.get_user(user_email) or {}
        user.update({
            "email": user_email,
            "broker": "zerodha",
            "broker_user_id": user_id,
            "broker_user_name": user_name,
            "broker_access_token": access_token,
            "broker_connected_at": datetime.utcnow().isoformat(),
            "provider": "zerodha"
        })
        UserService.save_user(user_email, user)
        
        print(f"[OAuth] [OK] Zerodha connected for {user_email} (User ID: {user_id})")
        
        # Redirect back to dashboard
        return RedirectResponse(
            url="/dashboard.html#success=broker_connected&broker=zerodha"
        )
        
    except Exception as e:
        print(f"[OAuth] Error: {str(e)}")
        return RedirectResponse(
            url=f"/dashboard.html#error=connection_error&detail={str(e)}"
        )


@app.post("/api/broker/disconnect")
async def disconnect_broker(authorization: Optional[str] = Header(None)):
    """
    Disconnect broker and remove access token.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        token = authorization.split()[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_email = payload.get("email")
        
        from services.user_service import UserService
        user = UserService.get_user(user_email)
        
        if user:
            # Remove broker tokens
            user.pop("broker_access_token", None)
            user.pop("broker_user_id", None)
            user.pop("broker", None)
            user["provider"] = "email"
            UserService.save_user(user_email, user)
            
        return {"status": "disconnected"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/broker/status")
async def get_broker_status(authorization: Optional[str] = Header(None)):
    """
    Check if user has connected broker and get connection details.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        token = authorization.split()[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_email = payload.get("email")
        
        from services.user_service import UserService
        user = UserService.get_user(user_email)
        
        if user and user.get("broker_access_token"):
            return {
                "connected": True,
                "broker": user.get("broker", "zerodha"),
                "user_id": user.get("broker_user_id"),
                "user_name": user.get("broker_user_name"),
                "connected_at": user.get("broker_connected_at")
            }
        
        return {"connected": False}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# STATIC FILES (FRONTEND)
# =========================

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
else:
    print(f"WARNING: Frontend path not found at {frontend_path}")
