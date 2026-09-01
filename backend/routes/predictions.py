from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List
from models import StockPrediction, PredictionListResponse, PredictionRequest
from services.prediction_service import PredictionService
from ml.model_manager import ModelManager
from ml.train_model import train_single_model
from ml.predict import predict_stock_ml
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.get("/top", response_model=PredictionListResponse)
async def get_top_predictions(
    limit: int = 10,
    force_refresh: bool = False,
    authorization: Optional[str] = Header(None)
):
    """
    Get top stock predictions ranked by expected percentage return.
    """
    try:
        limit = min(limit, 25)
        predictions = await PredictionService.get_top_predictions(limit=limit, force_refresh=force_refresh)
        accuracy = PredictionService.calculate_accuracy()

        return {
            "predictions": predictions,
            "total": len(predictions),
            "accuracy_metrics": accuracy
        }
    except Exception as e:
        logger.error(f"Error getting top predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate predictions: {str(e)}")


@router.post("/stock", response_model=StockPrediction)
async def predict_specific_stock(
    request: PredictionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generate Machine Learning prediction for a specific stock symbol with date-range & horizon support.
    """
    try:
        # Date Validation
        if request.start_date and request.end_date:
            if request.start_date > request.end_date:
                raise HTTPException(status_code=400, detail="Start date cannot be after end date")

        prediction = await PredictionService.predict_stock(
            symbol=request.symbol,
            force_refresh=request.force_refresh,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to generate prediction for {request.symbol}. Insufficient historical data."
            )

        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/model-metrics")
async def get_model_metrics(symbol: str = "RELIANCE.NS", horizon: int = 30):
    """
    Returns empirical evaluation metrics (MAE, RMSE, R², Directional Accuracy) for a trained ML model.
    """
    try:
        norm_symbol = PredictionService.normalize_symbol(symbol)
        artifact = ModelManager.load_model(norm_symbol, horizon)
        if not artifact:
            # Auto train model if missing
            artifact = train_single_model(norm_symbol, horizon=horizon)

        if not artifact:
            raise HTTPException(status_code=404, detail=f"No ML model found or trained for {norm_symbol} ({horizon}d)")

        return {
            "symbol": norm_symbol,
            "horizon": horizon,
            "model_name": artifact.get("model_name"),
            "model_version": artifact.get("model_version"),
            "metrics": artifact.get("metrics"),
            "trained_at": artifact.get("trained_at"),
            "data_summary": artifact.get("data_summary")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching model metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch model metrics: {str(e)}")


@router.get("/feature-importance")
async def get_feature_importance(symbol: str = "RELIANCE.NS", horizon: int = 30):
    """
    Returns Random Forest feature importance rankings from highest to lowest.
    """
    try:
        norm_symbol = PredictionService.normalize_symbol(symbol)
        artifact = ModelManager.load_model(norm_symbol, horizon)
        if not artifact:
            artifact = train_single_model(norm_symbol, horizon=horizon)

        if not artifact or "feature_importance" not in artifact:
            raise HTTPException(status_code=404, detail=f"Feature importance data unavailable for {norm_symbol}")

        return {
            "symbol": norm_symbol,
            "horizon": horizon,
            "model_name": artifact.get("model_name"),
            "feature_importance": artifact.get("feature_importance"),
            "disclaimer": "Feature importance represents relative statistical contribution in the Random Forest ensemble. It does not establish causal relationships."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature importance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get feature importance: {str(e)}")


@router.post("/train")
async def train_model_endpoint(symbol: str = "RELIANCE.NS", horizon: int = 30):
    """
    Triggers single-stock ML model training for an explicit symbol and horizon.
    """
    try:
        norm_symbol = PredictionService.normalize_symbol(symbol)
        artifact = train_single_model(norm_symbol, horizon=horizon)
        if not artifact:
            raise HTTPException(status_code=400, detail=f"Model training failed for {norm_symbol}")

        return {
            "status": "success",
            "message": f"ML model successfully trained and saved for {norm_symbol} ({horizon}d)",
            "metrics": artifact.get("metrics"),
            "trained_at": artifact.get("trained_at")
        }
    except Exception as e:
        logger.error(f"Training endpoint error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/accuracy")
async def get_prediction_accuracy(authorization: Optional[str] = Header(None)):
    """
    Get historical prediction accuracy metrics.
    """
    try:
        return PredictionService.calculate_accuracy()
    except Exception as e:
        logger.error(f"Error calculating accuracy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate accuracy: {str(e)}")


@router.post("/refresh")
async def refresh_all_predictions(authorization: Optional[str] = Header(None)):
    """
    Force refresh predictions cache.
    """
    try:
        PredictionService.PREDICTION_CACHE = {}
        PredictionService.save_cache()
        predictions = await PredictionService.get_top_predictions(limit=25, force_refresh=True)

        return {
            "status": "success",
            "message": f"Refreshed {len(predictions)} ML predictions",
            "count": len(predictions)
        }
    except Exception as e:
        logger.error(f"Error refreshing predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@router.get("/symbols")
async def get_available_symbols():
    """
    Get list of all supported Indian stock symbols for ML prediction.
    """
    return {
        "symbols": PredictionService.INDIAN_STOCKS,
        "total": len(PredictionService.INDIAN_STOCKS)
    }
