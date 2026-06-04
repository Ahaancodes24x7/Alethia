from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

try:
    from .config import FEATURE_COLUMNS, TARGET_COLUMN
except ImportError:
    from config import FEATURE_COLUMNS, TARGET_COLUMN


def load_dataset(
    csv_path: str | Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    df = pd.read_csv(csv_path)

    missing_features = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns in dataset: {missing_features}")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Target column '{TARGET_COLUMN}' not found in dataset.")

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    valid_mask = X.notna().all(axis=1) & y.notna()
    X = X[valid_mask].reset_index(drop=True)
    y = y[valid_mask].reset_index(drop=True)

    print(f"Dataset loaded: {len(X)} rows, {len(FEATURE_COLUMNS)} features.")
    print(f"Target '{TARGET_COLUMN}' — mean: {y.mean():.4f}, std: {y.std():.4f}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")
    return X_train, X_test, y_train, y_test