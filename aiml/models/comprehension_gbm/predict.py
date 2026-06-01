from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

import pandas as pd

try:
    from .config import FEATURE_COLUMNS_PATH, FEATURE_FILL_VALUE, MODEL_PATH
    from .model import ComprehensionGBM
except ImportError:
    from config import FEATURE_COLUMNS_PATH, FEATURE_FILL_VALUE, MODEL_PATH  # type: ignore
    from model import ComprehensionGBM  # type: ignore


def load_feature_columns(path: Path | str = FEATURE_COLUMNS_PATH) -> list[str]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Feature columns artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _ordered_feature_frame(
    features: Mapping[str, Any],
    feature_columns: list[str],
) -> pd.DataFrame:
    row: Dict[str, float] = {}
    for name in feature_columns:
        value = features.get(name, FEATURE_FILL_VALUE)
        row[name] = pd.to_numeric(pd.Series([value]), errors="coerce").fillna(FEATURE_FILL_VALUE).iloc[0]
    return pd.DataFrame([row], columns=feature_columns)


def predict_comprehension(features: Mapping[str, Any]) -> Dict[str, Any]:
    feature_columns = load_feature_columns()
    model = ComprehensionGBM.load(MODEL_PATH)
    X = _ordered_feature_frame(features, feature_columns)
    prediction = float(model.predict(X)[0])
    return {
        "comprehension_confidence": round(prediction, 4),
        "model": "LightGBM",
    }
