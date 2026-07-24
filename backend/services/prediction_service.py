import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from ta.trend import MACD, SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import json
import os

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Hybrid Stock Prediction Service
    Combines Technical Analysis + News Sentiment for long-term predictions
    """
    
    # Cache for predictions (24-hour validity)
    PREDICTION_CACHE = {}
    CACHE_FILE = "prediction_cache.json"
    
    # Prediction history for accuracy tracking
    PREDICTION_HISTORY = []
    HISTORY_FILE = "prediction_history.json"
    
    # Indian stocks for prediction (NSE symbols)
    INDIAN_STOCKS = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
        "HCLTECH.NS", "WIPRO.NS", "SUNPHARMA.NS", "TITAN.NS", "TATASTEEL.NS",
        "ADANIPORTS.NS", "ZOMATO.NS", "IRCTC.NS", "PAYTM.NS", "NYKAA.NS"
    ]
    
    @classmethod
    def load_cache(cls):
        """Load prediction cache from file"""
        try:
            if os.path.exists(cls.CACHE_FILE):
                with open(cls.CACHE_FILE, 'r') as f:
                    cls.PREDICTION_CACHE = json.load(f)
                    logger.info(f"Loaded {len(cls.PREDICTION_CACHE)} cached predictions")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    
    @classmethod
    def save_cache(cls):
        """Save prediction cache to file"""
        try:
            with open(cls.CACHE_FILE, 'w') as f:
                json.dump(cls.PREDICTION_CACHE, f)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    @classmethod
    def load_history(cls):
        """Load prediction history from file"""
        try:
            if os.path.exists(cls.HISTORY_FILE):
                with open(cls.HISTORY_FILE, 'r') as f:
                    cls.PREDICTION_HISTORY = json.load(f)
                    logger.info(f"Loaded {len(cls.PREDICTION_HISTORY)} historical predictions")
        except Exception as e:
            logger.error(f"Error loading history: {e}")
    
    @classmethod
    def save_history(cls):
        """Save prediction history to file"""
        try:
            with open(cls.HISTORY_FILE, 'w') as f:
                json.dump(cls.PREDICTION_HISTORY, f)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    @classmethod
    async def get_stock_data(cls, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """Fetch historical stock data using yfinance"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None
            
            return data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    @classmethod
    def calculate_technical_indicators(cls, data: pd.DataFrame) -> Dict:
        """Calculate technical indicators for prediction"""
        try:
            # Price data
            close_prices = data['Close']
            
            # 1. Moving Averages
            sma_50 = close_prices.rolling(window=50).mean().iloc[-1]
            sma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            # 2. RSI (Relative Strength Index)
            rsi_indicator = RSIIndicator(close=close_prices, window=14)
            rsi = rsi_indicator.rsi().iloc[-1]
            
            # 3. MACD
            macd_indicator = MACD(close=close_prices)
            macd = macd_indicator.macd().iloc[-1]
            macd_signal = macd_indicator.macd_signal().iloc[-1]
            macd_diff = macd_indicator.macd_diff().iloc[-1]
            
            # 4. Bollinger Bands
            bb_indicator = BollingerBands(close=close_prices)
            bb_high = bb_indicator.bollinger_hband().iloc[-1]
            bb_low = bb_indicator.bollinger_lband().iloc[-1]
            bb_mid = bb_indicator.bollinger_mavg().iloc[-1]
            
            # 5. Price Momentum (last 30 days)
            price_30d_ago = close_prices.iloc[-30] if len(close_prices) >= 30 else close_prices.iloc[0]
            momentum_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
            
            # 6. Volatility (standard deviation of returns)
            returns = close_prices.pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            return {
                "current_price": float(current_price),
                "sma_50": float(sma_50),
                "sma_200": float(sma_200),
                "rsi": float(rsi),
                "macd": float(macd),
                "macd_signal": float(macd_signal),
                "macd_diff": float(macd_diff),
                "bb_high": float(bb_high),
                "bb_low": float(bb_low),
                "bb_mid": float(bb_mid),
                "momentum_30d": float(momentum_30d),
                "volatility": float(volatility)
            }
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
    
    @classmethod
    def analyze_technical_signals(cls, indicators: Dict) -> Dict:
        """Analyze technical indicators and generate signals"""
        signals = []
        score = 0
        
        # 1. Moving Average Crossover (Golden Cross / Death Cross)
        if indicators["current_price"] > indicators["sma_50"] > indicators["sma_200"]:
            signals.append("Golden Cross: Strong uptrend")
            score += 25
        elif indicators["current_price"] < indicators["sma_50"] < indicators["sma_200"]:
            signals.append("Death Cross: Strong downtrend")
            score -= 25
        elif indicators["current_price"] > indicators["sma_50"]:
            signals.append("Above 50-day MA: Bullish")
            score += 10
        else:
            signals.append("Below 50-day MA: Bearish")
            score -= 10
        
        # 2. RSI Analysis
        rsi = indicators["rsi"]
        if rsi < 30:
            signals.append(f"RSI {rsi:.1f}: Oversold - potential buy")
            score += 20
        elif rsi > 70:
            signals.append(f"RSI {rsi:.1f}: Overbought - potential sell")
            score -= 20
        elif 40 <= rsi <= 60:
            signals.append(f"RSI {rsi:.1f}: Neutral momentum")
            score += 5
        
        # 3. MACD Analysis
        if indicators["macd_diff"] > 0:
            signals.append("MACD: Bullish crossover")
            score += 15
        else:
            signals.append("MACD: Bearish crossover")
            score -= 15
        
        # 4. Bollinger Bands
        price = indicators["current_price"]
        if price < indicators["bb_low"]:
            signals.append("Price below lower Bollinger Band: Oversold")
            score += 10
        elif price > indicators["bb_high"]:
            signals.append("Price above upper Bollinger Band: Overbought")
            score -= 10
        
        # 5. Momentum
        momentum = indicators["momentum_30d"]
        if momentum > 10:
            signals.append(f"Strong positive momentum: +{momentum:.1f}%")
            score += 10
        elif momentum < -10:
            signals.append(f"Strong negative momentum: {momentum:.1f}%")
            score -= 10
        
        # 6. Volatility Risk
        volatility = indicators["volatility"]
        if volatility > 0.4:
            signals.append(f"High volatility: {volatility:.1%} - Risky")
            score -= 5
        
        return {
            "signals": signals,
            "technical_score": max(-100, min(100, score))  # Clamp to -100 to 100
        }
    
    @classmethod
    async def get_sentiment_score(cls, symbol: str, news_data: Optional[List] = None) -> Dict:
        """Get sentiment score from news (if available)"""
        # For now, use a simplified sentiment based on momentum
        # In production, this would integrate with your NewsAPI + Gemini analysis
        try:
            # Placeholder: You can integrate with your existing news_service.py here
            sentiment_score = 0  # Range: -50 to +50
            sentiment_signals = []
            
            # If news_data is provided (from NewsAPI), analyze it
            if news_data and len(news_data) > 0:
                # Simple sentiment based on news count and keywords
                bullish_keywords = ["profit", "growth", "expansion", "bullish", "rally", "surge"]
                bearish_keywords = ["loss", "decline", "bearish", "crash", "fall", "debt"]
                
                bullish_count = 0
                bearish_count = 0
                
                for article in news_data[:10]:  # Check top 10 articles
                    title = article.get("title", "").lower()
                    description = article.get("description", "").lower()
                    text = title + " " + description
                    
                    if any(word in text for word in bullish_keywords):
                        bullish_count += 1
                    if any(word in text for word in bearish_keywords):
                        bearish_count += 1
                
                if bullish_count > bearish_count:
                    sentiment_score = min(50, bullish_count * 10)
                    sentiment_signals.append(f"Positive news sentiment: {bullish_count} bullish articles")
                elif bearish_count > bullish_count:
                    sentiment_score = max(-50, -bearish_count * 10)
                    sentiment_signals.append(f"Negative news sentiment: {bearish_count} bearish articles")
                else:
                    sentiment_signals.append("Neutral news sentiment")
            else:
                sentiment_signals.append("No recent news data available")
            
            return {
                "sentiment_score": sentiment_score,
                "sentiment_signals": sentiment_signals
            }
        except Exception as e:
            logger.error(f"Error calculating sentiment: {e}")
            return {"sentiment_score": 0, "sentiment_signals": ["Sentiment analysis unavailable"]}
    
    @classmethod
    def calculate_prediction(cls, technical_analysis: Dict, sentiment_analysis: Dict, indicators: Dict) -> Dict:
        """Generate final prediction based on technical + sentiment analysis"""
        
        # Weighted scoring (60% technical, 40% sentiment)
        technical_score = technical_analysis["technical_score"]
        sentiment_score = sentiment_analysis["sentiment_score"]
        
        combined_score = (technical_score * 0.6) + (sentiment_score * 0.4)
        
        # Predict price movement for different timeframes
        current_price = indicators["current_price"]
        volatility = indicators["volatility"]
        
        # Base prediction on combined score (-100 to +100)
        # Map score to percentage gain/loss
        prediction_1m = (combined_score / 100) * 5 * (1 + volatility)  # 1 month
        prediction_3m = (combined_score / 100) * 12 * (1 + volatility)  # 3 months
        prediction_6m = (combined_score / 100) * 20 * (1 + volatility)  # 6 months
        
        # Calculate confidence (based on score strength and low volatility)
        confidence_raw = abs(combined_score) * (1 - min(volatility, 0.5))
        
        if confidence_raw > 60:
            confidence = "HIGH"
            confidence_percent = min(95, 60 + (confidence_raw - 60) * 0.5)
        elif confidence_raw > 30:
            confidence = "MEDIUM"
            confidence_percent = 40 + (confidence_raw - 30)
        else:
            confidence = "LOW"
            confidence_percent = max(20, confidence_raw)
        
        # Determine risk level
        if volatility > 0.4:
            risk = "AGGRESSIVE"
        elif volatility > 0.25:
            risk = "MODERATE"
        else:
            risk = "CONSERVATIVE"
        
        # Generate recommendation
        if combined_score > 40:
            recommendation = "STRONG BUY"
        elif combined_score > 15:
            recommendation = "BUY"
        elif combined_score > -15:
            recommendation = "HOLD"
        elif combined_score > -40:
            recommendation = "SELL"
        else:
            recommendation = "STRONG SELL"
        
        # Target prices
        target_1m = current_price * (1 + prediction_1m / 100)
        target_3m = current_price * (1 + prediction_3m / 100)
        target_6m = current_price * (1 + prediction_6m / 100)
        
        return {
            "combined_score": round(combined_score, 2),
            "predictions": {
                "1_month": {
                    "percent_change": round(prediction_1m, 2),
                    "target_price": round(target_1m, 2)
                },
                "3_months": {
                    "percent_change": round(prediction_3m, 2),
                    "target_price": round(target_3m, 2)
                },
                "6_months": {
                    "percent_change": round(prediction_6m, 2),
                    "target_price": round(target_6m, 2)
                }
            },
            "confidence": confidence,
            "confidence_percent": round(confidence_percent, 1),
            "risk_level": risk,
            "recommendation": recommendation,
            "reasoning": technical_analysis["signals"] + sentiment_analysis["sentiment_signals"]
        }
    
    @classmethod
    async def predict_stock(cls, symbol: str, news_data: Optional[List] = None, force_refresh: bool = False) -> Optional[Dict]:
        """Main method to generate stock prediction"""
        
        # Check cache first (unless force refresh)
        cache_key = symbol
        if not force_refresh and cache_key in cls.PREDICTION_CACHE:
            cached = cls.PREDICTION_CACHE[cache_key]
            cache_time = datetime.fromisoformat(cached["generated_at"])
            
            # Cache valid for 24 hours
            if datetime.now() - cache_time < timedelta(hours=24):
                logger.info(f"Returning cached prediction for {symbol}")
                return cached["prediction"]
        
        try:
            # 1. Fetch historical data
            data = await cls.get_stock_data(symbol)
            if data is None or len(data) < 200:  # Need enough data for 200-day MA
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # 2. Calculate technical indicators
            indicators = cls.calculate_technical_indicators(data)
            if indicators is None:
                return None
            
            # 3. Analyze technical signals
            technical_analysis = cls.analyze_technical_signals(indicators)
            
            # 4. Get sentiment analysis
            sentiment_analysis = await cls.get_sentiment_score(symbol, news_data)
            
            # 5. Generate final prediction
            prediction = cls.calculate_prediction(technical_analysis, sentiment_analysis, indicators)
            
            # 6. Add metadata
            ticker_info = {}
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                ticker_info = {
                    "name": info.get("longName", symbol),
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown")
                }
            except:
                ticker_info = {"name": symbol, "sector": "Unknown", "industry": "Unknown"}
            
            result = {
                "symbol": symbol,
                "name": ticker_info["name"],
                "sector": ticker_info["sector"],
                "industry": ticker_info["industry"],
                "current_price": indicators["current_price"],
                **prediction,
                "generated_at": datetime.now().isoformat()
            }
            
            # Cache the result
            cls.PREDICTION_CACHE[cache_key] = {
                "prediction": result,
                "generated_at": datetime.now().isoformat()
            }
            cls.save_cache()
            
            # Add to history for accuracy tracking
            cls.PREDICTION_HISTORY.append({
                "symbol": symbol,
                "prediction": result,
                "actual_performance": None,  # Will be updated later
                "predicted_at": datetime.now().isoformat()
            })
            cls.save_history()
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting {symbol}: {e}")
            return None
    
    @classmethod
    async def get_top_predictions(cls, limit: int = 10, force_refresh: bool = False) -> List[Dict]:
        """Get top N predictions sorted by combined score"""
        predictions = []
        
        for symbol in cls.INDIAN_STOCKS[:25]:  # Analyze top 25 stocks
            try:
                prediction = await cls.predict_stock(symbol, force_refresh=force_refresh)
                if prediction:
                    predictions.append(prediction)
            except Exception as e:
                logger.error(f"Error predicting {symbol}: {e}")
                continue
        
        # Sort by combined score (descending)
        predictions.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return predictions[:limit]
    
    @classmethod
    def calculate_accuracy(cls) -> Dict:
        """Calculate prediction accuracy from historical data"""
        if not cls.PREDICTION_HISTORY:
            cls.load_history()
        
        total_predictions = len(cls.PREDICTION_HISTORY)
        if total_predictions == 0:
            return {
                "total_predictions": 0,
                "accuracy_rate": 0,
                "average_error": 0
            }
        
        accurate_predictions = 0
        total_error = 0
        
        for record in cls.PREDICTION_HISTORY:
            if record.get("actual_performance") is not None:
                predicted = record["prediction"]["predictions"]["3_months"]["percent_change"]
                actual = record["actual_performance"]["3_month_change"]
                
                # Consider accurate if within 5% of actual
                if abs(predicted - actual) < 5:
                    accurate_predictions += 1
                
                total_error += abs(predicted - actual)
        
        evaluated_predictions = sum(1 for r in cls.PREDICTION_HISTORY if r.get("actual_performance"))
        
        return {
            "total_predictions": total_predictions,
            "evaluated_predictions": evaluated_predictions,
            "accuracy_rate": round((accurate_predictions / evaluated_predictions * 100), 2) if evaluated_predictions > 0 else 0,
            "average_error": round((total_error / evaluated_predictions), 2) if evaluated_predictions > 0 else 0,
            "pending_evaluation": total_predictions - evaluated_predictions
        }

# Initialize on import
PredictionService.load_cache()
PredictionService.load_history()
