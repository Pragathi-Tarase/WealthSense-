import logging
import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, Optional

# Ensure parent path is in sys.path when script is executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.features import calculate_features, FEATURE_COLUMNS
from ml.model_manager import ModelManager
from ml.train_model import train_single_model

logger = logging.getLogger(__name__)


def predict_stock_ml(
    symbol: str,
    horizon: int = 30,
    historical_df: Optional[pd.DataFrame] = None,
    sentiment_score: float = 0.0
) -> Optional[Dict]:
    """
    Executes Machine Learning model inference for a given stock symbol and target horizon.
    Uses saved RandomForestRegressor artifacts for instant prediction.
    """
    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BSE") or symbol.endswith(".BOM")):
        # Append .NS default for Indian NSE stock symbols if no exchange suffix
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"

    # 1. Load Trained Model Artifact
    artifact = ModelManager.load_model(symbol, horizon)

    # 2. If model not found, attempt auto-training once
    if artifact is None:
        logger.info(f"No pre-trained ML model found for {symbol} ({horizon}d). Initiating auto-training...")
        artifact = train_single_model(symbol, horizon=horizon)
        if artifact is None:
            logger.warning(f"Unable to train ML model for {symbol}")
            return None

    model = artifact["model"]
    metrics = artifact["metrics"]
    feature_importance = artifact["feature_importance"]

    try:
        # 3. Obtain Recent Market Data for Inference
        if historical_df is None or historical_df.empty:
            ticker = yf.Ticker(symbol)
            historical_df = ticker.history(period="1y")

        if historical_df is None or historical_df.empty or len(historical_df) < 30:
            logger.warning(f"Insufficient recent market data for inference on {symbol}")
            return None

        current_price = float(historical_df['Close'].iloc[-1])

        # 4. Feature Extraction on Latest Market Data
        features_df = calculate_features(historical_df, sentiment_score=sentiment_score)
        if features_df.empty:
            return None

        # Extract latest row as feature vector X_latest
        X_latest = features_df.iloc[[-1]][FEATURE_COLUMNS]

        # 5. Model Inference: Predict Expected Percentage Return
        predicted_return = float(model.predict(X_latest)[0])
        predicted_target_price = round(current_price * (1.0 + predicted_return), 2)
        expected_return_pct = round(predicted_return * 100.0, 2)

        # 6. Tree Ensemble Uncertainty / Confidence Calculation
        # Computes prediction variance across individual Random Forest trees
        X_latest_arr = X_latest.values
        tree_predictions = np.array([tree.predict(X_latest_arr)[0] for tree in model.estimators_])
        tree_std = float(np.std(tree_predictions))

        # Convert tree variance to empirical confidence score (0-100%)
        # Lower standard deviation across trees implies higher model agreement/confidence
        confidence_percent = round(max(15.0, min(95.0, (1.0 - min(1.0, tree_std * 6.0)) * 100.0)), 1)
        if confidence_percent >= 70.0:
            confidence_level = "HIGH"
        elif confidence_percent >= 45.0:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        # 7. Direction & Recommendation Logic
        if expected_return_pct >= 5.0:
            recommendation = "STRONG BUY"
            direction = "BULLISH"
        elif expected_return_pct >= 1.5:
            recommendation = "BUY"
            direction = "BULLISH"
        elif expected_return_pct <= -5.0:
            recommendation = "STRONG SELL"
            direction = "BEARISH"
        elif expected_return_pct <= -1.5:
            recommendation = "SELL"
            direction = "BEARISH"
        else:
            recommendation = "HOLD"
            direction = "NEUTRAL"

        # Company Name Lookup (Fast Static Mapping to avoid blocking network calls)
        STOCK_NAMES = {
            "RELIANCE.NS": "Reliance Industries Limited",
            "TCS.NS": "Tata Consultancy Services Limited",
            "HDFCBANK.NS": "HDFC Bank Limited",
            "INFY.NS": "Infosys Limited",
            "ICICIBANK.NS": "ICICI Bank Limited",
            "HINDUNILVR.NS": "Hindustan Unilever Limited",
            "ITC.NS": "ITC Limited",
            "SBIN.NS": "State Bank of India",
            "BHARTIARTL.NS": "Bharti Airtel Limited",
            "KOTAKBANK.NS": "Kotak Mahindra Bank Limited",
            "LT.NS": "Larsen & Toubro Limited",
            "AXISBANK.NS": "Axis Bank Limited",
            "BAJFINANCE.NS": "Bajaj Finance Limited",
            "ASIANPAINT.NS": "Asian Paints Limited",
            "MARUTI.NS": "Maruti Suzuki India Limited",
            "HCLTECH.NS": "HCL Technologies Limited",
            "WIPRO.NS": "Wipro Limited",
            "SUNPHARMA.NS": "Sun Pharmaceutical Industries Limited",
            "TITAN.NS": "Titan Company Limited",
            "TATASTEEL.NS": "Tata Steel Limited",
            "ADANIPORTS.NS": "Adani Ports and SEZ Limited",
            "ZOMATO.NS": "Zomato Limited",
            "IRCTC.NS": "IRCTC Limited",
            "PAYTM.NS": "Paytm (One97 Communications)",
            "NYKAA.NS": "Nykaa (FSN E-Commerce)"
        }
        name = STOCK_NAMES.get(symbol, symbol.split('.')[0])

        # 8. Structured Payload Return
        return {
            "symbol": symbol,
            "name": name,
            "current_price": round(current_price, 2),
            "prediction_horizon_days": horizon,
            "predicted_price": predicted_target_price,
            "expected_return_percent": expected_return_pct,
            "prediction_direction": direction,
            "recommendation": recommendation,
            "confidence": confidence_level,
            "confidence_percent": confidence_percent,
            "prediction_uncertainty_std": round(tree_std * 100.0, 2), # % std dev across trees
            "model_info": {
                "name": artifact.get("model_name", "RandomForestRegressor"),
                "version": artifact.get("model_version", "1.0.0"),
                "trained_at": artifact.get("trained_at"),
                "data_summary": artifact.get("data_summary", {})
            },
            "metrics": {
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "r2": metrics.get("r2"),
                "directional_accuracy": metrics.get("directional_accuracy")
            },
            "feature_importance": feature_importance[:10], # Top 10 features
            "generated_at": datetime.now().isoformat(),
            "disclaimer": "Predictions are estimates produced by a Random Forest machine-learning model using historical stock data and technical indicators. They are not guaranteed future prices or financial advice."
        }

    except Exception as e:
        logger.error(f"Error executing ML inference for {symbol}: {e}", exc_info=True)
        return None
