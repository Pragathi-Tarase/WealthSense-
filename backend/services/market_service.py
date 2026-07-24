import requests
import os
import random
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
from config import ALPHA_VANTAGE_API_KEY

class MarketService:
    # Manual IST Offset (UTC + 5:30)
    IST_OFFSET = timedelta(hours=5, minutes=30)
    
    # Categorized Stocks for Market Feed - Comprehensive Indian Stock Database
    STOCKS_BY_CAP = {
        "High": [
            # Large Cap - Top Indian Companies
            {"symbol": "RELIANCE.BOM", "name": "Reliance Industries"},
            {"symbol": "TCS.BOM", "name": "TCS"},
            {"symbol": "HDFCBANK.BOM", "name": "HDFC Bank"},
            {"symbol": "INFY.BOM", "name": "Infosys"},
            {"symbol": "ICICIBANK.BOM", "name": "ICICI Bank"},
            {"symbol": "HINDUNILVR.BOM", "name": "Hindustan Unilever"},
            {"symbol": "ITC.BOM", "name": "ITC Ltd"},
            {"symbol": "SBIN.BOM", "name": "State Bank of India"},
            {"symbol": "BHARTIARTL.BOM", "name": "Bharti Airtel"},
            {"symbol": "KOTAKBANK.BOM", "name": "Kotak Mahindra Bank"},
            {"symbol": "LT.BOM", "name": "Larsen & Toubro"},
            {"symbol": "AXISBANK.BOM", "name": "Axis Bank"},
            {"symbol": "BAJFINANCE.BOM", "name": "Bajaj Finance"},
            {"symbol": "ASIANPAINT.BOM", "name": "Asian Paints"},
            {"symbol": "MARUTI.BOM", "name": "Maruti Suzuki"},
            {"symbol": "HCLTECH.BOM", "name": "HCL Technologies"},
            {"symbol": "WIPRO.BOM", "name": "Wipro"},
            {"symbol": "SUNPHARMA.BOM", "name": "Sun Pharma"},
            {"symbol": "TITAN.BOM", "name": "Titan Company"},
            {"symbol": "NESTLEIND.BOM", "name": "Nestle India"},
        ],
        "Mid": [
            # Mid Cap - Growing Companies
            {"symbol": "TATAPOWER.BOM", "name": "Tata Power"},
            {"symbol": "TRENT.BOM", "name": "Trent Ltd"},
            {"symbol": "RECLTD.BOM", "name": "REC Ltd"},
            {"symbol": "PFC.BOM", "name": "Power Finance"},
            {"symbol": "BEL.BOM", "name": "Bharat Electronics"},
            {"symbol": "PVRINOX.BOM", "name": "PVR INOX"},
            {"symbol": "DMART.BOM", "name": "Avenue Supermarts (DMart)"},
            {"symbol": "ADANIPORTS.BOM", "name": "Adani Ports"},
            {"symbol": "GODREJCP.BOM", "name": "Godrej Consumer"},
            {"symbol": "PIDILITIND.BOM", "name": "Pidilite Industries"},
            {"symbol": "DIVISLAB.BOM", "name": "Divi's Laboratories"},
            {"symbol": "BIOCON.BOM", "name": "Biocon"},
            {"symbol": "TORNTPHARM.BOM", "name": "Torrent Pharma"},
            {"symbol": "MUTHOOTFIN.BOM", "name": "Muthoot Finance"},
            {"symbol": "BAJAJFINSV.BOM", "name": "Bajaj Finserv"},
            {"symbol": "INDIGO.BOM", "name": "InterGlobe Aviation (IndiGo)"},
            {"symbol": "VEDL.BOM", "name": "Vedanta"},
            {"symbol": "HINDALCO.BOM", "name": "Hindalco Industries"},
            {"symbol": "TATASTEEL.BOM", "name": "Tata Steel"},
            {"symbol": "JSWSTEEL.BOM", "name": "JSW Steel"},
        ],
        "Low": [
            # Small Cap & Emerging Companies
            {"symbol": "SUZLON.BOM", "name": "Suzlon Energy"},
            {"symbol": "IDEA.BOM", "name": "Vodafone Idea"},
            {"symbol": "JPPOWER.BOM", "name": "Jaiprakash Power"},
            {"symbol": "RCOM.BOM", "name": "Reliance Comm"},
            {"symbol": "ZOMATO.BOM", "name": "Zomato"},
            {"symbol": "PAYTM.BOM", "name": "Paytm (One97)"},
            {"symbol": "NYKAA.BOM", "name": "Nykaa (FSN E-Commerce)"},
            {"symbol": "POLICYBZR.BOM", "name": "PB Fintech (PolicyBazaar)"},
            {"symbol": "IRCTC.BOM", "name": "IRCTC"},
            {"symbol": "IRFC.BOM", "name": "Indian Railway Finance"},
            {"symbol": "RVNL.BOM", "name": "Rail Vikas Nigam"},
            {"symbol": "YESBANK.BOM", "name": "Yes Bank"},
            {"symbol": "SAIL.BOM", "name": "SAIL"},
            {"symbol": "NMDC.BOM", "name": "NMDC"},
            {"symbol": "COALINDIA.BOM", "name": "Coal India"},
        ]
    }

    @classmethod
    def get_ist_time(cls) -> datetime:
        return datetime.utcnow() + cls.IST_OFFSET

    @classmethod
    def is_market_open(cls) -> bool:
        ist_now = cls.get_ist_time()
        if ist_now.weekday() > 4:
            return False
        current_time = ist_now.time()
        market_open = time(9, 15)
        market_close = time(15, 30)
        return market_open <= current_time <= market_close

    @classmethod
    async def search_stocks(cls, keywords: str) -> List[Dict]:
        """Search for stocks globally using Alpha Vantage."""
        if not ALPHA_VANTAGE_API_KEY:
            return []
            
        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={keywords}&apikey={ALPHA_VANTAGE_API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            best_matches = data.get("bestMatches", [])
            
            results = []
            for match in best_matches[:3]: # Take top 3 to save API budget
                results.append({
                    "symbol": match.get("1. symbol"),
                    "name": match.get("2. name"),
                    "type": match.get("3. type"),
                    "region": match.get("4. region"),
                    "currency": match.get("8. currency")
                })
            return results
        except Exception as e:
            print(f"Alpha Vantage search failed: {e}")
            return []

    @classmethod
    async def get_stock_quote(cls, symbol: str) -> Dict:
        """Fetch real quote for a specific symbol."""
        if not ALPHA_VANTAGE_API_KEY:
            return None
            
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json().get("Global Quote", {})
            if not data: return None
            
            price = float(data.get("05. price", 0))
            change = float(data.get("09. change", 0))
            change_percent = float(data.get("10. change percent", "0").replace("%", ""))
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "high": float(data.get("03. high", 0)),
                "low": float(data.get("04. low", 0)),
                "open": float(data.get("02. open", 0)),
                "volume": data.get("06. volume", "N/A"),
                "latest_day": data.get("07. latest trading day")
            }
        except Exception as e:
            print(f"Alpha Vantage quote failed: {e}")
            return None

    @classmethod
    async def get_market_feed(cls, category: Optional[str] = None, search_query: Optional[str] = None) -> Dict:
        """Fetch categorized stocks or search results for the market feed."""
        is_open = cls.is_market_open()
        
        # If searching, try API first, then fall back to local search
        if search_query:
            search_results = await cls.search_stocks(search_query)
            
            # If API returns empty (rate limit), fall back to searching local stocks
            if not search_results:
                query_lower = search_query.lower()
                all_stocks = [s for sublist in cls.STOCKS_BY_CAP.values() for s in sublist]
                search_results = [
                    s for s in all_stocks 
                    if query_lower in s["name"].lower() or query_lower in s["symbol"].lower()
                ]
            
            stocks_to_fetch = search_results[:10] # Limit to 10
        elif category and category.capitalize() in cls.STOCKS_BY_CAP:
            stocks_to_fetch = cls.STOCKS_BY_CAP[category.capitalize()]
        else:
            stocks_to_fetch = [s for sublist in cls.STOCKS_BY_CAP.values() for s in sublist]
        
        # Function to generate combined data (Real if possible, Mock fallback)
        async def process_stock(stock: Dict):
            symbol = stock["symbol"]
            name = stock.get("name", symbol)
            
            # For search queries, we ALWAYS try to get a real quote
            if search_query:
                quote = await cls.get_stock_quote(symbol)
                if quote:
                    return {
                        **quote,
                        "name": name,
                        "market_cap": "Global" 
                    }
            
            # Fallback/Default mock logic for categorized Indian stocks
            def get_mock():
                # Deterministic seed based on time + symbol hash
                ist_now = cls.get_ist_time()
                
                # If market is closed, freeze the time to 15:30 for consistent closing prices
                if not is_open:
                    # Freeze at 15:30 of the current day (or last trading day)
                    seed_val = 30 + (15 * 60) + hash(symbol) % 1000  # 15:30 = 930 minutes
                else:
                    seed_val = ist_now.minute + (ist_now.hour * 60) + hash(symbol) % 1000
                
                random.seed(seed_val)
                
                base = 100.0
                # High Cap Stocks
                if "RELIANCE" in symbol: base = 2740.0
                elif "TCS" in symbol: base = 3920.0
                elif "HDFCBANK" in symbol: base = 1530.0
                elif "INFY" in symbol: base = 1620.0
                elif "ICICIBANK" in symbol: base = 1005.0
                elif "HINDUNILVR" in symbol: base = 2680.0
                elif "ITC" in symbol: base = 445.0
                elif "SBIN" in symbol: base = 625.0
                elif "BHARTIARTL" in symbol: base = 1540.0
                elif "KOTAKBANK" in symbol: base = 1750.0
                elif "LT" in symbol: base = 3580.0
                elif "AXISBANK" in symbol: base = 1095.0
                elif "BAJFINANCE" in symbol: base = 6850.0
                elif "ASIANPAINT" in symbol: base = 2890.0
                elif "MARUTI" in symbol: base = 12500.0
                elif "HCLTECH" in symbol: base = 1820.0
                elif "WIPRO" in symbol: base = 565.0
                elif "SUNPHARMA" in symbol: base = 1680.0
                elif "TITAN" in symbol: base = 3420.0
                elif "NESTLEIND" in symbol: base = 2450.0
                # Mid Cap Stocks
                elif "TATAPOWER" in symbol: base = 380.0
                elif "TRENT" in symbol: base = 3950.0
                elif "PVRINOX" in symbol: base = 1485.0
                elif "DMART" in symbol: base = 3680.0
                elif "ADANIPORTS" in symbol: base = 1240.0
                elif "GODREJCP" in symbol: base = 1150.0
                elif "PIDILITIND" in symbol: base = 2890.0
                elif "DIVISLAB" in symbol: base = 5820.0
                elif "BIOCON" in symbol: base = 355.0
                elif "TORNTPHARM" in symbol: base = 3250.0
                elif "MUTHOOTFIN" in symbol: base = 1920.0
                elif "BAJAJFINSV" in symbol: base = 1680.0
                elif "INDIGO" in symbol: base = 4250.0
                elif "VEDL" in symbol: base = 445.0
                elif "HINDALCO" in symbol: base = 645.0
                elif "TATASTEEL" in symbol: base = 165.0
                elif "JSWSTEEL" in symbol: base = 920.0
                # Low Cap Stocks
                elif "ZOMATO" in symbol: base = 188.0
                elif "SUZLON" in symbol: base = 48.0
                elif "IDEA" in symbol: base = 14.5
                elif "PAYTM" in symbol: base = 920.0
                elif "NYKAA" in symbol: base = 185.0
                elif "POLICYBZR" in symbol: base = 1540.0
                elif "IRCTC" in symbol: base = 825.0
                elif "IRFC" in symbol: base = 145.0
                elif "RVNL" in symbol: base = 485.0
                elif "YESBANK" in symbol: base = 22.5
                elif "SAIL" in symbol: base = 118.0
                elif "NMDC" in symbol: base = 225.0
                elif "COALINDIA" in symbol: base = 425.0
                
                daily_volatility = random.uniform(-0.02, 0.02)
                micro_fluctuation = (datetime.utcnow().microsecond % 100 - 50) / 5000 
                
                price = base * (1 + daily_volatility + micro_fluctuation)
                change = price - base
                
                return {
                    "name": name,
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": round((change/base)*100, 2),
                    "open": round(base * 0.99, 2),
                    "high": round(max(price, base * 1.01), 2),
                    "low": round(min(price, base * 0.98), 2),
                    "volume": f"{random.randint(1, 50)}M",
                    "market_cap": "High" if any(s["symbol"] == symbol for s in cls.STOCKS_BY_CAP["High"]) else "Mid" if any(s["symbol"] == symbol for s in cls.STOCKS_BY_CAP["Mid"]) else "Low"
                }
            
            return get_mock()

        ist_now = cls.get_ist_time()
        feed_data = [await process_stock(s) for s in stocks_to_fetch]
            
        return {
            "status": "OPEN" if is_open else "CLOSED",
            "ist_time": ist_now.isoformat(),
            "stocks": feed_data
        }
