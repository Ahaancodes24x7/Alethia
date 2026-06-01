from __future__ import annotations

from typing import Any, Mapping, Union

from aiml.features import FeatureResult
from aiml.inference.rule_engine import RuleEngine, RuleEngineOutput
from aiml.inference.rule_engine.feature_adapter import adapt_features_for_rule_engine


FeatureInput = Union[FeatureResult, Mapping[str, Any]]


def evaluate_rule_engine(feature_input: FeatureInput, engine: RuleEngine | None = None) -> RuleEngineOutput:
    features = feature_input.features if isinstance(feature_input, FeatureResult) else feature_input
    adapted_features = adapt_features_for_rule_engine(features)
    return (engine or RuleEngine()).evaluate(adapted_features)
