from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

try:
    from .config import (
        DATASET_PATH,
        FATIGUE_SIGNAL_COLUMNS,
        METADATA_COLUMNS,
        MIN_FEATURE_COUNT,
        RANDOM_STATE,
        TEST_SIZE,
    )
except ImportError:
    from config import (  # type: ignore
        DATASET_PATH,
        FATIGUE_SIGNAL_COLUMNS,
        METADATA_COLUMNS,
        MIN_FEATURE_COUNT,
        RANDOM_STATE,
        TEST_SIZE,
    )


DatasetSplit = Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str]]


def _normalize(series: pd.Series, reverse: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    lo = values.quantile(0.02)
    hi = values.quantile(0.98)
    scaled = ((values - lo) / max(hi - lo, 1e-9)).clip(0.0, 1.0)
    return 1.0 - scaled if reverse else scaled


def _fatigue_score(df: pd.DataFrame) -> pd.Series:
    signals = {
        "fatigue_proxy": _normalize(df["fatigue_proxy"]),
        "typing_motor_slowdown": _normalize(df["typing_speed_cpm"], reverse=True),
        "typing_latency": _normalize(df["typing_iki_mean_ms"]),
        "typing_variability": _normalize(df["typing_iki_std_ms"]),
        "typing_pause_load": _normalize(df["typing_long_pause_rate"]),
        "typing_acceleration_drop": _normalize(df["typing_acceleration"], reverse=True),
        "focus_idle": _normalize(df["focus_idle_ratio"]),
        "return_latency": _normalize(df["focus_return_latency_mean_s"]),
        "instability": _normalize(df["behavioral_instability_index"]),
        "quiz_latency": _normalize(df["quiz_time_to_answer_mean_s"]),
    }
    score = (
        0.24 * signals["fatigue_proxy"]
        + 0.13 * signals["typing_motor_slowdown"]
        + 0.11 * signals["typing_latency"]
        + 0.10 * signals["typing_variability"]
        + 0.09 * signals["typing_pause_load"]
        + 0.09 * signals["typing_acceleration_drop"]
        + 0.08 * signals["focus_idle"]
        + 0.06 * signals["return_latency"]
        + 0.06 * signals["instability"]
        + 0.04 * signals["quiz_latency"]
    )
    return score.clip(0.0, 1.0)


def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    excluded = set(METADATA_COLUMNS)
    candidates = df.drop(columns=[col for col in excluded if col in df.columns])
    numeric_features = candidates.select_dtypes(include=["number"]).copy()

    if numeric_features.shape[1] < MIN_FEATURE_COUNT:
        raise ValueError(
            f"Expected at least {MIN_FEATURE_COUNT} numeric features, "
            f"found {numeric_features.shape[1]}"
        )

    numeric_features = numeric_features.replace([np.inf, -np.inf], pd.NA)
    return numeric_features.fillna(numeric_features.median(numeric_only=True)).fillna(0.0)


def load_dataset() -> DatasetSplit:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    missing = [name for name in FATIGUE_SIGNAL_COLUMNS if name not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing fatigue signal columns: {missing}")

    fatigue_score = _fatigue_score(df)
    rng = np.random.default_rng(RANDOM_STATE)
    noisy_score = (fatigue_score + rng.normal(0.0, 0.075, size=len(fatigue_score))).clip(0.0, 1.0)
    y = (noisy_score >= noisy_score.quantile(0.62)).astype(int)
    X = _feature_frame(df)
    feature_names = list(X.columns)

    return train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        shuffle=True,
        stratify=y,
    ) + [feature_names]  # type: ignore[operator]
