from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from aiml.models.comprehension_gbm.config import (  # noqa: E402
    ARTIFACT_DIR,
    FEATURE_COLUMNS_PATH,
    FEATURE_IMPORTANCE_PATH,
    MODEL_PATH,
)
from aiml.models.comprehension_gbm.dataset import load_dataset  # noqa: E402
from aiml.models.comprehension_gbm.evaluate import regression_metrics, save_metrics  # noqa: E402
from aiml.models.comprehension_gbm.model import ComprehensionGBM  # noqa: E402


def save_json(payload, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> dict:
    started = time.perf_counter()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    X_train, X_test, y_train, y_test, feature_names = load_dataset()
    model = ComprehensionGBM().train(X_train, y_train)
    predictions = model.predict(X_test)

    metrics = regression_metrics(y_test, predictions)
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
    feature_importance = model.feature_importance(feature_names)
    save_json(feature_importance, FEATURE_IMPORTANCE_PATH)

    print("LightGBM comprehension model trained")
    print(f"Dataset size: {metrics['dataset_size']}")
    print(f"Feature count: {metrics['feature_count']}")
    print(f"Training time: {metrics['training_time_seconds']}s")
    print(
        "Metrics: "
        f"MAE={metrics['mae']:.5f}, "
        f"RMSE={metrics['rmse']:.5f}, "
        f"R2={metrics['r2_score']:.5f}, "
        f"Pearson={metrics['pearson_correlation']:.5f}"
    )
    print(f"Artifacts saved to: {ARTIFACT_DIR}")
    return metrics


if __name__ == "__main__":
    main()
