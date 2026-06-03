from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

try:
    from .config import FATIGUE_THRESHOLD, METRICS_PATH
except ImportError:
    from config import FATIGUE_THRESHOLD, METRICS_PATH  # type: ignore


def classification_metrics(y_true, probabilities, threshold: float = FATIGUE_THRESHOLD) -> Dict[str, Any]:
    actual = np.asarray(y_true, dtype=int)
    predicted_probabilities = np.asarray(probabilities, dtype=float)
    predicted = (predicted_probabilities >= threshold).astype(int)

    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1_score": float(f1_score(actual, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(actual, predicted_probabilities)),
        "confusion_matrix": confusion_matrix(actual, predicted).tolist(),
        "prediction_distribution": {
            "min": float(np.min(predicted_probabilities)),
            "max": float(np.max(predicted_probabilities)),
            "mean": float(np.mean(predicted_probabilities)),
            "std": float(np.std(predicted_probabilities)),
        },
    }


def save_metrics(metrics: Dict[str, Any], path: Path | str = METRICS_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> Dict[str, Any]:
    try:
        from .dataset import load_dataset
        from .model import FatigueXGB
        from .config import MODEL_PATH
    except ImportError:
        from dataset import load_dataset  # type: ignore
        from model import FatigueXGB  # type: ignore
        from config import MODEL_PATH  # type: ignore

    _, X_test, _, y_test, feature_names = load_dataset()
    model = FatigueXGB.load(MODEL_PATH)
    probabilities = model.predict_probability(X_test)
    metrics = classification_metrics(y_test, probabilities)
    metrics.update(
        {
            "dataset_size": int(len(y_test) / 0.20),
            "test_size": int(len(y_test)),
            "feature_count": int(len(feature_names)),
        }
    )

    print("XGBoost fatigue model evaluation")
    print(f"Dataset size: {metrics['dataset_size']}")
    print(f"Features used: {metrics['feature_count']}")
    print(
        "Metrics: "
        f"Accuracy={metrics['accuracy']:.5f}, "
        f"Precision={metrics['precision']:.5f}, "
        f"Recall={metrics['recall']:.5f}, "
        f"F1={metrics['f1_score']:.5f}, "
        f"ROC-AUC={metrics['roc_auc']:.5f}"
    )
    print(f"Confusion matrix: {metrics['confusion_matrix']}")
    return metrics


if __name__ == "__main__":
    main()
