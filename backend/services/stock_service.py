import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import ALPHA_VANTAGE_API_KEY

# In-memory cache for stock data
STOCK_CACHE: Dict[str, Dict] = {}
CACHE_TTL = 300  # 5 minutes

class StockService:
    BASE_URL = "https://www.alphavantage.co/query"
    
    INDIAN_STOCKS = [
        {"symbol": "RELIANCE.BSE", "name": "Reliance Industries"},
        {"symbol": "TCS.BSE", "name": "Tata Consultancy Services"},
        {"symbol": "HDFCBANK.BSE", "name": "HDFC Bank"},
        {"symbol": "ICICIBANK.BSE", "name": "ICICI Bank"},
        {"symbol": "INFY.BSE", "name": "Infosys"},
        {"symbol": "LT.BSE", "name": "Larsen & Toubro"},
        {"symbol": "ITC.BSE", "name": "ITC Limited"},
        {"symbol": "SBIN.BSE", "name": "State Bank of India"},
        {"symbol": "BHARTIARTL.BSE", "name": "Bharti Airtel"},
        {"symbol": "KOTAKBANK.BSE", "name": "Kotak Mahindra Bank"},
    ]
    
    @classmethod
    def _is_cache_valid(cls, symbol: str) -> bool:
        if symbol not in STOCK_CACHE:
            return False
        cached_time = STOCK_CACHE[symbol].get("cached_at")
        if not cached_time:
            return False
        return (datetime.utcnow() - cached_time).total_seconds() < CACHE_TTL
    
    @classmethod
    async def get_quote(cls, symbol: str) -> Dict:
        if cls._is_cache_valid(symbol):
            return STOCK_CACHE[symbol]["data"]
        
        # MOCK FALLBACK DATA (For when API is limited or fails)
        MOCK_FALLBACKS = {
            "RELIANCE.BSE": {"price": 2450.0, "change": 12.5, "change_percent": 0.52},
            "TCS.BSE": {"price": 3320.0, "change": -45.0, "change_percent": -1.34},
            "HDFC.BSE": {"price": 1550.0, "change": 5.0, "change_percent": 0.32},
            "INFY.BSE": {"price": 1420.0, "change": 18.0, "change_percent": 1.28},
            "WIPRO.BSE": {"price": 415.0, "change": -2.0, "change_percent": -0.48}
        }

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        try:
            # Using requests here; in a high-concurrency app, we'd use httpx.
            response = requests.get(cls.BASE_URL, params=params, timeout=5)
            data = response.json()
            
            if "Note" in data or "Information" in data:
                print(f"[StockService] Rate limit hit for {symbol}. Using mock fallback.")
                fallback = MOCK_FALLBACKS.get(symbol, {"price": 100.0, "change": 0, "change_percent": 0})
                result = {
                    "symbol": symbol,
                    "price": fallback["price"],
                    "change": fallback["change"],
                    "change_percent": fallback["change_percent"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_mock": True
                }
                return result
            
            quote = data.get("Global Quote", {})
            if quote and "05. price" in quote:
                result = {
                    "symbol": symbol,
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": float(quote.get("10. change percent", "0").replace("%", "")),
                    "timestamp": datetime.utcnow().isoformat(),
                    "is_mock": False
                }
                
                STOCK_CACHE[symbol] = {
                    "data": result,
                    "cached_at": datetime.utcnow()
                }
                return result
            # If no data, use fallback
            print(f"[StockService] No data for {symbol}. Using mock fallback.")
            fallback = MOCK_FALLBACKS.get(symbol, {"price": 100.0, "change": 0, "change_percent": 0})
            return {
                "symbol": symbol,
                "price": fallback["price"],
                "change": fallback["change"],
                "change_percent": fallback["change_percent"],
                "timestamp": datetime.utcnow().isoformat(),
                "is_mock": True
            }
        except Exception as e:
            print(f"[StockService] Fetch error for {symbol}: {e}. Using fallback.")
            fallback = MOCK_FALLBACKS.get(symbol, {"price": 100.0, "change": 0, "change_percent": 0})
            return {
                "symbol": symbol,
                "price": fallback["price"],
                "change": fallback["change"],
                "change_percent": fallback["change_percent"],
                "timestamp": datetime.utcnow().isoformat(),
                "is_mock": True
            }
    
    @classmethod
    async def get_intraday(cls, symbol: str, interval: str = "5min") -> Dict:
        params = {
            "function": f"TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            data = response.json()
            if "Note" in data:
                return {"error": "Rate limit reached", "details": data["Note"]}
            return data
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    async def get_daily(cls, symbol: str) -> Dict:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        try:
            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            data = response.json()
            if "Note" in data:
                return {"error": "Rate limit reached", "details": data["Note"]}
            return data
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    async def get_multiple_quotes(cls, symbols: List[str]) -> List[Dict]:
        results = []
        for symbol in symbols:
            quote = await cls.get_quote(symbol)
            results.append(quote)
        return results
    
    @classmethod
    def get_supported_indian_stocks(cls) -> List[Dict]:
        return cls.INDIAN_STOCKS

    @classmethod
    async def get_kite_holdings(cls, access_token: str) -> List[Dict]:
        """Fetch real holdings from Zerodha Kite API."""
        url = "https://api.kite.trade/portfolio/holdings"
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {os.environ.get('KITE_API_KEY')}:{access_token}"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            if data.get("status") == "success":
                holdings = []
                for h in data.get("data", []):
                    # Map Kite response to our internal format
                    # Kite symbol is usually like 'RELIANCE', we need 'RELIANCE.BSE' or '.NSE'
                    # Alpha Vantage typically uses .BSE or .NSE
                    symbol = h.get("tradingsymbol")
                    exchange = h.get("exchange")
                    full_symbol = f"{symbol}.{exchange}" if exchange in ["BSE", "NSE"] else symbol
                    
                    holdings.append({
                        "symbol": full_symbol,
                        "quantity": h.get("quantity", 0),
                        "avg_cost": float(h.get("average_price", 0)),
                        # Current price is often provided by Kite too
                        "current_price": float(h.get("last_price", 0))
                    })
                return holdings
            print(f"[StockService] Kite Error: {data}")
            return []
        except Exception as e:
            print(f"[StockService] Kite Exception: {e}")
            return []
