from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    demat: Optional[str] = None

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class UserProfileResponse(BaseModel):
    email: str
    name: str = "User"
    demat: Optional[str] = None
    picture: Optional[str] = None
    provider: str = "email"

class PortfolioHolding(BaseModel):
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    gain_loss: float
    gain_loss_percent: float

class PortfolioResponse(BaseModel):
    email: str
    total_value: float
    invested_value: float
    gain_loss: float
    gain_loss_percent: float
    holdings: List[PortfolioHolding]

class StockQuote(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    timestamp: str

class NewsArticle(BaseModel):
    title: str
    description: Optional[str]
    source: str
    url: str
    published_at: str
    image_url: Optional[str] = None

class ChatMessage(BaseModel):
    role: str # 'user' or 'ai'
    content: str
    timestamp: datetime = datetime.utcnow()

class ChatRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    chat_id: str
    messages: List[ChatMessage]

# Prediction Models
class PredictionTimeframe(BaseModel):
    percent_change: float
    target_price: float

class StockPrediction(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: str
    current_price: float
    combined_score: float
    predictions: Dict[str, PredictionTimeframe]
    confidence: str
    confidence_percent: float
    risk_level: str
    recommendation: str
    reasoning: List[str]
    generated_at: str

class PredictionListResponse(BaseModel):
    predictions: List[StockPrediction]
    total: int
    accuracy_metrics: Optional[Dict] = None

class PredictionRequest(BaseModel):
    symbol: str
    force_refresh: bool = False
