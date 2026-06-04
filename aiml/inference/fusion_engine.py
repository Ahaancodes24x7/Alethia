from __future__ import annotations

from typing import Any, Mapping


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _percent(value: float) -> int:
    return int(round(_clamp(value) * 100))


def _title_state(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _rule_dict(rule_engine: Any) -> dict[str, Any]:
    if hasattr(rule_engine, "to_dict"):
        return rule_engine.to_dict()
    if isinstance(rule_engine, Mapping):
        return dict(rule_engine)
    return {}


def _retention_strength(inputs: Mapping[str, Any]) -> float:
    if "retention_probability" in inputs:
        return _clamp(float(inputs["retention_probability"]))
    if "retention_strength" in inputs:
        return _clamp(float(inputs["retention_strength"]))
    if "retention_risk_score" in inputs:
        return _clamp(1.0 - float(inputs["retention_risk_score"]))
    return 0.5


def _learning_state(
    comprehension: float,
    fatigue_probability: float,
    retention_strength: float,
    rule_risk: str,
) -> str:
    cognitive_energy = 1.0 - fatigue_probability

    if rule_risk == "CRITICAL" or (comprehension < 0.45 and fatigue_probability >= 0.65):
        return "Cognitive Overload"
    if comprehension >= 0.78 and cognitive_energy >= 0.70 and retention_strength >= 0.70:
        return "Optimal Learning"
    if comprehension >= 0.68 and fatigue_probability >= 0.55:
        return "Productive Struggle"
    if comprehension < 0.55 and cognitive_energy >= 0.58:
        return "Needs Strategy Change"
    if retention_strength < 0.45 and comprehension >= 0.60:
        return "Review Needed"
    if cognitive_energy < 0.45:
        return "Recovery Recommended"
    if comprehension >= 0.62 and retention_strength >= 0.55:
        return "Productive Learning"
    return "Unstable Learning"


def _risks(
    comprehension: float,
    fatigue_probability: float,
    retention_strength: float,
    rule_engine: Mapping[str, Any],
) -> list[str]:
    risks: list[str] = []
    if comprehension < 0.55:
        risks.append("low comprehension confidence")
    if fatigue_probability >= 0.65:
        risks.append("high cognitive fatigue")
    elif fatigue_probability >= 0.40:
        risks.append("moderate cognitive fatigue")
    if retention_strength < 0.45:
        risks.append("high retention decay")
    elif retention_strength < 0.70:
        risks.append("moderate retention decay")

    rule_risk = str(rule_engine.get("cognitive_risk_level", "")).upper()
    if rule_risk in {"HIGH", "CRITICAL"}:
        risks.append(f"{rule_risk.lower()} rule-engine cognitive risk")

    for flag in rule_engine.get("confusion_flags", [])[:3]:
        risks.append(_title_state(str(flag)))

    return risks


def _recommendations(
    learning_state: str,
    comprehension: float,
    fatigue_probability: float,
    retention_strength: float,
    rule_engine: Mapping[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    intervention = rule_engine.get("intervention", {})
    if isinstance(intervention, Mapping):
        message = intervention.get("message")
        action = intervention.get("action")
        if message and action != "NONE":
            recommendations.append(str(message))

    if retention_strength < 0.70:
        recommendations.append("Review this topic tomorrow")
    if fatigue_probability >= 0.65:
        recommendations.append("Take a short break before continuing")
    elif fatigue_probability >= 0.40:
        recommendations.append("Use a lighter revision task next")
    if comprehension < 0.55:
        recommendations.append("Try a worked example before the next quiz")
    if learning_state in {"Optimal Learning", "Productive Learning"}:
        recommendations.append("Continue current learning pattern")

    deduped: list[str] = []
    for item in recommendations:
        if item not in deduped:
            deduped.append(item)
    return deduped[:4]


def fuse_learning_state(
    model_outputs: Mapping[str, Any],
    rule_engine: Any,
) -> dict[str, Any]:
    rule_data = _rule_dict(rule_engine)
    comprehension = _clamp(float(model_outputs.get("comprehension_score", 0.0)))
    fatigue_probability = _clamp(float(model_outputs.get("fatigue_probability", 0.0)))
    retention_strength = _retention_strength(model_outputs)
    cognitive_energy = 1.0 - fatigue_probability
    focus_quality = _clamp(1.0 - float(rule_data.get("attention_risk", 0.0)) / 100.0)

    overall_score = _percent(
        0.45 * comprehension
        + 0.35 * retention_strength
        + 0.20 * cognitive_energy
    )
    rule_risk = str(rule_data.get("cognitive_risk_level", "LOW")).upper()
    learning_state = _learning_state(
        comprehension,
        fatigue_probability,
        retention_strength,
        rule_risk,
    )
    confidence = _clamp(
        0.40 * float(model_outputs.get("comprehension_confidence", comprehension))
        + 0.25 * float(model_outputs.get("fatigue_confidence", 1.0 - abs(0.5 - fatigue_probability)))
        + 0.20 * (1.0 - abs(0.5 - retention_strength))
        + 0.15 * (1.0 - min(float(rule_data.get("drift_score", 0.0)) / 100.0, 1.0))
    )

    return {
        "overall_learning_score": overall_score,
        "learning_state": learning_state,
        "confidence": round(confidence, 4),
        "cognitive_metrics": {
            "comprehension": _percent(comprehension),
            "focus_quality": _percent(focus_quality),
            "cognitive_energy": _percent(cognitive_energy),
            "retention_strength": _percent(retention_strength),
        },
        "risks": _risks(comprehension, fatigue_probability, retention_strength, rule_data),
        "recommendations": _recommendations(
            learning_state,
            comprehension,
            fatigue_probability,
            retention_strength,
            rule_data,
        ),
        "rule_engine": rule_data,
        "model_outputs": {
            "comprehension_model": model_outputs.get("comprehension_model", "LightGBM"),
            "fatigue_model": model_outputs.get("fatigue_model", "XGBoost"),
            "retention_model": model_outputs.get("retention_model", "XGBoost"),
            "comprehension_score": round(comprehension, 4),
            "fatigue_probability": round(fatigue_probability, 4),
            "fatigue_state": model_outputs.get("fatigue_state"),
            "retention_probability": round(retention_strength, 4),
            "retention_risk": model_outputs.get("retention_risk"),
            "retention_risk_score": model_outputs.get("retention_risk_score"),
        },
    }
