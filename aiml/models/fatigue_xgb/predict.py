from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

import pandas as pd

try:
    from .config import FATIGUE_THRESHOLD, FEATURE_COLUMNS_PATH, FEATURE_FILL_VALUE, MODEL_PATH
    from .model import FatigueXGB
except ImportError:
    from config import FATIGUE_THRESHOLD, FEATURE_COLUMNS_PATH, FEATURE_FILL_VALUE, MODEL_PATH  # type: ignore
    from model import FatigueXGB  # type: ignore


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


def _fatigue_state(probability: float) -> str:
    if probability >= FATIGUE_THRESHOLD:
        return "fatigued"
    if probability >= 0.35:
        return "moderate"
    return "low"


def predict_fatigue(features: Mapping[str, Any]) -> Dict[str, Any]:
    feature_columns = load_feature_columns()
    model = FatigueXGB.load(MODEL_PATH)
    X = _ordered_feature_frame(features, feature_columns)
    probability = float(model.predict_probability(X)[0])
    confidence = probability if probability >= 0.5 else 1.0 - probability
    return {
        "fatigue_probability": round(probability, 4),
        "fatigue_state": _fatigue_state(probability),
        "confidence": round(confidence, 4),
        "model": "XGBoost",
    }
