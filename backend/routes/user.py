from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Optional
from services.user_service import UserService
from models import UserProfileResponse
import jwt
from config import APP_SECRET_KEY, JWT_ALGORITHM

router = APIRouter(prefix="/api/user", tags=["User"])

def get_current_user_email(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1]
    try:
        payload = jwt.decode(token, APP_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload.get("email") or payload.get("sub")

@router.get("/profile", response_model=UserProfileResponse)
def get_user_profile(email: str = Depends(get_current_user_email)):
    """
    Fetch the logged-in user's profile details.
    """
    return UserService.get_user_profile(email)

@router.post("/profile")
def update_user_profile(
    data: dict,
    email: str = Depends(get_current_user_email)
):
    """
    Update the logged-in user's profile details.
    """
    updated_user = UserService.save_user(email, data)
    return {"message": "Profile updated successfully", "user": updated_user}
