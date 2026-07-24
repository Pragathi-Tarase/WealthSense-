import json
import os
from typing import Dict, Optional, Any
from models import UserProfileResponse

# In-memory mock database backed by file
USER_DB: Dict[str, Dict] = {}
DB_FILE = "users.json"

class UserService:
    # Valid Demo Demat IDs (16-digit numeric for CDSL)
    VALID_DEMO_DEMATS = [
        "1201010101010101",
        "1201010123456789",
        "8888888888888888",
    ]

    @staticmethod
    def _load_db():
        """Load DB from file if it exists."""
        global USER_DB
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r") as f:
                    USER_DB = json.load(f)
                print(f"[UserService] Loaded {len(USER_DB)} users from {DB_FILE}")
            except Exception as e:
                print(f"[UserService] Error loading DB: {e}")

    @staticmethod
    def _save_db():
        """Save DB to file."""
        try:
            with open(DB_FILE, "w") as f:
                json.dump(USER_DB, f, indent=2)
            print(f"[UserService] Saved DB to {DB_FILE}")
        except Exception as e:
            print(f"[UserService] Error saving DB: {e}")

    @staticmethod
    def verify_demat(email: str, demat: str) -> str:
        """
        Validate Demat ID format and authenticity.
        Returns "OK" if valid, or a descriptive error message.
        """
        # 1. Check format (16 digits)
        if not demat:
            return "Demat ID is required."
        if not demat.isdigit():
            return "Demat ID must contain only numbers."
        if len(demat) != 16:
            return f"Demat ID must be exactly 16 digits (entered {len(demat)})."
        
        # 2. Allow any valid 16-digit ID (acting as sign-up/login)
        # In a real app, this would verify with CDSL/NSDL
        return "OK"

    @staticmethod
    def save_user(email: str, data: Dict[str, Any]):
        """Save or update user data in the mock DB and file."""
        # Ensure DB is loaded first
        if not USER_DB and os.path.exists(DB_FILE):
            UserService._load_db()

        if email not in USER_DB:
            USER_DB[email] = {}
        
        # Merge new data
        USER_DB[email].update(data)
        
        # Ensure default fields exist
        if "name" not in USER_DB[email]:
            USER_DB[email]["name"] = data.get("name", "User")
        
        print(f"[UserService] Saved user: {email}, Data keys: {list(USER_DB[email].keys())}")
        # Disable file save to prevent Live Server auto-reload loops during demo
        # UserService._save_db()
        return USER_DB[email]

    @staticmethod
    def get_user(email: str) -> Optional[Dict]:
        """Retrieve user data from mock DB."""
        # Ensure DB is loaded first
        if not USER_DB and os.path.exists(DB_FILE):
            UserService._load_db()
            
        return USER_DB.get(email)

    @staticmethod
    def get_user_profile(email: str) -> UserProfileResponse:
        """Get strict UserProfileResponse for API."""
        # Ensure DB is loaded first
        if not USER_DB and os.path.exists(DB_FILE):
            UserService._load_db()
            
        user = USER_DB.get(email, {})
        
        # If user not found in DB but we have email (e.g. from token), return basic profile
        if not user:
            return UserProfileResponse(
                email=email,
                name="User",
                demat=None,
                picture=None,
                provider="email"
            )

        return UserProfileResponse(
            email=user.get("email", email),
            name=user.get("name", "User"),
            demat=user.get("demat"),
            picture=user.get("picture"),
            provider=user.get("provider", "email")
        )

# Initialize DB on module load
if os.path.exists(DB_FILE):
    UserService._load_db()
