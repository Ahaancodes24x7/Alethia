from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from aiml.models.fatigue_xgb.config import (  # noqa: E402
    ARTIFACT_DIR,
    FEATURE_COLUMNS_PATH,
    FEATURE_IMPORTANCE_PATH,
    MODEL_PATH,
)
from aiml.models.fatigue_xgb.dataset import load_dataset  # noqa: E402
from aiml.models.fatigue_xgb.evaluate import classification_metrics, save_metrics  # noqa: E402
from aiml.models.fatigue_xgb.model import FatigueXGB  # noqa: E402


def save_json(payload, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> dict:
    started = time.perf_counter()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    X_train, X_test, y_train, y_test, feature_names = load_dataset()
    model = FatigueXGB().train(X_train, y_train)
    probabilities = model.predict_probability(X_test)

    metrics = classification_metrics(y_test, probabilities)
    metrics.update(
        {
            "training_time_seconds": round(time.perf_counter() - started, 4),
            "dataset_size": int(len(X_train) + len(X_test)),
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
            "feature_count": int(len(feature_names)),
        }
    )

    model.save(MODEL_PATH)
    save_json(feature_names, FEATURE_COLUMNS_PATH)
    save_metrics(metrics)
    save_json(model.feature_importance(feature_names), FEATURE_IMPORTANCE_PATH)

    print("XGBoost fatigue model trained")
    print(f"Dataset size: {metrics['dataset_size']}")
    print(f"Features used: {metrics['feature_count']}")
    print(f"Training time: {metrics['training_time_seconds']}s")
    print(
        "Metrics: "
        f"Accuracy={metrics['accuracy']:.5f}, "
        f"Precision={metrics['precision']:.5f}, "
        f"Recall={metrics['recall']:.5f}, "
        f"F1={metrics['f1_score']:.5f}, "
        f"ROC-AUC={metrics['roc_auc']:.5f}"
    )
    print(f"Artifacts saved to: {ARTIFACT_DIR}")
    return metrics


if __name__ == "__main__":
    main()
