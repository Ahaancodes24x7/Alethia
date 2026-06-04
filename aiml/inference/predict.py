from __future__ import annotations

import json
from typing import Any, Mapping, Union

from aiml.features import FeatureResult
from aiml.inference.fusion_engine import fuse_learning_state
from aiml.inference.rule_engine import RuleEngine, RuleEngineOutput
from aiml.inference.rule_engine.feature_adapter import adapt_features_for_rule_engine
from aiml.models.comprehension_gbm.predict import predict_comprehension
from aiml.models.fatigue_xgb.predict import predict_fatigue
from aiml.models.retention_xgb.config import FEATURE_COLUMNS as RETENTION_FEATURE_COLUMNS
from aiml.models.retention_xgb.predict import predict_retention


FeatureInput = Union[FeatureResult, Mapping[str, Any]]


FEATURE_ALIASES = {
    "typing_speed": "typing_speed_cpm",
    "focus_ratio": "focus_active_engagement_ratio",
    "rewind_density": "video_rewind_density",
    "pause_density": "video_pause_density",
    "quiz_accuracy": "quiz_score",
}


def _feature_mapping(feature_input: FeatureInput) -> dict[str, Any]:
    features = feature_input.features if isinstance(feature_input, FeatureResult) else feature_input
    normalized = dict(features)
    for source, target in FEATURE_ALIASES.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]

    if "focus_ratio" in normalized and "focus_loss_ratio" not in normalized:
        try:
            normalized["focus_loss_ratio"] = max(0.0, 1.0 - float(normalized["focus_ratio"]))
        except (TypeError, ValueError):
            pass

    return normalized


def evaluate_rule_engine(feature_input: FeatureInput, engine: RuleEngine | None = None) -> RuleEngineOutput:
    features = _feature_mapping(feature_input)
    adapted_features = adapt_features_for_rule_engine(features)
    return (engine or RuleEngine()).evaluate(adapted_features)


def _retention_features(features: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for name in RETENTION_FEATURE_COLUMNS:
        default = 20 if name == "age" else 0.0
        row[name] = features.get(name, default)
    return row


def predict_learning_state(feature_input: FeatureInput) -> dict[str, Any]:
    features = _feature_mapping(feature_input)
    comprehension = predict_comprehension(features)
    fatigue = predict_fatigue(features)
    retention = predict_retention(_retention_features(features))
    rule_engine = evaluate_rule_engine(features)

    model_outputs = {
        "comprehension_score": comprehension["comprehension_confidence"],
        "comprehension_confidence": comprehension["comprehension_confidence"],
        "fatigue_probability": fatigue["fatigue_probability"],
        "fatigue_state": fatigue["fatigue_state"],
        "fatigue_confidence": fatigue["confidence"],
        "retention_probability": round(1.0 - retention["retention_risk_score"], 4),
        "retention_risk_score": retention["retention_risk_score"],
        "retention_risk": retention["retention_risk_level"],
        "comprehension_model": comprehension["model"],
        "fatigue_model": fatigue["model"],
        "retention_model": "XGBoost",
    }

    return fuse_learning_state(model_outputs, rule_engine)


if __name__ == "__main__":
    sample_features = {name: 0.5 for name in RETENTION_FEATURE_COLUMNS}
    sample_features.update(
        {
            "age": 20,
            "typing_speed_cpm": 220,
            "typing_iki_mean_ms": 260,
            "typing_iki_std_ms": 90,
            "focus_active_engagement_ratio": 0.78,
            "focus_loss_ratio": 0.12,
            "quiz_score": 0.82,
            "quiz_first_attempt_accuracy": 0.76,
            "video_completion_ratio": 0.88,
            "scroll_reading_coverage": 0.84,
        }
    )
    print(json.dumps(predict_learning_state(sample_features), indent=2))
