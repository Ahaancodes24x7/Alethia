from __future__ import annotations

import json

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from .config import MODEL_PATH, FEATURE_COLUMNS
except ImportError:
    from config import MODEL_PATH, FEATURE_COLUMNS  # type: ignore

ARTIFACTS_DIR = MODEL_PATH.parent


def evaluate_model(
    model,
    X_test,
    y_test,
    training_time_seconds: float = 0.0,
    save_artifacts: bool = True,
) -> dict:
    """
    Evaluate the retention model and save 3 artifact files:
      metrics.json
      feature_importance.json
      feature_columns.json
    """

    y_pred = model.predict(X_test)
    y_true = np.array(y_test)

    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)

    def bucket(v):
        if v < 0.3:   return "low"
        elif v < 0.5: return "medium"
        else:          return "high"

    bucket_correct  = sum(bucket(p) == bucket(t) for p, t in zip(y_pred, y_true))
    bucket_accuracy = bucket_correct / len(y_true)

    pred_distribution = {
        "min":  float(y_pred.min()),
        "max":  float(y_pred.max()),
        "mean": float(y_pred.mean()),
        "std":  float(y_pred.std()),
    }

    print("\n" + "=" * 55)
    print("  RETENTION XGB — EVALUATION RESULTS")
    print("=" * 55)
    print(f"  MAE             : {mae:.4f}")
    print(f"  RMSE            : {rmse:.4f}")
    print(f"  R²              : {r2:.4f}")
    print(f"  Bucket Accuracy : {bucket_accuracy:.2%}")
    print(f"  ({bucket_correct}/{len(y_true)} correct LOW/MEDIUM/HIGH calls)")
    print("=" * 55)
    print(f"\n  Prediction range : [{pred_distribution['min']:.4f}, {pred_distribution['max']:.4f}]")
    print(f"  Prediction mean  : {pred_distribution['mean']:.4f}")
    print(f"  Prediction std   : {pred_distribution['std']:.4f}\n")

    metrics = {
        "mae":                     round(mae,  10),
        "rmse":                    round(rmse, 10),
        "r2":                      round(r2,   10),
        "bucket_accuracy":         round(bucket_accuracy, 10),
        "prediction_distribution": pred_distribution,
        "training_time_seconds":   round(training_time_seconds, 4),
        "dataset_size":            20000,
        "train_size":              int(len(y_true) * 4),
        "test_size":               int(len(y_true)),
        "feature_count":           len(FEATURE_COLUMNS),
    }

    if save_artifacts:
        _save_metrics(metrics)
        _save_feature_importance(model)
        _save_feature_columns()

    return metrics


def _save_metrics(metrics: dict) -> None:
    path = ARTIFACTS_DIR / "metrics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Saved -> {path}")


def _save_feature_importance(model) -> None:
    try:
        importances = model.feature_importances(FEATURE_COLUMNS)
        importance_dict = {name: float(score) for name, score in importances}

        path = ARTIFACTS_DIR / "feature_importance.json"
        with open(path, "w") as f:
            json.dump(importance_dict, f, indent=2)
        print(f"  Saved -> {path}")

        print("\n  Top 10 Features Driving Retention Risk:")
        top10 = importances[:10]
        max_score = top10[0][1]
        for rank, (name, score) in enumerate(top10, 1):
            bar = "█" * int(score / max_score * 20)
            print(f"  {rank:2}. {name:<45} {bar} ({score:.4f})")

    except Exception as e:
        print(f"  Warning: Could not save feature importance: {e}")


def _save_feature_columns() -> None:
    path = ARTIFACTS_DIR / "feature_columns.json"
    with open(path, "w") as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)
    print(f"  Saved -> {path}")