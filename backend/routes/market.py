from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from services.market_service import MarketService

router = APIRouter(prefix="/api/market", tags=["Market"])

@router.get("/status")
async def get_market_status():
    is_open = MarketService.is_market_open()
    return {
        "is_open": is_open,
        "ist_time": MarketService.get_ist_time().isoformat(),
        "message": "Market is open" if is_open else "Market is closed. Opens at 9:15 AM IST."
    }

@router.get("/feed")
async def get_market_feed(category: Optional[str] = None, search: Optional[str] = None):
    return await MarketService.get_market_feed(category, search)
