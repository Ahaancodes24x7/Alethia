from __future__ import annotations

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[2]

DATASET_PATH = REPO_ROOT / "aiml" / "data" / "synthetic_comprehension_dataset.csv"
TARGET_COLUMN = "fatigue_label"

TEST_SIZE = 0.20
RANDOM_STATE = 42
MIN_FEATURE_COUNT = 10
FEATURE_FILL_VALUE = 0.0
FATIGUE_THRESHOLD = 0.55

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
    "comprehension_confidence",
    TARGET_COLUMN,
}

FATIGUE_SIGNAL_COLUMNS = [
    "fatigue_proxy",
    "typing_acceleration",
    "typing_speed_cpm",
    "typing_iki_mean_ms",
    "typing_iki_std_ms",
    "typing_long_pause_rate",
    "typing_rhythm_entropy",
    "focus_idle_ratio",
    "focus_loss_ratio",
    "focus_return_latency_mean_s",
    "behavioral_instability_index",
    "quiz_time_to_answer_mean_s",
    "quiz_time_to_answer_cv",
]

MODEL_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "n_estimators": 320,
    "max_depth": 4,
    "learning_rate": 0.045,
    "subsample": 0.86,
    "colsample_bytree": 0.86,
    "min_child_weight": 3,
    "reg_alpha": 0.08,
    "reg_lambda": 0.7,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}

ARTIFACT_DIR = PACKAGE_DIR / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "fatigue_xgb.pkl"
FEATURE_COLUMNS_PATH = ARTIFACT_DIR / "feature_columns.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
FEATURE_IMPORTANCE_PATH = ARTIFACT_DIR / "feature_importance.json"
