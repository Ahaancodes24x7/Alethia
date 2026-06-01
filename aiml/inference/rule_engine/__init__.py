from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .feature_adapter import adapt_features_for_rule_engine

EPSILON = 1e-9

# ---------------------------------------------------------------------------
# Output dataclass the strictly typed state object
# ---------------------------------------------------------------------------

@dataclass
class RuleEngineOutput:
    drift_score: float                          # 0-100
    cognitive_risk_level: str                   # LOW/MODERATE/HIGH/CRITICAL
    confusion_flags: List[str]                  # e.g. ["VIDEO_LOOPING"]
    attention_risk: float                       # 0-100
    fatigue_risk: float                         # 0-100
    intervention: Dict[str, Any]                # action + target + urgency + message
    explanation_trace: List[str]                # ordered human-readable reasons

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_score": self.drift_score,
            "cognitive_risk_level": self.cognitive_risk_level,
            "confusion_flags": self.confusion_flags,
            "attention_risk": self.attention_risk,
            "fatigue_risk": self.fatigue_risk,
            "intervention": self.intervention,
            "explanation_trace": self.explanation_trace,
        }


# ---------------------------------------------------------------------------
# Thresholds — tune these based on your data distribution
# ---------------------------------------------------------------------------

DRIFT_THRESHOLDS = {
    "LOW":      (0,  25),
    "MODERATE": (26, 45),
    "HIGH":     (46, 72),
    "CRITICAL": (73, 100),
}

# Confusion flag rules: (flag_name, check_function, explanation_template)
CONFUSION_FLAG_RULES = [
    (
        "VIDEO_LOOPING",
        lambda f: f.get("video_rewind_density", 0) > 0.35
                  and f.get("same_segment_replay_count", 0) >= 3,
        lambda f: f"Video rewind density {f.get('video_rewind_density',0):.2f} with "
                  f"{int(f.get('same_segment_replay_count',0))} segment replays — looping detected.",
    ),
    (
        "PANIC_GUESSING",
        lambda f: f.get("quiz_score", 1.0) < 0.40
                  and f.get("hint_request_count", 0) >= 3,
        lambda f: f"Quiz score {f.get('quiz_score',1.0):.0%} with "
                  f"{int(f.get('hint_request_count',0))} hints — panic guessing pattern.",
    ),
    (
        "ATTENTION_DROPOUT",
        lambda f: f.get("focus_loss_ratio", 0) > 0.25
                  or f.get("tab_blur_count", 0) >= 5,
        lambda f: f"Focus loss ratio {f.get('focus_loss_ratio',0):.0%}, "
                  f"tab switches {int(f.get('tab_blur_count',0))} — attention dropout.",
    ),
    (
        "ANSWER_THRASHING",
        lambda f: f.get("correction_burst_rate", 0) > 0.35,
        lambda f: f"Correction burst rate {f.get('correction_burst_rate',0):.2f} — "
                  f"heavy answer rewriting detected.",
    ),
    (
        "COGNITIVE_FATIGUE",
        lambda f: f.get("time_on_task_min", 0) > 50
                  and f.get("iki_mean_ms", 0) > 350,
        lambda f: f"Time on task {f.get('time_on_task_min',0):.0f}min with "
                  f"IKI mean {f.get('iki_mean_ms',0):.0f}ms — cognitive fatigue.",
    ),
]

# Intervention decision table: (condition, action, urgency, message_template)
INTERVENTION_RULES = [
    (
        lambda f, d: d >= 73 or "PANIC_GUESSING" in _get_flags(f),
        "CHECKPOINT_QUIZ",
        "immediate",
        "Comprehension has collapsed. Take a checkpoint quiz before continuing.",
    ),
    (
        lambda f, d: "VIDEO_LOOPING" in _get_flags(f),
        "REVISIT_SEGMENT",
        "immediate",
        "You keep rewinding the same segment. Revisit it with focus before moving on.",
    ),
    (
        lambda f, d: "COGNITIVE_FATIGUE" in _get_flags(f),
        "TAKE_BREAK",
        "high",
        "You have been studying for a long time. Take a 10-minute break.",
    ),
    (
        lambda f, d: "ATTENTION_DROPOUT" in _get_flags(f),
        "FOCUS_PROMPT",
        "moderate",
        "Your attention has drifted. Close other tabs and refocus.",
    ),
    (
        lambda f, d: 46 <= d <= 72,
        "HINT_OFFER",
        "moderate",
        "You seem to be struggling. Would you like a hint or concept recap?",
    ),
    (
        lambda f, d: 26 <= d <= 45,
        "ENCOURAGE",
        "low",
        "Mild drift detected. Keep going — you're on track.",
    ),
    (
        lambda f, d: d <= 25,
        "NONE",
        "none",
        "Comprehension looks strong. Keep it up.",
    ),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_flags(features: Dict[str, float]) -> List[str]:
    """Evaluate all confusion flag rules against a feature dict."""
    return [
        flag
        for flag, condition, _ in CONFUSION_FLAG_RULES
        if condition(features)
    ]


def _normalize(value: float, lo: float, hi: float) -> float:
    """Clamp value to [0,1] relative to [lo, hi]."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo + EPSILON)))


# ---------------------------------------------------------------------------
# Core scoring functions
# ---------------------------------------------------------------------------

def _score_video(f: Dict) -> float:
    rewind = min(1.0, f.get("video_rewind_density", 0))
    replay = min(1.0, f.get("same_segment_replay_count", 0) / 10.0)
    pause = min(1.0, f.get("video_pause_density", 0))
    skip = min(1.0, f.get("skip_forward_density", 0))
    return rewind * 0.45 + replay * 0.30 + pause * 0.15 + skip * 0.10


def _score_scroll(f: Dict) -> float:
    reversal = min(1.0, f.get("scroll_reversal_rate", 0))
    return reversal


def _score_typing(f: Dict) -> float:
    iki_std = f.get("iki_std_ms", 0)
    correction = min(1.0, f.get("correction_burst_rate", 0))
    typing_instability = min(1.0, iki_std / 250.0)
    return typing_instability * 0.6 + correction * 0.4


def _score_cursor(f: Dict) -> float:
    return min(1.0, f.get("cursor_entropy", 0))


def _score_quiz_hint(f: Dict) -> float:
    quiz = f.get("quiz_score", 1.0)
    hint = min(1.0, f.get("hint_request_count", 0) / 8.0)
    answer_changes = min(1.0, f.get("answer_change_count", 0) / 8.0)
    first_attempt = f.get("first_attempt_correct_rate", 1.0)
    return (1.0 - quiz) * 0.40 + hint * 0.25 + answer_changes * 0.15 + (1.0 - first_attempt) * 0.20


def _score_fatigue(f: Dict) -> float:
    time_raw = min(1.0, f.get("time_on_task_min", 0) / 90.0)
    iki_mean = f.get("iki_mean_ms", 100)
    iki_raw = min(1.0, max(0.0, (iki_mean - 100) / 600.0))
    return time_raw * 0.6 + iki_raw * 0.4


# ---------------------------------------------------------------------------
# Main Rule Engine class
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Stateless rule-based drift scorer.
    Call .evaluate(features) for every 60-second window.
    """

    def evaluate(self, features: Dict[str, Any]) -> RuleEngineOutput:
        trace: List[str] = []

        # 1. Compute sub-scores (each 0-1)
        video_s   = _score_video(features)
        scroll_s  = _score_scroll(features)
        typing_s  = _score_typing(features)
        cursor_s  = _score_cursor(features)
        quiz_s    = _score_quiz_hint(features)
        fatigue_s = _score_fatigue(features)

        # 2. Weighted drift score (PDF formula, Section 11)
        raw_drift = (
            0.20 * cursor_s
            + 0.20 * scroll_s
            + 0.20 * typing_s
            + 0.15 * video_s
            + 0.15 * quiz_s
            + 0.10 * fatigue_s
        ) * 100

        drift_score = round(min(100.0, max(0.0, raw_drift)), 2)

        # 3. Build explanation trace
        sub_scores = {
            "Cursor entropy":     (cursor_s,  0.20),
            "Scroll reversal":    (scroll_s,  0.20),
            "Typing instability": (typing_s,  0.20),
            "Video rewind":       (video_s,   0.15),
            "Quiz/hint behavior": (quiz_s,    0.15),
            "Fatigue index":      (fatigue_s, 0.10),
        }

        for name, (score, weight) in sub_scores.items():
            pct = score * 100
            contribution = score * weight * 100
            level = "high" if pct > 65 else "moderate" if pct > 35 else "low"
            trace.append(
                f"{name}: {pct:.1f}/100 ({level}) — contributes {contribution:.1f} pts to drift."
            )

        # 4. Risk level
        risk_level = "CRITICAL"
        for level, (lo, hi) in DRIFT_THRESHOLDS.items():
            if lo <= drift_score <= hi:
                risk_level = level
                break

        trace.append(f"Final drift score: {drift_score:.1f} → Risk level: {risk_level}.")

        # 5. Confusion flags
        confusion_flags: List[str] = []
        for flag, condition, explain in CONFUSION_FLAG_RULES:
            if condition(features):
                confusion_flags.append(flag)
                trace.append(explain(features))

        if not confusion_flags:
            trace.append("No confusion flags triggered.")

        # 6. Attention risk (0-100)
        focus_loss = features.get("focus_loss_ratio", 0)
        tab_blur   = features.get("tab_blur_count", 0)
        attention_risk = round(min(100.0, max(0.0, focus_loss * 80 + tab_blur * 4)), 2)

        if attention_risk > 60:
            trace.append(f"High attention risk ({attention_risk:.0f}/100) — focus breakdown detected.")
        elif attention_risk > 30:
            trace.append(f"Moderate attention risk ({attention_risk:.0f}/100).")

        # 7. Fatigue risk (0-100)
        time_on_task = features.get("time_on_task_min", 0)
        iki_mean     = features.get("iki_mean_ms", 100)
        fatigue_risk = round(
            min(100.0, max(0.0,
                (time_on_task / 90.0) * 60
                + (max(0, iki_mean - 100) / 600.0) * 40
            )), 2
        )

        if fatigue_risk > 60:
            trace.append(f"High fatigue risk ({fatigue_risk:.0f}/100) — motor decay detected.")

        # 8. Intervention (first matching rule wins)
        intervention = {
            "action": "NONE",
            "urgency": "none",
            "message": "No intervention needed.",
            "target": None,
        }
        for condition, action, urgency, message in INTERVENTION_RULES:
            if condition(features, drift_score):
                intervention = {
                    "action": action,
                    "urgency": urgency,
                    "message": message,
                    "target": features.get("current_concept_id", "current_concept"),
                }
                trace.append(f"Intervention triggered: {action} (urgency={urgency}).")
                break

        return RuleEngineOutput(
            drift_score=drift_score,
            cognitive_risk_level=risk_level,
            confusion_flags=confusion_flags,
            attention_risk=attention_risk,
            fatigue_risk=fatigue_risk,
            intervention=intervention,
            explanation_trace=trace,
        )


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = RuleEngine()

    test_window = {
        "video_rewind_density": 0.62,
        "same_segment_replay_count": 5,
        "video_pause_density": 0.45,
        "skip_forward_density": 0.10,
        "scroll_reversal_rate": 0.48,
        "cursor_entropy": 0.71,
        "iki_mean_ms": 410,
        "iki_std_ms": 130,
        "correction_burst_rate": 0.41,
        "focus_loss_ratio": 0.32,
        "tab_blur_count": 7,
        "hint_request_count": 4,
        "quiz_score": 0.28,
        "time_on_task_min": 58,
        "answer_change_count": 5,
        "first_attempt_correct_rate": 0.20,
        "concept_difficulty": 0.75,
        "performance_deviation": -0.42,
        "current_concept_id": "uncertainty_principle",
    }

    result = engine.evaluate(test_window)
    import json
    print(json.dumps(result.to_dict(), indent=2))
