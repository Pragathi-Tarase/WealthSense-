import os
import joblib
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directory for storing trained model artifacts
MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")

class ModelManager:
    """
    Manages saving, loading, and querying trained ML model artifacts (.joblib).
    """

    @classmethod
    def _ensure_dir(cls):
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR, exist_ok=True)

    @classmethod
    def get_model_filename(cls, symbol: str, horizon: int) -> str:
        safe_symbol = symbol.replace(".", "_").replace(":", "_").upper()
        return f"model_{safe_symbol}_{horizon}d.joblib"

    @classmethod
    def get_model_path(cls, symbol: str, horizon: int) -> str:
        cls._ensure_dir()
        filename = cls.get_model_filename(symbol, horizon)
        return os.path.join(MODEL_DIR, filename)

    @classmethod
    def save_model(cls, symbol: str, horizon: int, model_artifact: Dict[str, Any]) -> str:
        """
        Saves a trained model artifact to disk.
        """
        cls._ensure_dir()
        path = cls.get_model_path(symbol, horizon)
        
        # Ensure timestamp is set
        if "trained_at" not in model_artifact:
            model_artifact["trained_at"] = datetime.now().isoformat()
            
        try:
            joblib.dump(model_artifact, path)
            logger.info(f"[ModelManager] Saved model artifact to {path}")
            return path
        except Exception as e:
            logger.error(f"[ModelManager] Failed to save model to {path}: {e}")
            raise e

    @classmethod
    def load_model(cls, symbol: str, horizon: int) -> Optional[Dict[str, Any]]:
        """
        Loads a trained model artifact from disk if available.
        """
        path = cls.get_model_path(symbol, horizon)
        if not os.path.exists(path):
            logger.debug(f"[ModelManager] No model artifact found at {path}")
            return None

        try:
            artifact = joblib.load(path)
            logger.info(f"[ModelManager] Loaded model artifact for {symbol} ({horizon}d)")
            return artifact
        except Exception as e:
            logger.error(f"[ModelManager] Error loading model from {path}: {e}")
            return None

    @classmethod
    def has_model(cls, symbol: str, horizon: int) -> bool:
        path = cls.get_model_path(symbol, horizon)
        return os.path.exists(path)

    @classmethod
    def list_available_models(cls) -> Dict[str, Any]:
        """
        Lists all trained models currently stored in MODEL_DIR.
        """
        cls._ensure_dir()
        models = []
        for fname in os.listdir(MODEL_DIR):
            if fname.endswith(".joblib") and fname.startswith("model_"):
                fpath = os.path.join(MODEL_DIR, fname)
                try:
                    artifact = joblib.load(fpath)
                    models.append({
                        "filename": fname,
                        "symbol": artifact.get("symbol"),
                        "horizon": artifact.get("horizon"),
                        "model_name": artifact.get("model_name"),
                        "metrics": artifact.get("metrics"),
                        "trained_at": artifact.get("trained_at")
                    })
                except Exception:
                    continue
        return {"total": len(models), "models": models}
