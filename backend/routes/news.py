from fastapi import APIRouter
from services.news_service import NewsService

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/stock/{symbol}")
async def get_stock_news(symbol: str):
    news = await NewsService.get_stock_news(symbol)
    return news

@router.get("/market")
async def get_market_news():
    news = await NewsService.get_market_news()
    return news
