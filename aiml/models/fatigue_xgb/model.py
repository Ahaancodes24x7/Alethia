from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import joblib
import numpy as np

try:
    from xgboost import XGBClassifier
except ImportError as exc:
    raise ImportError("XGBoost is required. Install it with `pip install xgboost`.") from exc

try:
    from .config import MODEL_PARAMS, MODEL_PATH
except ImportError:
    from config import MODEL_PARAMS, MODEL_PATH  # type: ignore


class FatigueXGB:
    def __init__(self, params: Optional[dict] = None) -> None:
        self.params = dict(MODEL_PARAMS)
        if params:
            self.params.update(params)
        self.model = XGBClassifier(**self.params)

    def train(self, X_train, y_train) -> "FatigueXGB":
        self.model.fit(X_train, y_train)
        return self

    def predict_probability(self, X) -> np.ndarray:
        probabilities = self.model.predict_proba(X)[:, 1]
        return np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)

    def save(self, path: Path | str = MODEL_PATH) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    @classmethod
    def load(cls, path: Path | str = MODEL_PATH) -> "FatigueXGB":
        instance = cls()
        instance.model = joblib.load(path)
        return instance

    def feature_importance(self, feature_names: Iterable[str]) -> list[dict[str, float | str]]:
        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            raise ValueError("Model has not been trained yet")

        rows = [
            {"feature": name, "importance": float(value)}
            for name, value in zip(feature_names, importances)
        ]
        return sorted(rows, key=lambda item: item["importance"], reverse=True)
