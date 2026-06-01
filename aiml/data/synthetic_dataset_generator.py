from __future__ import annotations

import csv
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aiml.features.feature_pipeline import FeaturePipeline


ROW_COUNT = 20_000
SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parent
DATASET_PATH = OUTPUT_DIR / "synthetic_comprehension_dataset.csv"

PLATFORMS = ["YouTube", "Coursera", "NPTEL", "LeetCode", "GeeksForGeeks", "College LMS"]
TOPICS = [
    "Data Structures",
    "Algorithms",
    "Operating Systems",
    "DBMS",
    "Computer Networks",
    "Machine Learning",
    "Physics",
    "Mathematics",
]

PERSONAS: Dict[str, Dict[str, float]] = {
    "High Performer": {
        "target_min": 0.80,
        "target_max": 0.98,
        "quiz": 0.90,
        "focus": 0.05,
        "fatigue": 0.18,
        "hint": 0.10,
        "struggle": 0.18,
        "confidence": 0.86,
        "completion": 0.94,
    },
    "Productive Struggler": {
        "target_min": 0.60,
        "target_max": 0.85,
        "quiz": 0.72,
        "focus": 0.12,
        "fatigue": 0.32,
        "hint": 0.45,
        "struggle": 0.62,
        "confidence": 0.68,
        "completion": 0.88,
    },
    "Distracted Learner": {
        "target_min": 0.25,
        "target_max": 0.60,
        "quiz": 0.48,
        "focus": 0.42,
        "fatigue": 0.30,
        "hint": 0.35,
        "struggle": 0.45,
        "confidence": 0.54,
        "completion": 0.52,
    },
    "Fatigued Learner": {
        "target_min": 0.20,
        "target_max": 0.55,
        "quiz": 0.44,
        "focus": 0.24,
        "fatigue": 0.78,
        "hint": 0.40,
        "struggle": 0.55,
        "confidence": 0.48,
        "completion": 0.58,
    },
    "False Confidence Learner": {
        "target_min": 0.20,
        "target_max": 0.50,
        "quiz": 0.36,
        "focus": 0.16,
        "fatigue": 0.28,
        "hint": 0.18,
        "struggle": 0.35,
        "confidence": 0.84,
        "completion": 0.72,
    },
    "Intensive Revision Learner": {
        "target_min": 0.65,
        "target_max": 0.90,
        "quiz": 0.78,
        "focus": 0.14,
        "fatigue": 0.44,
        "hint": 0.30,
        "struggle": 0.76,
        "confidence": 0.74,
        "completion": 0.91,
    },
}

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def sample_unit(rng: random.Random, mean: float, spread: float = 0.10) -> float:
    return clamp(rng.gauss(mean, spread), 0.0, 1.0)


def count_like(rng: random.Random, mean: float, spread: float = 1.0) -> float:
    return float(max(0, round(rng.gauss(mean, spread))))


def get_feature_metadata() -> Dict[str, Any]:
    pipeline = FeaturePipeline()
    metadata: Dict[str, Any] = {}
    for extractor in list(pipeline.extractors.values()) + [pipeline.derived_extractor]:
        metadata.update(extractor.get_feature_metadata())
    return metadata


def generate_feature_row(rng: random.Random, persona: str) -> Dict[str, float]:
    p = PERSONAS[persona]
    quiz = sample_unit(rng, p["quiz"], 0.08)
    focus_loss = sample_unit(rng, p["focus"], 0.08)
    fatigue = sample_unit(rng, p["fatigue"], 0.10)
    hint = sample_unit(rng, p["hint"], 0.12)
    struggle = sample_unit(rng, p["struggle"], 0.12)
    confidence = sample_unit(rng, p["confidence"], 0.08)
    completion = sample_unit(rng, p["completion"], 0.08)
    distraction = focus_loss

    rewind_density = clamp(0.15 + struggle * 2.4 + rng.gauss(0, 0.25), 0, 5)
    replay_count = count_like(rng, struggle * 5.0, 1.0)
    correction_burst = clamp(struggle * 2.1 + fatigue * 0.8 + rng.gauss(0, 0.25), 0, 5)
    answer_change = clamp(struggle * 1.6 + (1 - quiz) * 0.8 + rng.gauss(0, 0.18), 0, 4)
    iki_mean = clamp(150 + fatigue * 700 + rng.gauss(0, 45), 80, 1600)
    iki_std = clamp(40 + fatigue * 430 + struggle * 140 + rng.gauss(0, 35), 0, 1200)
    engagement = clamp(1 - focus_loss - fatigue * 0.18 + rng.gauss(0, 0.04), 0, 1)
    confidence_gap = clamp(confidence - quiz, -1, 1)
    overconfident = 1.0 if confidence_gap > 0.3 else 0.0
    underconfident = 1.0 if confidence_gap < -0.3 else 0.0

    features = {
        "video_pause_density": clamp(0.3 + struggle * 1.4 + fatigue * 0.5 + rng.gauss(0, 0.2), 0, 5),
        "video_rewind_density": rewind_density,
        "video_rewind_distance_mean_s": clamp(5 + struggle * 38 + rng.gauss(0, 5), 0, 120),
        "video_same_segment_replay_count": replay_count,
        "video_forward_skip_density": clamp(0.1 + distraction * 2.0 + (1 - completion) * 1.2 + rng.gauss(0, 0.2), 0, 5),
        "video_forward_skip_distance_mean_s": clamp(4 + distraction * 50 + rng.gauss(0, 8), 0, 180),
        "video_slowdown_ratio": clamp(struggle * 0.55 + rng.gauss(0, 0.07), 0, 1),
        "video_speedup_ratio": clamp((1 - struggle) * 0.18 + distraction * 0.25 + rng.gauss(0, 0.05), 0, 1),
        "video_speed_change_count": count_like(rng, 1 + struggle * 5 + distraction * 2, 1.2),
        "video_completion_ratio": completion,
        "video_effective_watch_ratio": clamp(completion + struggle * 0.35 + rng.gauss(0, 0.08), 0, 1.8),
        "video_segment_coverage": clamp(completion - distraction * 0.18 + rng.gauss(0, 0.05), 0, 1),
        "video_pause_duration_mean_s": clamp(4 + fatigue * 35 + struggle * 18 + rng.gauss(0, 4), 0, 180),
        "scroll_velocity_mean_px_s": clamp(180 + distraction * 700 + rng.gauss(0, 80), 20, 2200),
        "scroll_velocity_std_px_s": clamp(60 + distraction * 900 + struggle * 350 + rng.gauss(0, 80), 0, 3000),
        "scroll_reversal_rate": clamp(struggle * 4.8 + distraction * 1.6 + rng.gauss(0, 0.5), 0, 9),
        "scroll_reversal_depth_mean_px": clamp(60 + struggle * 760 + rng.gauss(0, 90), 0, 2400),
        "scroll_revisit_rate": clamp(struggle * 0.75 + rng.gauss(0, 0.08), 0, 1),
        "scroll_concept_loop_count": count_like(rng, struggle * 5.5, 1.0),
        "scroll_reading_coverage": clamp(completion - distraction * 0.22 + rng.gauss(0, 0.05), 0, 1),
        "scroll_dwell_time_mean_s": clamp(8 + struggle * 18 + fatigue * 20 + rng.gauss(0, 4), 0, 90),
        "scroll_dwell_time_variance_s": clamp(20 + struggle * 420 + fatigue * 240 + rng.gauss(0, 55), 0, 1400),
        "scroll_linear_reading_ratio": clamp(0.92 - struggle * 0.38 - distraction * 0.30 + rng.gauss(0, 0.06), 0, 1),
        "scroll_section_skip_count": count_like(rng, distraction * 6 + (1 - completion) * 3, 1.2),
        "scroll_reading_speed_wpm_estimate": clamp(130 + distraction * 220 - fatigue * 80 + rng.gauss(0, 35), 40, 700),
        "typing_iki_mean_ms": iki_mean,
        "typing_iki_std_ms": iki_std,
        "typing_iki_cv": clamp(iki_std / max(iki_mean, 1), 0, 4),
        "typing_speed_cpm": clamp(260 - fatigue * 135 - struggle * 35 + rng.gauss(0, 35), 30, 520),
        "typing_dwell_time_mean_ms": clamp(70 + fatigue * 180 + rng.gauss(0, 18), 30, 500),
        "typing_dwell_time_std_ms": clamp(12 + fatigue * 95 + rng.gauss(0, 12), 0, 350),
        "typing_flight_time_mean_ms": clamp(45 + fatigue * 230 + rng.gauss(0, 30), 10, 700),
        "typing_flight_time_std_ms": clamp(15 + fatigue * 150 + struggle * 60 + rng.gauss(0, 18), 0, 500),
        "typing_backspace_rate": clamp(0.03 + struggle * 0.28 + fatigue * 0.08 + rng.gauss(0, 0.03), 0, 1),
        "typing_correction_burst_rate": correction_burst,
        "typing_correction_burst_length_mean": clamp(1 + struggle * 5 + fatigue * 2 + rng.gauss(0, 0.7), 0, 12),
        "typing_pause_before_typing_ms": clamp(300 + struggle * 3200 + fatigue * 1400 + rng.gauss(0, 350), 0, 12000),
        "typing_rhythm_entropy": clamp(0.4 + fatigue * 1.4 + struggle * 0.5 + rng.gauss(0, 0.15), 0, 2.302585092994046),
        "typing_long_pause_rate": clamp(fatigue * 0.55 + struggle * 0.15 + rng.gauss(0, 0.06), 0, 1),
        "typing_acceleration": clamp(35 - fatigue * 110 + rng.gauss(0, 30), -250, 180),
        "typing_error_correction_ratio": clamp(0.04 + struggle * 0.55 + fatigue * 0.16 + rng.gauss(0, 0.06), 0, 2),
        "focus_loss_count": count_like(rng, focus_loss * 12, 1.5),
        "focus_loss_total_duration_s": clamp(focus_loss * 60 + rng.gauss(0, 4), 0, 60),
        "focus_loss_ratio": focus_loss,
        "focus_mean_loss_duration_s": clamp(2 + focus_loss * 35 + rng.gauss(0, 3), 0, 60),
        "focus_max_loss_duration_s": clamp(4 + focus_loss * 55 + rng.gauss(0, 5), 0, 60),
        "focus_rapid_tab_switch_rate": clamp(distraction * 8 + rng.gauss(0, 0.8), 0, 15),
        "focus_return_latency_mean_s": clamp(2 + distraction * 30 + fatigue * 10 + rng.gauss(0, 3), 0, 90),
        "focus_return_latency_std_s": clamp(distraction * 40 + fatigue * 12 + rng.gauss(0, 4), 0, 120),
        "focus_idle_ratio": clamp(fatigue * 0.42 + distraction * 0.22 + rng.gauss(0, 0.05), 0, 1),
        "focus_idle_bout_count": count_like(rng, fatigue * 3 + distraction * 2, 0.8),
        "focus_active_engagement_ratio": engagement,
        "focus_context_flag": 1.0,
        "quiz_score": quiz,
        "quiz_first_attempt_accuracy": clamp(quiz - hint * 0.22 - struggle * 0.10 + rng.gauss(0, 0.05), 0, 1),
        "quiz_time_to_answer_mean_s": clamp(9 + struggle * 42 + fatigue * 18 + rng.gauss(0, 6), 1, 180),
        "quiz_time_to_answer_std_s": clamp(2 + struggle * 20 + fatigue * 12 + rng.gauss(0, 3), 0, 90),
        "quiz_time_to_answer_cv": 0.0,
        "quiz_hint_request_rate": clamp(hint * 2.2 + struggle * 0.45 + rng.gauss(0, 0.15), 0, 4),
        "quiz_max_hint_level_used": float(round(clamp(hint * 3.2 + rng.gauss(0, 0.35), 0, 3))),
        "quiz_hint_dependency_ratio": clamp(hint * 0.9 + rng.gauss(0, 0.08), 0, 1),
        "quiz_answer_change_rate": answer_change,
        "quiz_confidence_mean": confidence,
        "quiz_confidence_accuracy_correlation": clamp(0.7 - abs(confidence_gap) * 1.2 + rng.gauss(0, 0.12), -1, 1),
        "quiz_confidence_mismatch": confidence_gap,
        "quiz_overconfidence_flag": overconfident,
        "quiz_underconfidence_flag": underconfident,
        "quiz_time_to_first_action_s": clamp(2 + struggle * 16 + fatigue * 8 + rng.gauss(0, 3), 0, 90),
        "quiz_abandonment_rate": clamp(distraction * 0.35 + (1 - quiz) * 0.18 + rng.gauss(0, 0.04), 0, 1),
        "external_reference_count": count_like(rng, hint * 6, 1.1),
        "external_llm_reference_count": count_like(rng, hint * 2.4, 0.9),
        "external_search_reference_count": count_like(rng, hint * 2.2, 0.9),
        "external_reference_site_count": count_like(rng, hint * 1.8, 0.8),
        "external_time_ratio": clamp(hint * 0.36 + rng.gauss(0, 0.05), 0, 1),
        "external_llm_time_ratio": clamp(hint * 0.16 + rng.gauss(0, 0.03), 0, 1),
        "external_mean_duration_s": clamp(8 + hint * 70 + rng.gauss(0, 10), 0, 240),
        "external_before_answer_rate": clamp(hint * 0.65 + rng.gauss(0, 0.08), 0, 1),
        "external_help_seeking_index": clamp(hint * 0.85 + rng.gauss(0, 0.07), 0, 1),
        "external_borrowed_knowledge_flag": 0.0,
    }
    features["quiz_time_to_answer_cv"] = clamp(
        features["quiz_time_to_answer_std_s"] / max(features["quiz_time_to_answer_mean_s"], 1),
        0,
        5,
    )
    features["external_borrowed_knowledge_flag"] = (
        1.0 if features["external_help_seeking_index"] > 0.5 and quiz > 0.7 else 0.0
    )

    confusion = statistics.fmean([
        clamp(features["video_rewind_density"] / 5, 0, 1),
        clamp(features["video_same_segment_replay_count"] / 3, 0, 1),
        features["video_slowdown_ratio"],
        clamp(features["scroll_reversal_rate"] / 6, 0, 1),
        features["scroll_revisit_rate"],
        clamp(features["scroll_concept_loop_count"] / 3, 0, 1),
        clamp(features["typing_backspace_rate"] / 0.5, 0, 1),
        clamp(features["typing_correction_burst_rate"] / 3, 0, 1),
        clamp(features["quiz_answer_change_rate"] / 3, 0, 1),
        clamp(features["quiz_confidence_mismatch"], 0, 1),
    ])
    struggle_score = statistics.fmean([
        clamp(features["video_rewind_density"] / 5, 0, 1),
        clamp(features["video_same_segment_replay_count"] / 3, 0, 1),
        clamp(features["scroll_reversal_rate"] / 6, 0, 1),
        clamp(features["scroll_concept_loop_count"] / 3, 0, 1),
        clamp(features["typing_correction_burst_rate"] / 3, 0, 1),
        clamp(features["typing_iki_cv"] / 2, 0, 1),
        clamp(features["quiz_answer_change_rate"] / 3, 0, 1),
    ])
    fatigue_proxy = statistics.fmean([
        clamp(features["typing_iki_mean_ms"] / 2000, 0, 1),
        clamp(features["typing_iki_std_ms"] / 2000, 0, 1),
        clamp(features["typing_dwell_time_mean_ms"] / 500, 0, 1),
        features["focus_idle_ratio"],
        features["focus_loss_ratio"],
        1 - engagement,
    ])
    features.update({
        "personal_drift_zscore": clamp((confusion + fatigue_proxy) * 4 + rng.gauss(0, 0.35), 0, 10),
        "confidence_gap": confidence_gap,
        "multi_modal_confusion_score": confusion,
        "productive_struggle_score": struggle_score * clamp((quiz - 0.7) / 0.3, 0, 1),
        "unproductive_struggle_score": struggle_score * max(clamp((0.4 - quiz) / 0.4, 0, 1), clamp(confidence_gap, 0, 1)),
        "engagement_deviation": clamp((engagement - 0.65) * 4 + rng.gauss(0, 0.4), -10, 10),
        "behavioral_instability_index": statistics.fmean([
            clamp(features["typing_iki_cv"] / 2, 0, 1),
            clamp(features["typing_iki_std_ms"] / 2000, 0, 1),
            clamp(features["scroll_velocity_std_px_s"] / 2000, 0, 1),
            clamp(features["scroll_dwell_time_variance_s"] / 900, 0, 1),
            clamp(features["focus_return_latency_std_s"] / 120, 0, 1),
            clamp(features["quiz_time_to_answer_cv"] / 2, 0, 1),
        ]),
        "concept_loop_score": statistics.fmean([
            clamp(features["scroll_concept_loop_count"] / 3, 0, 1),
            features["scroll_revisit_rate"],
            clamp(features["video_same_segment_replay_count"] / 3, 0, 1),
        ]),
        "retention_risk_proxy": statistics.fmean([
            1 - quiz,
            1 - features["quiz_first_attempt_accuracy"],
            features["quiz_hint_dependency_ratio"],
            1 - max(features["video_completion_ratio"], features["scroll_reading_coverage"]),
            fatigue_proxy,
            struggle_score,
        ]),
        "fatigue_proxy": fatigue_proxy,
    })
    return features


def target_from_features(rng: random.Random, features: Dict[str, float], persona: str) -> float:
    p = PERSONAS[persona]
    raw = (
        0.38 * features["quiz_score"]
        + 0.14 * features["quiz_first_attempt_accuracy"]
        + 0.13 * features["focus_active_engagement_ratio"]
        + 0.09 * features["productive_struggle_score"]
        + 0.08 * (1 - features["quiz_hint_dependency_ratio"])
        + 0.07 * (1 - features["fatigue_proxy"])
        + 0.06 * (1 - features["multi_modal_confusion_score"])
        + 0.05 * (1 - max(0.0, features["confidence_gap"]))
    )
    raw += rng.gauss(0, 0.025)
    return round(clamp(raw, p["target_min"], p["target_max"]), 4)


def validate(rows: List[Dict[str, Any]], feature_names: List[str]) -> List[str]:
    errors: List[str] = []
    if len(rows) < 10_000:
        errors.append("row count below minimum")
    for name in feature_names + ["comprehension_confidence"]:
        if any(row.get(name, "") == "" for row in rows):
            errors.append(f"missing values in {name}")
            break
    target_values = [float(row["comprehension_confidence"]) for row in rows]
    if not all(0.0 <= value <= 1.0 for value in target_values):
        errors.append("target outside range")
    return errors


def main() -> None:
    rng = random.Random(SEED)
    metadata = get_feature_metadata()
    feature_names = list(metadata.keys())

    rows: List[Dict[str, Any]] = []
    personas = list(PERSONAS.keys())
    for idx in range(ROW_COUNT):
        persona = personas[idx % len(personas)]
        features = generate_feature_row(rng, persona)
        target = target_from_features(rng, features, persona)
        row: Dict[str, Any] = {
            "session_id": f"session_{idx + 1:05d}",
            "user_id": f"student_{(idx % 2400) + 1:04d}",
            "age": rng.randint(18, 24),
            "platform": rng.choice(PLATFORMS),
            "topic": rng.choice(TOPICS),
            "persona": persona,
        }
        row.update({name: round(float(features[name]), 6) for name in feature_names})
        row["comprehension_confidence"] = target
        rows.append(row)

    with DATASET_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    validation_errors = validate(rows, feature_names)
    print(f"wrote {DATASET_PATH} with {len(rows)} rows and {len(feature_names)} feature columns")
    if validation_errors:
        raise SystemExit("; ".join(validation_errors))


if __name__ == "__main__":
    main()
