import argparse
import logging
import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestRegressor

# Ensure parent path is in sys.path when script is executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.features import prepare_training_data, FEATURE_COLUMNS
from ml.evaluate import evaluate_predictions
from ml.model_manager import ModelManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# List of top Indian stocks (NSE symbols) for prediction
DEFAULT_INDIAN_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "WIPRO.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS",
    "ADANIPORTS.NS", "ZOMATO.NS", "IRCTC.NS", "PAYTM.NS", "NYKAA.NS"
]

HORIZONS = [30, 60, 90]


def train_single_model(
    symbol: str,
    horizon: int = 30,
    period: str = "5y",
    test_size: float = 0.2,
    n_estimators: int = 100,
    random_state: int = 42
) -> Optional[Dict]:
    """
    Downloads historical data via yfinance, engineers technical features,
    performs chronological time-series splitting, trains a RandomForestRegressor,
    evaluates model metrics, and persists the trained artifact.
    """
    logger.info(f"=== Training ML Model for {symbol} (Horizon: {horizon}d, Period: {period}) ===")

    try:
        # 1. Ingest Data via yfinance
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty or len(df) < 150:
            logger.warning(f"Insufficient historical data for {symbol} (found {len(df)} rows)")
            return None

        # 2. Feature Engineering & Target Preparation
        X, y = prepare_training_data(df, horizon=horizon)

        if len(X) < 100:
            logger.warning(f"Insufficient aligned training samples for {symbol}: {len(X)}")
            return None

        # 3. Time-Series Safe Chronological Split (No random shuffling!)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        logger.info(f"Dataset split: Train samples={len(X_train)}, Held-out Test samples={len(X_test)}")

        # 4. Train Primary Model: RandomForestRegressor
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=12,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1
        )
        model.fit(X_train, y_train)

        # 5. Evaluate on Held-Out Test Set
        y_pred_test = model.predict(X_test)
        metrics = evaluate_predictions(y_test.values, y_pred_test)

        logger.info(f"Evaluation Results for {symbol} ({horizon}d): "
                    f"MAE={metrics['mae']}%, RMSE={metrics['rmse']}%, R²={metrics['r2']}, "
                    f"Directional Accuracy={metrics['directional_accuracy']}%")

        # 6. Extract Feature Importance
        importances = model.feature_importances_
        feature_importance_list = sorted(
            [{"feature": f, "importance": round(float(imp), 4)} for f, imp in zip(FEATURE_COLUMNS, importances)],
            key=lambda x: x["importance"],
            reverse=True
        )

        # 7. Package Model Artifact
        artifact = {
            "symbol": symbol,
            "horizon": horizon,
            "model_name": "RandomForestRegressor",
            "model_version": "1.0.0",
            "model": model,
            "features": FEATURE_COLUMNS,
            "metrics": metrics,
            "feature_importance": feature_importance_list,
            "trained_at": datetime.now().isoformat(),
            "data_summary": {
                "total_samples": len(X),
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "last_historical_date": df.index[-1].strftime("%Y-%m-%d")
            }
        }

        # 8. Save Artifact using ModelManager
        saved_path = ModelManager.save_model(symbol, horizon, artifact)
        artifact["saved_path"] = saved_path

        return artifact

    except Exception as e:
        logger.error(f"Error training model for {symbol} ({horizon}d): {e}", exc_info=True)
        return None


def train_bulk_models(symbols: List[str] = None, horizons: List[int] = HORIZONS) -> Dict:
    """
    Bulk trains ML models for all supported stock symbols and target horizons.
    """
    if symbols is None:
        symbols = DEFAULT_INDIAN_STOCKS

    logger.info(f"Starting Bulk ML Model Training for {len(symbols)} stocks across {horizons} horizons")
    results = {}

    for symbol in symbols:
        results[symbol] = {}
        for horizon in horizons:
            res = train_single_model(symbol, horizon=horizon)
            if res:
                results[symbol][f"{horizon}d"] = res["metrics"]
            else:
                results[symbol][f"{horizon}d"] = "FAILED"

    logger.info("Bulk training completed successfully!")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train WealthSense Stock Prediction ML Models")
    parser.add_argument("--symbol", type=str, default="RELIANCE.NS", help="Stock symbol to train (e.g. RELIANCE.NS)")
    parser.add_argument("--horizon", type=int, default=30, choices=[30, 60, 90], help="Prediction horizon in days")
    parser.add_argument("--bulk", action="store_true", help="Train models for all supported Indian stocks")

    args = parser.parse_args()

    if args.bulk:
        train_bulk_models()
    else:
        artifact = train_single_model(args.symbol, horizon=args.horizon)
        if artifact:
            print("\n=== TRAINING SUCCESSFUL ===")
            print(f"Symbol: {artifact['symbol']}")
            print(f"Horizon: {artifact['horizon']} Days")
            print(f"Model: {artifact['model_name']}")
            print(f"MAE: {artifact['metrics']['mae']}%")
            print(f"RMSE: {artifact['metrics']['rmse']}%")
            print(f"R²: {artifact['metrics']['r2']}")
            print(f"Directional Accuracy: {artifact['metrics']['directional_accuracy']}%")
            print("\nTop 5 Influential Features:")
            for item in artifact["feature_importance"][:5]:
                print(f"  - {item['feature']}: {item['importance']}")
        else:
            print("\n!!! TRAINING FAILED !!!")
            sys.exit(1)
