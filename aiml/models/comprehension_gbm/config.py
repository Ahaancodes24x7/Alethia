from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[2]

DATASET_PATH = REPO_ROOT / "aiml" / "data" / "synthetic_comprehension_dataset.csv"
TARGET_COLUMN = "comprehension_confidence"

TEST_SIZE = 0.20
RANDOM_STATE = 42
MIN_FEATURE_COUNT = 10
FEATURE_FILL_VALUE = 0.0

METADATA_COLUMNS = {
    "session_id",
    "user_id",
    "student_id",
    "learner_id",
    "platform",
    "topic",
    "persona",
    "age",
    "timestamp",
    "created_at",
    "updated_at",
}

MODEL_PARAMS = {
    "objective": "regression",
    "metric": "rmse",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.035,
    "n_estimators": 900,
    "max_depth": 7,
    "min_child_samples": 18,
    "subsample": 0.88,
    "subsample_freq": 1,
    "colsample_bytree": 0.88,
    "reg_alpha": 0.08,
    "reg_lambda": 0.35,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "verbosity": -1,
}

ARTIFACT_DIR = PACKAGE_DIR / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "comprehension_lgbm.pkl"
FEATURE_COLUMNS_PATH = ARTIFACT_DIR / "feature_columns.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
FEATURE_IMPORTANCE_PATH = ARTIFACT_DIR / "feature_importance.json"
