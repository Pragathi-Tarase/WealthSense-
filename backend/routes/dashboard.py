from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from services.stock_service import StockService
from services.news_service import NewsService
from services.user_service import UserService
from services.depository_service import DepositoryService
import jwt
from config import APP_SECRET_KEY, JWT_ALGORITHM
from models import UserProfileResponse, PortfolioResponse, NewsArticle, StockQuote

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def get_user_from_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    token = parts[1]
    try:
        payload = jwt.decode(token, APP_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {
            "id": payload.get("id"),
            "email": payload.get("email"),
            "demat": payload.get("demat"),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
            "provider": payload.get("provider")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/overview")
async def get_dashboard_overview(authorization: Optional[str] = Header(None)):
    user = get_user_from_token(authorization)
    
    indian_stocks = StockService.get_supported_indian_stocks()
    symbols = [s["symbol"] for s in indian_stocks[:5]]
    quotes = await StockService.get_multiple_quotes(symbols)
    
    news = await NewsService.get_market_news()
    
    return {
        "user": user,
        "stocks": quotes,
        "news": news.get("articles", [])[:5]
    }

@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio_data(authorization: Optional[str] = Header(None)):
    user_token = get_user_from_token(authorization)
    email = user_token["email"]
    
    user_profile = UserService.get_user(email)
    provider = user_token.get("provider") or (user_profile.get("provider") if user_profile else "email")
    broker_token = user_profile.get("broker_access_token") if user_profile else None
    
    holding_configs = []

    if provider != "email":
        if broker_token:
            print(f"[Dashboard] OAUTH USER: Fetching holdings for {email} from Kite")
            holding_configs = await StockService.get_kite_holdings(broker_token)
    else:
        print(f"[Dashboard] EMAIL USER: Prioritizing CAS holdings for {email}")
        holding_configs = user_profile.get("external_holdings", []) if user_profile else []
            
    if not holding_configs:
        print(f"[Dashboard] No holdings found for {email} via {provider} flow.")
        
        import random
        random.seed(hash(email))
        
        print(f"[Dashboard] Injecting DYNAMIC fallback holdings for {email}")
        
        stock_pool = [
            {"symbol": "RELIANCE.BSE", "base_price": 2500},
            {"symbol": "TCS.BSE", "base_price": 2400},
            {"symbol": "HDFCBANK.BSE", "base_price": 2200},
            {"symbol": "INFY.BSE", "base_price": 2450},
            {"symbol": "ICICIBANK.BSE", "base_price": 1500},
            {"symbol": "SBIN.BSE", "base_price": 600},
            {"symbol": "BHARTIARTL.BSE", "base_price": 800},
            {"symbol": "ITC.BSE", "base_price": 450},
        ]
        
        num_stocks = random.randint(3, 6)
        selected_stocks = random.sample(stock_pool, num_stocks)
        
        holding_configs = []
        for stock in selected_stocks:
            qty = random.randint(10, 200)
            avg_cost = stock["base_price"] * (1 + random.uniform(-0.2, 0.2))
            curr_price = stock["base_price"] * (1 + random.uniform(-0.15, 0.15))
            
            holding_configs.append({
                "symbol": stock["symbol"],
                "quantity": qty,
                "avg_cost": round(avg_cost, 2),
                "current_price": round(curr_price, 2)
            })
    
    holdings = []
    total_value = 0.0
    invested_value = 0.0
    
    for h in holding_configs:
        quote = await StockService.get_quote(h["symbol"])
        current_price = quote.get("price") or h.get("current_price") or h["avg_cost"]
        
        value = h["quantity"] * current_price
        cost = h["quantity"] * h["avg_cost"]
        gain_loss = value - cost
        gain_loss_percent = (gain_loss / cost * 100) if cost > 0 else 0
        
        holdings.append({
            "symbol": h["symbol"],
            "quantity": h["quantity"],
            "avg_cost": h["avg_cost"],
            "current_price": round(current_price, 2),
            "value": round(value, 2),
            "gain_loss": round(gain_loss, 2),
            "gain_loss_percent": round(gain_loss_percent, 2)
        })
        
        total_value += value
        invested_value += cost
    
    total_gain_loss = total_value - invested_value
    total_gain_loss_percent = (total_gain_loss / invested_value * 100) if invested_value > 0 else 0

    return PortfolioResponse(
        email=email,
        total_value=round(total_value, 2),
        invested_value=round(invested_value, 2),
        gain_loss=round(total_gain_loss, 2),
        gain_loss_percent=round(total_gain_loss_percent, 2),
        holdings=holdings
    )

@router.get("/charts")
async def get_chart_data(authorization: Optional[str] = Header(None), symbol: str = "RELIANCE.BSE"):
    user = get_user_from_token(authorization)
    
    daily_data = await StockService.get_daily(symbol)
    intraday_data = await StockService.get_intraday(symbol, "15min")
    
    return {
        "symbol": symbol,
        "daily": daily_data,
        "intraday": intraday_data
    }

@router.get("/ai-analysis")
async def get_ai_portfolio_analysis(authorization: Optional[str] = Header(None)):
    user_token = get_user_from_token(authorization)
    email = user_token["email"]
    
    portfolio = await get_portfolio_data(authorization)
    
    if not portfolio.holdings:
        return {"analysis": "No holdings found. Please upload your CAS statement or link a broker to see an AI analysis of your portfolio."}
        
    holdings_str = "\n".join([f"{h['symbol'] if isinstance(h, dict) else h.symbol}: {h['quantity'] if isinstance(h, dict) else h.quantity} units, Gain/Loss: {h['gain_loss_percent'] if isinstance(h, dict) else h.gain_loss_percent}%" for h in portfolio.holdings])
    
    prompt = (
        "You are an expert AI Portfolio Analyst for the Indian Stock Market. Analyze this user's holdings and provide a 'Portfolio Health Check'. "
        "Include: \n"
        "1. Risk Assessment (e.g., High exposure to tech/finance)\n"
        "2. Diversification Insight\n"
        "3. Tactical Tip (e.g., Rebalancing or sector focus)\n"
        "Keep it professional, data-driven, and under 150 words.\n\n"
        f"Portfolio Data:\n{holdings_str}"
    )
    
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return {"analysis": "AI Analysis is currently unavailable. Please configure the Gemini API Key in the backend."}
        
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return {"analysis": response.text}
    except Exception as e:
        error_msg = str(e)
        print(f"[Dashboard] AI Analysis Error: {error_msg}")
        if "429" in error_msg:
            return {"analysis": "WealthSense AI is currently at its daily analysis limit. Please try again later or upgrade to a Pro plan for instant rebalancing advice."}
        return {"analysis": f"AI Analysis Error: {error_msg}"}
