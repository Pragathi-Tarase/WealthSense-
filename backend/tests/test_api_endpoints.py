import unittest
import os
import sys

# Ensure backend root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from main import app


class TestPredictionAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_symbols_endpoint(self):
        response = self.client.get("/api/predictions/symbols")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("symbols", data)
        self.assertIn("RELIANCE.NS", data["symbols"])

    def test_get_accuracy_endpoint(self):
        response = self.client.get("/api/predictions/accuracy")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("accuracy_rate", data)

    def test_post_stock_prediction_endpoint(self):
        payload = {
            "symbol": "RELIANCE.NS",
            "horizon": 30
        }
        response = self.client.post("/api/predictions/stock", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["symbol"], "RELIANCE.NS")
        self.assertIn("predictions", data)
        self.assertIn("recommendation", data)
        self.assertIn("confidence", data)

    def test_get_top_predictions_endpoint(self):
        response = self.client.get("/api/predictions/top?limit=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("predictions", data)
        self.assertLessEqual(len(data["predictions"]), 2)

    def test_get_model_metrics_endpoint(self):
        response = self.client.get("/api/predictions/model-metrics?symbol=RELIANCE.NS&horizon=30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["symbol"], "RELIANCE.NS")
        self.assertIn("metrics", data)

    def test_get_feature_importance_endpoint(self):
        response = self.client.get("/api/predictions/feature-importance?symbol=RELIANCE.NS&horizon=30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["symbol"], "RELIANCE.NS")
        self.assertIn("feature_importance", data)

    def test_post_train_endpoint(self):
        response = self.client.post("/api/predictions/train?symbol=RELIANCE.NS&horizon=30")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")


if __name__ == "__main__":
    unittest.main()
