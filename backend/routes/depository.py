from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Form
from typing import Optional
import jwt
import traceback
from config import APP_SECRET_KEY, JWT_ALGORITHM
from services.user_service import UserService
from services.depository_service import DepositoryService

router = APIRouter(prefix="/api/depository", tags=["depository"])

def get_email_from_token(authorization: str) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = parts[1]
    try:
        payload = jwt.decode(token, APP_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/upload-cas")
async def upload_cas(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None)
):
    """
    Upload and process a CAS (Consolidated Account Statement) file.
    
    - Supports both text files and password-protected PDFs
    - For PDFs, password is required (usually PAN number, e.g., ABCDE1234F)
    - Extracts stock holdings and saves to user profile
    """
    email = get_email_from_token(authorization)
    
    print(f"[CAS Upload] Processing file: {file.filename} for user: {email}")
    print(f"[CAS Upload] Password provided: {'Yes' if password else 'No'}")
    
    # Read file content
    file_bytes = await file.read()
    print(f"[CAS Upload] File size: {len(file_bytes)} bytes")
    print(f"[CAS Upload] First 10 bytes: {file_bytes[:10]}")
    
    # Try to decode as text for text files, empty string for PDFs
    try:
        text_content = file_bytes.decode("utf-8")
        print(f"[CAS Upload] File decoded as text, length: {len(text_content)}")
    except UnicodeDecodeError:
        text_content = ""  # Binary file (likely PDF)
        print(f"[CAS Upload] File is binary (likely PDF)")
    
    try:
        # Parse holdings with PDF support
        print(f"[CAS Upload] Calling parse_cas_statement...")
        holdings = await DepositoryService.parse_cas_statement(
            content=text_content,
            file_bytes=file_bytes,
            password=password
        )
    
        # Ensure holdings is not None
        if holdings is None:
            holdings = []

        print(f"[CAS Upload] Parsed {len(holdings)} holdings")
        
        if not holdings:
            raise HTTPException(
                status_code=400, 
                detail="No valid holdings found in CAS file. Supported formats:\n"
                       "1. Text file: SYMBOL QUANTITY PRICE (one per line)\n"
                       "2. Password-protected PDF from CAMS/KFintech"
            )

        # Save to user profile as external holdings
        UserService.save_user(email, {"external_holdings": holdings})
        print(f"[CAS Upload] Saved holdings to user profile")
        
        return {
            "message": f"Successfully imported {len(holdings)} holdings from CAS.",
            "holdings_count": len(holdings),
            "holdings": holdings
        }
        
    except ValueError as e:
        print(f"[CAS Upload] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[CAS Upload] Exception: {e}")
        print(f"[CAS Upload] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
