import requests
from google import genai
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import NEWSAPI_API_KEY, GEMINI_API_KEY

# In-memory cache for news
NEWS_CACHE: Dict[str, Dict] = {}
CACHE_TTL = 3600  # 1 hour

# Global Sentiment Cache (Headlines -> result)
SENTIMENT_CACHE: Dict[str, Dict] = {}

# Initialize google-genai client
gemini_client: Optional[genai.Client] = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[NewsService] Gemini client initialization error: {e}")

class NewsService:
    BASE_URL = "https://newsapi.org/v2"
    
    INDIAN_STOCK_KEYWORDS = [
        "Indian stock market",
        "NSE", "BSE",
        "stock market India",
        "equity market",
        "Indian economy"
    ]
    
    @classmethod
    def _get_cache_key(cls, query: str) -> str:
        return f"news_{query.lower().replace(' ', '_')}"
    
    @classmethod
    def _is_cache_valid(cls, cache_key: str) -> bool:
        if cache_key not in NEWS_CACHE:
            return False
        cached_time = NEWS_CACHE[cache_key].get("cached_at")
        if not cached_time:
            return False
        return (datetime.utcnow() - cached_time).total_seconds() < CACHE_TTL
    
    @classmethod
    async def _add_sentiment(cls, articles: List[Dict]):
        if not GEMINI_API_KEY or not gemini_client or not articles:
            return articles
            
        remaining_articles = []
        for article in articles:
            if article['title'] in SENTIMENT_CACHE:
                article['sentiment'] = SENTIMENT_CACHE[article['title']]['sentiment']
                article['ai_insight'] = SENTIMENT_CACHE[article['title']]['ai_insight']
            else:
                remaining_articles.append(article)
        
        if not remaining_articles:
            return articles

        try:
            sample = remaining_articles[:5]
            headlines = "\n".join([f"{i}. {a['title']}" for i, a in enumerate(sample)])
            prompt = (
                "Analyze the sentiment of these Indian Stock Market headlines. "
                "For each, respond with exactly '[Bullish]', '[Bearish]', or '[Neutral]' followed by a short reason. "
                "Format: 0. [Sentiment] Reason\n"
                f"Headlines:\n{headlines}"
            )
            
            response = gemini_client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            
            lines = response.text.strip().split('\n')
            for line in lines:
                if '[' in line and ']' in line:
                    try:
                        parts = line.split(". ", 1)
                        if len(parts) < 2: continue
                        idx = int(parts[0])
                        content = parts[1]
                        sentiment_tag = content.split(']')[0].replace('[', '').strip()
                        reason = content.split(']', 1)[1].strip()
                        
                        if idx < len(sample):
                            sample[idx]['sentiment'] = sentiment_tag
                            sample[idx]['ai_insight'] = reason
                            
                            SENTIMENT_CACHE[sample[idx]['title']] = {
                                "sentiment": sentiment_tag,
                                "ai_insight": reason
                            }
                    except Exception as e:
                        print(f"[NewsService] Line Parse Error: {e} | Line: {line}")
                        continue
        except Exception as e:
            error_msg = str(e)
            print(f"[NewsService] Sentiment Analysis Error: {error_msg}")
            if "429" in error_msg:
                print("[NewsService] Rate limit hit. Serving news without AI insights.")
            
        return articles

    @classmethod
    async def get_stock_news(cls, symbol: str) -> Dict:
        cache_key = cls._get_cache_key(symbol)
        
        if cls._is_cache_valid(cache_key):
            return NEWS_CACHE[cache_key]["data"]
        
        is_newsdata = NEWSAPI_API_KEY.startswith("pub_")
        
        if is_newsdata:
            url = "https://newsdata.io/api/1/news"
            params = {
                "q": f"{symbol} Indian stock",
                "apikey": NEWSAPI_API_KEY,
                "language": "en"
            }
        else:
            url = f"{cls.BASE_URL}/everything"
            params = {
                "q": f"{symbol} Indian stock",
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": NEWSAPI_API_KEY,
                "pageSize": 10
            }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            articles = []
            raw_articles = data.get("results" if is_newsdata else "articles", [])
            for article in raw_articles[:10]:
                articles.append({
                    "title": article.get("title"),
                    "description": article.get("description" if not is_newsdata else "description"),
                    "source": article.get("source_id" if is_newsdata else "source", {}).get("name") if not is_newsdata else article.get("source_id"),
                    "url": article.get("link" if is_newsdata else "url"),
                    "published_at": article.get("pubDate" if is_newsdata else "publishedAt"),
                    "image_url": article.get("image_url" if is_newsdata else "urlToImage")
                })
            
            articles = await cls._add_sentiment(articles)

            if not articles and symbol != "Indian Market":
                return await cls.get_market_news()

            result = {"articles": articles, "total": len(articles)}
            NEWS_CACHE[cache_key] = {
                "data": result,
                "cached_at": datetime.utcnow()
            }
            return result
        except Exception as e:
            print(f"[NewsService] Error: {e}")
            return {"error": str(e), "articles": []}
    
    @classmethod
    async def get_market_news(cls) -> Dict:
        cache_key = cls._get_cache_key("indian_market")
        
        if cls._is_cache_valid(cache_key):
            return NEWS_CACHE[cache_key]["data"]
        
        is_newsdata = NEWSAPI_API_KEY.startswith("pub_")
        
        if is_newsdata:
            url = "https://newsdata.io/api/1/news"
            params = {
                "q": "Indian stock market",
                "apikey": NEWSAPI_API_KEY,
                "language": "en"
            }
        else:
            url = f"{cls.BASE_URL}/everything"
            params = {
                "q": "Indian stock market",
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": NEWSAPI_API_KEY,
                "pageSize": 15
            }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            articles = []
            raw_articles = data.get("results" if is_newsdata else "articles", [])
            for article in raw_articles[:15]:
                articles.append({
                    "title": article.get("title"),
                    "description": article.get("description" if not is_newsdata else "description"),
                    "source": article.get("source_id" if is_newsdata else "source", {}).get("name") if not is_newsdata else article.get("source_id"),
                    "url": article.get("link" if is_newsdata else "url"),
                    "published_at": article.get("pubDate" if is_newsdata else "publishedAt"),
                    "image_url": article.get("image_url" if is_newsdata else "urlToImage")
                })
            
            articles = await cls._add_sentiment(articles)

            result = {"articles": articles, "total": len(articles)}
            NEWS_CACHE[cache_key] = {
                "data": result,
                "cached_at": datetime.utcnow()
            }
            return result
        except Exception as e:
            print(f"[NewsService] Error: {e}")
            return {"error": str(e), "articles": []}
