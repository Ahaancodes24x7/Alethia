from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from sklearn.metrics import (
    explained_variance_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

try:
    from .config import METRICS_PATH
except ImportError:
    from config import METRICS_PATH  # type: ignore


def regression_metrics(y_true, y_pred) -> Dict[str, Any]:
    actual = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)

    if actual.size != predicted.size:
        raise ValueError("y_true and y_pred must have the same length")

    pearson = 0.0
    if actual.size > 1 and np.std(actual) > 0 and np.std(predicted) > 0:
        pearson = float(np.corrcoef(actual, predicted)[0, 1])

    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2_score": float(r2_score(actual, predicted)),
        "explained_variance": float(explained_variance_score(actual, predicted)),
        "pearson_correlation": pearson,
        "prediction_distribution": {
            "min": float(np.min(predicted)),
            "max": float(np.max(predicted)),
            "mean": float(np.mean(predicted)),
            "std": float(np.std(predicted)),
        },
    }


def save_metrics(metrics: Dict[str, Any], path: Path | str = METRICS_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> Dict[str, Any]:
    if not METRICS_PATH.exists():
        raise FileNotFoundError(f"Metrics artifact not found: {METRICS_PATH}")

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    print("LightGBM comprehension model evaluation")
    print(f"Dataset size: {metrics.get('dataset_size')}")
    print(f"Features used: {metrics.get('feature_count')}")
    print(
        "Metrics: "
        f"MAE={metrics['mae']:.5f}, "
        f"RMSE={metrics['rmse']:.5f}, "
        f"R2={metrics['r2_score']:.5f}, "
        f"Pearson={metrics['pearson_correlation']:.5f}"
    )
    return metrics


if __name__ == "__main__":
    main()
