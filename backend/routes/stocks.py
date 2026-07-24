from fastapi import APIRouter, HTTPException, Header
from typing import Optional, List
from services.stock_service import StockService

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

@router.get("/quote/{symbol}")
async def get_stock_quote(symbol: str):
    quote = await StockService.get_quote(symbol)
    if "error" in quote:
        raise HTTPException(status_code=404, detail=quote["error"])
    return quote

@router.get("/quotes")
async def get_multiple_quotes(symbols: str):
    symbol_list = [s.strip() for s in symbols.split(",")]
    quotes = await StockService.get_multiple_quotes(symbol_list)
    return {"quotes": quotes}

@router.get("/intraday/{symbol}")
async def get_intraday_data(symbol: str, interval: str = "5min"):
    data = await StockService.get_intraday(symbol, interval)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data

@router.get("/daily/{symbol}")
async def get_daily_data(symbol: str):
    data = await StockService.get_daily(symbol)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data

@router.get("/supported")
async def get_supported_stocks():
    stocks = StockService.get_supported_indian_stocks()
    return {"stocks": stocks}
