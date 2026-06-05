from __future__ import annotations

from typing import List, Tuple

import numpy as np
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
except ImportError:
    from .config import (  # type: ignore
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
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataset")

    y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce")
    if y.isna().any():
        raise ValueError(f"Target column '{TARGET_COLUMN}' contains non-numeric values")
    unique_labels = set(y.astype(int).unique())
    if not unique_labels.issubset({0, 1}):
        raise ValueError(f"Target column '{TARGET_COLUMN}' must contain only 0/1 labels")

    X = _feature_frame(df)
    feature_names = list(X.columns)

    return train_test_split(
        X,
        y.astype(int),
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        shuffle=True,
        stratify=y,
    ) + [feature_names]  # type: ignore[operator]
