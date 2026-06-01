from __future__ import annotations

from typing import List, Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

try:
    from .config import (
        DATASET_PATH,
        METADATA_COLUMNS,
        MIN_FEATURE_COUNT,
        RANDOM_STATE,
        TARGET_COLUMN,
        TEST_SIZE,
    )
except ImportError:  # Allows `python dataset.py` from this directory.
    from config import (  # type: ignore
        DATASET_PATH,
        METADATA_COLUMNS,
        MIN_FEATURE_COUNT,
        RANDOM_STATE,
        TARGET_COLUMN,
        TEST_SIZE,
    )


DatasetSplit = Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str]]


def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    excluded = set(METADATA_COLUMNS)
    excluded.add(TARGET_COLUMN)

    candidates = df.drop(columns=[col for col in excluded if col in df.columns])
    numeric_features = candidates.select_dtypes(include=["number"]).copy()

    if numeric_features.shape[1] < MIN_FEATURE_COUNT:
        raise ValueError(
            f"Expected at least {MIN_FEATURE_COUNT} numeric features, "
            f"found {numeric_features.shape[1]}"
        )

    numeric_features = numeric_features.replace([float("inf"), float("-inf")], pd.NA)
    return numeric_features.fillna(numeric_features.median(numeric_only=True)).fillna(0.0)


def load_dataset() -> DatasetSplit:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataset")

    y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    if y.isna().any():
        raise ValueError(f"Target column '{TARGET_COLUMN}' contains non-numeric values")

    X = _feature_frame(df)
    feature_names = list(X.columns)

    return train_test_split(
        X,
        y.astype(float),
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        shuffle=True,
    ) + [feature_names]  # type: ignore[operator]
