from fastapi import APIRouter, Header, HTTPException
from typing import Optional
from models import ChatRequest, ChatResponse
from services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest, authorization: Optional[str] = Header(None)):
    # 1. Gather Context if authorization is provided
    context_data = {}
    if authorization:
        try:
            from .dashboard import get_portfolio_data
            from services.market_service import MarketService
            from services.user_service import UserService
            
            # Get basic user data
            from .dashboard import get_user_from_token
            user = get_user_from_token(authorization)
            
            # Get full market feed instead of just overview
            market_feed = await MarketService.get_market_feed()
            
            # Get portfolio data
            portfolio = await get_portfolio_data(authorization)
            
            context_data = {
                "user": user,
                "current_market_ist_time": market_feed.get("ist_time"),
                "market_status": market_feed.get("status"),
                "top_stocks_performance": market_feed.get("stocks", [])[:15], # Give top 15 for better depth
                "portfolio": {
                    "overview": {
                        "total_value": portfolio.total_value,
                        "invested": portfolio.invested_value,
                        "total_gain_loss": portfolio.gain_loss,
                        "gain_percent": portfolio.gain_loss_percent
                    },
                    "holdings": [h.dict() if hasattr(h, 'dict') else h for h in portfolio.holdings]
                }
            }
        except Exception as e:
            print(f"[ChatRoute] Error gathering context: {e}")

    return await ChatService.get_response(req.chat_id, req.message, context_data=context_data)

@router.get("/history", response_model=ChatResponse)
async def get_chat_history(authorization: Optional[str] = Header(None), chat_id: Optional[str] = None):
    # 1. If User is logged in, get their history
    if authorization:
        try:
            from .dashboard import get_user_from_token
            user = get_user_from_token(authorization)
            if user and "id" in user:
                return ChatService.get_user_history(user["id"])
        except Exception:
            pass # Fallback to chat_id if token invalid
            
    # 2. Fallback to chat_id if provided
    if chat_id:
        history = ChatService.get_session(chat_id)
        return {
            "chat_id": chat_id,
            "messages": history
        }
    
    # 3. New Session
    return {
        "chat_id": ChatService.create_session(),
        "messages": []
    }
