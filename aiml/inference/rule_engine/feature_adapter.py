from __future__ import annotations

from typing import Any, Dict, Mapping


ALIAS_MAPPINGS = {
    "video_same_segment_replay_count": "same_segment_replay_count",
    "video_forward_skip_density": "skip_forward_density",
    "typing_iki_std_ms": "iki_std_ms",
    "typing_iki_mean_ms": "iki_mean_ms",
    "typing_correction_burst_rate": "correction_burst_rate",
    "quiz_hint_request_rate": "hint_request_count",
    "quiz_answer_change_rate": "answer_change_count",
    "quiz_first_attempt_accuracy": "first_attempt_correct_rate",
}


def adapt_features_for_rule_engine(features: Mapping[str, Any]) -> Dict[str, Any]:
    adapted = dict(features)
    for source_name, alias_name in ALIAS_MAPPINGS.items():
        if source_name in features and alias_name not in adapted:
            adapted[alias_name] = features[source_name]
    if "tab_blur_count" not in adapted:
        if "focus_loss_count" in features:
            adapted["tab_blur_count"] = features["focus_loss_count"]
        elif "focus_rapid_tab_switch_rate" in features:
            adapted["tab_blur_count"] = features["focus_rapid_tab_switch_rate"]
    return adapted
