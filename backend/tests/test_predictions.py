import unittest
import os
import sys
import pandas as pd
import numpy as np

# Add backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from ml.features import calculate_features, create_target, prepare_training_data, FEATURE_COLUMNS
from ml.evaluate import evaluate_predictions
from ml.model_manager import ModelManager
from ml.train_model import train_single_model
from ml.predict import predict_stock_ml


class TestMLPipeline(unittest.TestCase):

    def setUp(self):
        """Generate mock daily OHLCV historical dataframe for testing"""
        dates = pd.date_range(start="2022-01-01", periods=300, freq="B")
        np.random.seed(42)
        price_trend = np.linspace(100, 150, 300) + np.random.normal(0, 2, 300)
        
        self.mock_df = pd.DataFrame({
            'Open': price_trend * 0.99,
            'High': price_trend * 1.02,
            'Low': price_trend * 0.98,
            'Close': price_trend,
            'Volume': np.random.randint(100000, 1000000, 300)
        }, index=dates)

    def test_feature_calculation(self):
        features = calculate_features(self.mock_df)
        self.assertFalse(features.empty)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, features.columns)
        self.assertEqual(len(features), len(self.mock_df))
        self.assertFalse(features.isnull().values.any())

    def test_target_creation(self):
        target_30 = create_target(self.mock_df, horizon=30)
        self.assertEqual(len(target_30), len(self.mock_df))
        # Target for last 30 rows should be NaN before dropna
        self.assertTrue(pd.isna(target_30.iloc[-1]))
        self.assertFalse(pd.isna(target_30.iloc[0]))

    def test_prepare_training_data(self):
        X, y = prepare_training_data(self.mock_df, horizon=30)
        self.assertEqual(len(X), len(y))
        self.assertEqual(len(X), 300 - 30)
        self.assertFalse(X.isnull().values.any())
        self.assertFalse(y.isnull().values.any())

    def test_evaluate_predictions(self):
        y_true = np.array([0.05, -0.02, 0.10, -0.04])
        y_pred = np.array([0.04, -0.01, 0.08, 0.02])
        
        metrics = evaluate_predictions(y_true, y_pred)
        self.assertIn("mae", metrics)
        self.assertIn("rmse", metrics)
        self.assertIn("r2", metrics)
        self.assertIn("directional_accuracy", metrics)
        self.assertGreaterEqual(metrics["directional_accuracy"], 0.0)
        self.assertLessEqual(metrics["directional_accuracy"], 100.0)

    def test_model_manager(self):
        test_artifact = {
            "symbol": "TEST.NS",
            "horizon": 30,
            "model_name": "TestModel",
            "metrics": {"mae": 1.0, "rmse": 1.5, "r2": 0.5, "directional_accuracy": 70.0}
        }
        saved_path = ModelManager.save_model("TEST.NS", 30, test_artifact)
        self.assertTrue(os.path.exists(saved_path))
        
        loaded = ModelManager.load_model("TEST.NS", 30)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["symbol"], "TEST.NS")
        self.assertEqual(loaded["model_name"], "TestModel")

    def test_ml_inference_invalid_symbol(self):
        # Invalid ticker should handle gracefully without crashing
        res = predict_stock_ml("INVALID_TICKER_XYZ_999", horizon=30)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
