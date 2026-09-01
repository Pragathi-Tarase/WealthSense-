import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
import logging
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

logger = logging.getLogger(__name__)

# Canonical feature columns used for ML model training and inference
FEATURE_COLUMNS = [
    'Open',
    'High',
    'Low',
    'Close',
    'Volume',
    'sma_20',
    'sma_50',
    'sma_200',
    'price_sma20_ratio',
    'price_sma50_ratio',
    'price_sma200_ratio',
    'rsi_14',
    'macd',
    'macd_signal',
    'macd_hist',
    'bb_width',
    'daily_return',
    'return_5d',
    'return_10d',
    'return_20d',
    'volatility_20d',
    'volume_ratio',
    'momentum_14',
    'close_lag1',
    'close_lag5',
    'return_lag1',
    'sentiment_score'
]


def calculate_features(df: pd.DataFrame, sentiment_score: float = 0.0) -> pd.DataFrame:
    """
    Computes technical indicators, price ratios, momentum, volatility, and lag features
    from raw OHLCV price history.
    """
    if df is None or df.empty or len(df) < 30:
        logger.warning("Insufficient data to compute features")
        return pd.DataFrame()

    data = df.copy()

    # Ensure required columns exist
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")

    # 1. Moving Averages & Price Ratios
    close = data['Close']
    data['sma_20'] = close.rolling(window=20, min_periods=5).mean()
    data['sma_50'] = close.rolling(window=50, min_periods=10).mean()
    data['sma_200'] = close.rolling(window=200, min_periods=20).mean()

    # Fill initial NaN in moving averages with backfill/ffill
    data['sma_20'] = data['sma_20'].bfill().ffill()
    data['sma_50'] = data['sma_50'].bfill().ffill()
    data['sma_200'] = data['sma_200'].bfill().ffill()

    data['price_sma20_ratio'] = close / data['sma_20']
    data['price_sma50_ratio'] = close / data['sma_50']
    data['price_sma200_ratio'] = close / data['sma_200']

    # 2. RSI (14)
    rsi_indicator = RSIIndicator(close=close, window=14)
    data['rsi_14'] = rsi_indicator.rsi().fillna(50.0)

    # 3. MACD
    macd_indicator = MACD(close=close)
    data['macd'] = macd_indicator.macd().fillna(0.0)
    data['macd_signal'] = macd_indicator.macd_signal().fillna(0.0)
    data['macd_hist'] = macd_indicator.macd_diff().fillna(0.0)

    # 4. Bollinger Bands
    bb_indicator = BollingerBands(close=close)
    bb_high = bb_indicator.bollinger_hband().bfill().ffill()
    bb_low = bb_indicator.bollinger_lband().bfill().ffill()
    bb_mid = bb_indicator.bollinger_mavg().bfill().ffill()
    data['bb_width'] = ((bb_high - bb_low) / (bb_mid + 1e-8)).fillna(0.0)

    # 5. Returns & Volatility
    data['daily_return'] = close.pct_change().fillna(0.0)
    data['return_5d'] = close.pct_change(5).fillna(0.0)
    data['return_10d'] = close.pct_change(10).fillna(0.0)
    data['return_20d'] = close.pct_change(20).fillna(0.0)
    data['volatility_20d'] = data['daily_return'].rolling(window=20, min_periods=5).std().fillna(0.0)

    # 6. Volume Moving Average Ratio
    vol_sma20 = data['Volume'].rolling(window=20, min_periods=5).mean().bfill().ffill()
    data['volume_ratio'] = (data['Volume'] / (vol_sma20 + 1.0)).fillna(1.0)

    # 7. Momentum
    data['momentum_14'] = (close - close.shift(14)).fillna(0.0)

    # 8. Lagged Features
    data['close_lag1'] = close.shift(1).bfill()
    data['close_lag5'] = close.shift(5).bfill()
    data['return_lag1'] = data['daily_return'].shift(1).fillna(0.0)

    # 9. Sentiment Score
    data['sentiment_score'] = float(sentiment_score)

    # Replace inf or -inf with 0
    data = data.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    return data[FEATURE_COLUMNS]


def create_target(df: pd.DataFrame, horizon: int = 30) -> pd.Series:
    """
    Creates target percentage return for a specified trading day horizon (30, 60, 90).
    target_pct = (Close_{t + horizon} - Close_t) / Close_t
    """
    if 'Close' not in df.columns:
        raise ValueError("DataFrame must contain 'Close' column to compute target")
    
    close = df['Close']
    target = (close.shift(-horizon) - close) / close
    target.name = f"target_{horizon}d"
    return target


def prepare_training_data(df: pd.DataFrame, horizon: int = 30, sentiment_score: float = 0.0) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepares aligned feature matrix X and target vector y for training.
    Drops trailing rows where target is NaN (due to future lookahead window).
    """
    features = calculate_features(df, sentiment_score=sentiment_score)
    target = create_target(df, horizon=horizon)

    # Combine to align and drop NaNs in target
    combined = pd.concat([features, target], axis=1).dropna(subset=[f"target_{horizon}d"])

    X = combined[FEATURE_COLUMNS]
    y = combined[f"target_{horizon}d"]
    return X, y
