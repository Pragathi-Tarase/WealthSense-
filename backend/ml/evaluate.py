import numpy as np
from typing import Dict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes regression evaluation metrics (MAE, RMSE, R²)
    and directional prediction accuracy (% correct trend direction).
    """
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    if len(y_true) == 0 or len(y_pred) == 0:
        return {
            "mae": 0.0,
            "rmse": 0.0,
            "r2": 0.0,
            "directional_accuracy": 0.0
        }

    # Regression Metrics
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)

    # R2 Score (Can be negative if prediction is worse than mean baseline)
    r2 = r2_score(y_true, y_pred)

    # Directional Accuracy (Hit rate of sign matching: Both positive or both negative)
    # A prediction is directional hit if sign(y_true) == sign(y_pred)
    same_sign = (y_true * y_pred) >= 0
    directional_acc = np.mean(same_sign) * 100.0

    return {
        "mae": round(float(mae * 100), 2),                # converted to percentage format e.g. 3.45%
        "rmse": round(float(rmse * 100), 2),              # converted to percentage format e.g. 4.12%
        "r2": round(float(r2), 4),                         # e.g. 0.4521
        "directional_accuracy": round(float(directional_acc), 2)  # e.g. 68.5%
    }
