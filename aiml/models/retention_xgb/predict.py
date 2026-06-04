from __future__ import annotations

from typing import Any, Dict

try:
    from .config import FEATURE_COLUMNS
    from .model import RetentionXGB
except ImportError:
    from config import FEATURE_COLUMNS  # type: ignore
    from model import RetentionXGB      # type: ignore


def predict_retention(feature_dict: Dict[str, Any]) -> Dict[str, Any]:
    missing = [c for c in FEATURE_COLUMNS if c not in feature_dict]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    feature_vector = [feature_dict[c] for c in FEATURE_COLUMNS]

    model = RetentionXGB.load()
    score = model.predict_single(feature_vector)

    if score < 0.3:
        level = "low"
        will_remember = True
        message = "Strong retention likely. Student understood the concept well."
    elif score < 0.5:
        level = "medium"
        will_remember = True
        message = "Moderate retention. Consider a revision prompt in 2-3 days."
    else:
        level = "high"
        will_remember = False
        message = "High forgetting risk. Recommend immediate review or re-attempt."

    return {
        "retention_risk_score": round(score, 4),
        "retention_risk_level": level,
        "will_likely_remember": will_remember,
        "message": message,
    }


if __name__ == "__main__":
    dummy = {col: 0.5 for col in FEATURE_COLUMNS}
    dummy["age"] = 20
    result = predict_retention(dummy)
    import json
    print(json.dumps(result, indent=2))
