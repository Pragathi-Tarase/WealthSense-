from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from models import StockPrediction, PredictionListResponse, PredictionRequest
from services.prediction_service import PredictionService
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
    Get top stock predictions ranked by combined score
    
    Args:
        limit: Number of predictions to return (default: 10, max: 25)
        force_refresh: Force regeneration of predictions instead of using cache
        authorization: Optional JWT token for personalized predictions
    
    Returns:
        List of predictions with accuracy metrics
    """
    try:
        # Limit to max 25
        limit = min(limit, 25)
        
        # Get top predictions
        predictions = await PredictionService.get_top_predictions(limit=limit, force_refresh=force_refresh)
        
        # Get accuracy metrics
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
    Get prediction for a specific stock symbol
    
    Args:
        request: Contains symbol and force_refresh flag
        authorization: Optional JWT token
    
    Returns:
        Detailed prediction for the requested stock
    """
    try:
        prediction = await PredictionService.predict_stock(
            symbol=request.symbol,
            force_refresh=request.force_refresh
        )
        
        if prediction is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to generate prediction for {request.symbol}. Stock may not have sufficient data."
            )
        
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.get("/accuracy")
async def get_prediction_accuracy(authorization: Optional[str] = Header(None)):
    """
    Get historical prediction accuracy metrics
    
    Returns:
        Accuracy statistics and performance metrics
    """
    try:
        accuracy = PredictionService.calculate_accuracy()
        return accuracy
    except Exception as e:
        logger.error(f"Error calculating accuracy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate accuracy: {str(e)}")

@router.post("/refresh")
async def refresh_all_predictions(authorization: Optional[str] = Header(None)):
    """
    Force refresh all predictions (clears cache and regenerates)
    
    Note: This may take a few minutes to complete
    """
    try:
        # Clear cache
        PredictionService.PREDICTION_CACHE = {}
        PredictionService.save_cache()
        
        # Regenerate top predictions
        predictions = await PredictionService.get_top_predictions(limit=25, force_refresh=True)
        
        return {
            "status": "success",
            "message": f"Refreshed {len(predictions)} predictions",
            "count": len(predictions)
        }
    except Exception as e:
        logger.error(f"Error refreshing predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

@router.get("/symbols")
async def get_available_symbols():
    """
    Get list of all available Indian stock symbols for prediction
    
    Returns:
        List of symbols that can be predicted
    """
    return {
        "symbols": PredictionService.INDIAN_STOCKS,
        "total": len(PredictionService.INDIAN_STOCKS)
    }
