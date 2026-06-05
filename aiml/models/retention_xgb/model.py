from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import joblib
import numpy as np

try:
    from xgboost import XGBRegressor
except ImportError as exc:
    raise ImportError(
    ) from exc

try:
    from .config import MODEL_PARAMS, MODEL_PATH, EARLY_STOPPING_ROUNDS
except ImportError:
    from config import MODEL_PARAMS, MODEL_PATH, EARLY_STOPPING_ROUNDS  # type: ignore


class RetentionXGB:
    def __init__(self, params: Optional[dict] = None) -> None:
        self.params = dict(MODEL_PARAMS)
        if params:
            self.params.update(params)
        self.model = XGBRegressor(**self.params)

    def train(
        self,
        X_train,
        y_train,
        X_val=None,
        y_val=None,
    ) -> "RetentionXGB":
        fit_params: dict = {}

        if X_val is not None and y_val is not None:
            fit_params["eval_set"] = [(X_val, y_val)]
            fit_params["verbose"] = 100

            self.model.set_params(early_stopping_rounds=EARLY_STOPPING_ROUNDS)

        self.model.fit(X_train, y_train, **fit_params)
        return self

    def predict(self, X) -> np.ndarray:
        """Predict retention risk scores clipped to [0, 1]."""
        raw = self.model.predict(X)
        return np.clip(raw, 0.0, 1.0)

    def predict_single(self, feature_vector: Iterable[float]) -> float:
        """Predict retention risk for one feature vector."""
        x = np.array(feature_vector).reshape(1, -1)
        return float(self.predict(x)[0])

    def feature_importances(self, feature_names: list[str]) -> list[tuple[str, float]]:
        """Return features sorted by importance (highest first)."""
        importances = self.model.feature_importances_
        pairs = sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True,
        )
        return pairs

    def save(self, path: Optional[Path] = None) -> None:
        save_path = path or MODEL_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, save_path)
        print(f"Model saved to {save_path}")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "RetentionXGB":
        load_path = path or MODEL_PATH
        if not load_path.exists():
            raise FileNotFoundError(
                f"No saved model at {load_path}. Run train.py first."
            )
        instance = cls.__new__(cls)
        instance.params = dict(MODEL_PARAMS)
        instance.model = joblib.load(load_path)
        print(f"Model loaded from {load_path}")
        return instance