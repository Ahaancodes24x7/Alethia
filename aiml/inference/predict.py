from __future__ import annotations

from typing import Any, Mapping, Union

from aiml.features import FeatureResult
from aiml.inference.rule_engine import RuleEngine, RuleEngineOutput
from aiml.inference.rule_engine.feature_adapter import adapt_features_for_rule_engine
from aiml.models.comprehension_gbm.predict import predict_comprehension
from aiml.models.fatigue_xgb.predict import predict_fatigue


FeatureInput = Union[FeatureResult, Mapping[str, Any]]


def evaluate_rule_engine(feature_input: FeatureInput, engine: RuleEngine | None = None) -> RuleEngineOutput:
    features = feature_input.features if isinstance(feature_input, FeatureResult) else feature_input
    adapted_features = adapt_features_for_rule_engine(features)
    return (engine or RuleEngine()).evaluate(adapted_features)


def predict_learning_state(feature_input: FeatureInput) -> dict[str, Any]:
    features = feature_input.features if isinstance(feature_input, FeatureResult) else feature_input
    comprehension = predict_comprehension(features)
    fatigue = predict_fatigue(features)
    return {
        "comprehension_confidence": comprehension["comprehension_confidence"],
        "fatigue_probability": fatigue["fatigue_probability"],
        "fatigue_state": fatigue["fatigue_state"],
        "fatigue_confidence": fatigue["confidence"],
        "models": {
            "comprehension": comprehension["model"],
            "fatigue": fatigue["model"],
        },
    }
