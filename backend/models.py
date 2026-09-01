from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
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

# Prediction Models — Preserving Backward Compatibility
class PredictionTimeframe(BaseModel):
    percent_change: float
    target_price: float

class StockPrediction(BaseModel):
    symbol: str
    name: str
    sector: str = "Indian Stock Market"
    industry: str = "Financial Services / Equity"
    current_price: float
    combined_score: float = 0.0
    predictions: Dict[str, PredictionTimeframe]
    confidence: str
    confidence_percent: float
    risk_level: str
    recommendation: str
    reasoning: List[str]
    generated_at: str
    
    # Phase 2 ML Additions (Optional fields for backward compatibility)
    is_ml_model: Optional[bool] = True
    model_name: Optional[str] = "RandomForestRegressor"
    metrics: Optional[Dict[str, float]] = None
    feature_importance: Optional[List[Dict[str, Any]]] = None
    disclaimer: Optional[str] = None

    model_config = {"protected_namespaces": ()}

class PredictionListResponse(BaseModel):
    predictions: List[StockPrediction]
    total: int
    accuracy_metrics: Optional[Dict] = None

class PredictionRequest(BaseModel):
    symbol: str
    horizon: Optional[int] = 30
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    force_refresh: bool = False

class MLModelMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float
    directional_accuracy: float

class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
