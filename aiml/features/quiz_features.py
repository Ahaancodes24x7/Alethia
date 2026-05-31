

from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Tuple

from .base import (
    EPSILON,
    FeatureExtractor,
    FeatureMetadata,
    FeatureResult,
    TelemetryEvent,
    TelemetryWindow,
)


def _safe_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# Constants

_CONFIDENCE_SCALE_MAX: float = 5.0

_OVERCONFIDENCE_THRESHOLD: float = 0.3

_UNDERCONFIDENCE_THRESHOLD: float = -0.3


_MIN_MEANINGFUL_ATTEMPT_S: float = 2.0

def _build_metadata_registry() -> Dict[str, FeatureMetadata]:
    return {
        "quiz_score": FeatureMetadata(
            name="quiz_score",
            display_name="Quiz Score",
            modality="quiz",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_mastery",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of questions answered correctly.",
        ),
        "quiz_first_attempt_accuracy": FeatureMetadata(
            name="quiz_first_attempt_accuracy",
            display_name="First-Attempt Accuracy",
            modality="quiz",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_mastery",
            requires_baseline=False,
            unit="ratio",
            description="Proportion correct on first try without hints.",
        ),
        "quiz_time_to_answer_mean_s": FeatureMetadata(
            name="quiz_time_to_answer_mean_s",
            display_name="Mean Time to Answer",
            modality="quiz",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="seconds",
            description="Mean response latency per question.",
        ),
        "quiz_time_to_answer_std_s": FeatureMetadata(
            name="quiz_time_to_answer_std_s",
            display_name="Time-to-Answer Variability",
            modality="quiz",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Standard deviation of response latencies.",
        ),
        "quiz_time_to_answer_cv": FeatureMetadata(
            name="quiz_time_to_answer_cv",
            display_name="Time-to-Answer CV",
            modality="quiz",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="ratio",
            description="Coefficient of variation of response times.",
        ),
        "quiz_hint_request_rate": FeatureMetadata(
            name="quiz_hint_request_rate",
            display_name="Hint Request Rate",
            modality="quiz",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="more_help_seeking",
            requires_baseline=True,
            unit="per_question",
            description="Hints requested divided by number of questions.",
        ),
        "quiz_max_hint_level_used": FeatureMetadata(
            name="quiz_max_hint_level_used",
            display_name="Max Hint Level Used",
            modality="quiz",
            tier=2,
            range_min=0.0,
            range_max=3.0,
            higher_means="more_help_seeking",
            requires_baseline=False,
            unit="level",
            description="Deepest hint level accessed (0=none, 3=solution).",
        ),
        "quiz_hint_dependency_ratio": FeatureMetadata(
            name="quiz_hint_dependency_ratio",
            display_name="Hint Dependency Ratio",
            modality="quiz",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_help_seeking",
            requires_baseline=False,
            unit="ratio",
            description="Correct answers that used hints divided by all correct.",
        ),
        "quiz_answer_change_rate": FeatureMetadata(
            name="quiz_answer_change_rate",
            display_name="Answer Change Rate",
            modality="quiz",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="per_question",
            description="Answer revisions divided by number of questions.",
        ),
        "quiz_confidence_mean": FeatureMetadata(
            name="quiz_confidence_mean",
            display_name="Mean Confidence",
            modality="quiz",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="ratio",
            description="Mean self-reported confidence, normalized to 0-1.",
        ),
        "quiz_confidence_accuracy_correlation": FeatureMetadata(
            name="quiz_confidence_accuracy_correlation",
            display_name="Confidence-Accuracy Correlation",
            modality="quiz",
            tier=2,
            range_min=-1.0,
            range_max=1.0,
            higher_means="more_mastery",
            requires_baseline=False,
            unit="correlation",
            description="Spearman correlation between confidence and correctness.",
        ),
        "quiz_confidence_mismatch": FeatureMetadata(
            name="quiz_confidence_mismatch",
            display_name="Confidence Mismatch",
            modality="quiz",
            tier=1,
            range_min=-1.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="signed_ratio",
            description="Confidence minus score. Positive = overconfident.",
        ),
        "quiz_overconfidence_flag": FeatureMetadata(
            name="quiz_overconfidence_flag",
            display_name="Overconfidence Flag",
            modality="quiz",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="binary",
            description="1 if confidence_mismatch > 0.3 (Dunning-Kruger).",
        ),
        "quiz_underconfidence_flag": FeatureMetadata(
            name="quiz_underconfidence_flag",
            display_name="Underconfidence Flag",
            modality="quiz",
            tier=3,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="binary",
            description="1 if confidence_mismatch < -0.3 (impostor pattern).",
        ),
        "quiz_time_to_first_action_s": FeatureMetadata(
            name="quiz_time_to_first_action_s",
            display_name="Time to First Action",
            modality="quiz",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="seconds",
            description="Mean time from question display to first interaction.",
        ),
        "quiz_abandonment_rate": FeatureMetadata(
            name="quiz_abandonment_rate",
            display_name="Abandonment Rate",
            modality="quiz",
            tier=3,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of questions submitted without meaningful attempt.",
        ),
    }
# Helpers

def _spearman_rank_correlation(
    x_values: List[float],
    y_values: List[float],
) -> float:
    n = len(x_values)
    if n != len(y_values) or n < 2:
        return 0.0

    def rank(values: List[float]) -> List[float]:
        """Compute average ranks, handling ties."""
        indexed = sorted(enumerate(values), key=lambda p: p[1])
        ranks: List[float] = [0.0] * len(values)
        i = 0
        while i < len(indexed):
            j = i
            while (
                j + 1 < len(indexed)
                and indexed[j + 1][1] == indexed[i][1]
            ):
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    x_ranks = rank(x_values)
    y_ranks = rank(y_values)

    mean_x = statistics.fmean(x_ranks)
    mean_y = statistics.fmean(y_ranks)

    numerator = sum(
        (xr - mean_x) * (yr - mean_y)
        for xr, yr in zip(x_ranks, y_ranks)
    )
    denom_x = math.sqrt(sum((xr - mean_x) ** 2 for xr in x_ranks))
    denom_y = math.sqrt(sum((yr - mean_y) ** 2 for yr in y_ranks))

    denominator = denom_x * denom_y
    if denominator < EPSILON:
        return 0.0
    correlation = numerator / denominator
    return max(-1.0, min(1.0, correlation))
#EXTRACTOR

class QuizFeatureExtractor(FeatureExtractor):

    _MODALITY: str = "quiz"
    _METADATA_REGISTRY: Dict[str, FeatureMetadata] = _build_metadata_registry()
    _MIN_EVENTS: int = 4

    def get_modality(self) -> str:
        """Return the modality identifier."""
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        
        return dict(self._METADATA_REGISTRY)

    def get_required_event_types(self) -> List[str]:
        return [
            "quiz_start",
            "question_display",
            "answer_change",
            "hint_request",
            "answer_submit",
            "confidence_rating",
            "quiz_end",
        ]

    def get_minimum_events(self) -> int:
        
        return self._MIN_EVENTS

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        if self._MODALITY not in window.modality_coverage:
            return self._build_empty_result(
                window, "No quiz events present in window.",
            )

        question_display_events = sorted(
            window.events_by_type.get("question_display", []),
            key=lambda e: e.timestamp,
        )
        submit_events = sorted(
            window.events_by_type.get("answer_submit", []),
            key=lambda e: e.timestamp,
        )
        hint_events = sorted(
            window.events_by_type.get("hint_request", []),
            key=lambda e: e.timestamp,
        )
        change_events = sorted(
            window.events_by_type.get("answer_change", []),
            key=lambda e: e.timestamp,
        )
        confidence_events = sorted(
            window.events_by_type.get("confidence_rating", []),
            key=lambda e: e.timestamp,
        )

        if not submit_events:
            return self._build_empty_result(
                window, "Quiz modality flagged but no answer_submit events.",
            )

        warnings: List[str] = []
        raw_features: Dict[str, float] = {}

        raw_features.update(
            self._compute_accuracy_metrics(submit_events, hint_events)
        )
        raw_features.update(
            self._compute_timing_metrics(
                question_display_events, submit_events,
            )
        )
        raw_features.update(
            self._compute_hint_metrics(hint_events, submit_events)
        )
        raw_features.update(
            self._compute_answer_change_metrics(
                change_events, len(submit_events),
            )
        )
        raw_features.update(
            self._compute_confidence_metrics(
                confidence_events, submit_events,
            )
        )
        raw_features.update(
            self._compute_first_action_and_abandonment(
                question_display_events,
                change_events,
                hint_events,
                submit_events,
            )
        )

        total_quiz_events = (
            len(question_display_events) + len(submit_events)
            + len(hint_events) + len(change_events) + len(confidence_events)
        )

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=total_quiz_events,
            warnings=warnings,
        )

    def _compute_accuracy_metrics(
        self,
        submit_events: List[TelemetryEvent],
        hint_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        total = len(submit_events)
        if total == 0:
            return {
                "quiz_score": 0.0,
                "quiz_first_attempt_accuracy": 0.0,
            }

        # Build set of question_ids that had hints requested before submission.
        questions_with_hints: set = set()
        for hint in hint_events:
            qid = hint.payload.get("question_id")
            if qid is not None:
                questions_with_hints.add(qid)

        correct_count = 0
        first_attempt_correct_count = 0

        # Use only the final submission per question for scoring.
        final_submissions: Dict[str, TelemetryEvent] = {}
        for submit in submit_events:
            qid = submit.payload.get("question_id", str(id(submit)))
            final_submissions[qid] = submit

        for qid, submit in final_submissions.items():
            is_correct = bool(submit.payload.get("is_correct", False))
            attempt_number = _safe_int(
                submit.payload.get("attempt_number"), 1,
            )
            if is_correct:
                correct_count += 1
                used_hint = qid in questions_with_hints
                if attempt_number == 1 and not used_hint:
                    first_attempt_correct_count += 1

        num_questions = len(final_submissions)
        score = correct_count / num_questions if num_questions > 0 else 0.0
        first_attempt = (
            first_attempt_correct_count / num_questions
            if num_questions > 0 else 0.0
        )

        return {
            "quiz_score": score,
            "quiz_first_attempt_accuracy": first_attempt,
        }

    # Timing metrics

    def _compute_timing_metrics(
        self,
        question_display_events: List[TelemetryEvent],
        submit_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        # Map question_id to display timestamp.
        display_timestamps: Dict[str, float] = {}
        for event in question_display_events:
            qid = event.payload.get("question_id")
            if qid is not None and qid not in display_timestamps:
                display_timestamps[qid] = event.timestamp

        # Map question_id to first submission timestamp.
        first_submit_timestamps: Dict[str, float] = {}
        for event in submit_events:
            qid = event.payload.get("question_id")
            if qid is not None and qid not in first_submit_timestamps:
                first_submit_timestamps[qid] = event.timestamp

        latencies: List[float] = []
        for qid, display_ts in display_timestamps.items():
            if qid in first_submit_timestamps:
                latency = first_submit_timestamps[qid] - display_ts
                if latency >= 0:
                    latencies.append(latency)

        if not latencies:
            return {
                "quiz_time_to_answer_mean_s": 0.0,
                "quiz_time_to_answer_std_s": 0.0,
                "quiz_time_to_answer_cv": 0.0,
            }

        mean_latency = statistics.fmean(latencies)
        std_latency = (
            statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        )
        cv = std_latency / mean_latency if mean_latency > EPSILON else 0.0

        return {
            "quiz_time_to_answer_mean_s": mean_latency,
            "quiz_time_to_answer_std_s": std_latency,
            "quiz_time_to_answer_cv": cv,
        }
    # Hint metrics
    

    def _compute_hint_metrics(
        self,
        hint_events: List[TelemetryEvent],
        submit_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        # Final submission per question.
        final_submissions: Dict[str, TelemetryEvent] = {}
        for submit in submit_events:
            qid = submit.payload.get("question_id", str(id(submit)))
            final_submissions[qid] = submit

        num_questions = len(final_submissions)
        if num_questions == 0:
            return {
                "quiz_hint_request_rate": 0.0,
                "quiz_max_hint_level_used": 0.0,
                "quiz_hint_dependency_ratio": 0.0,
            }

        hint_request_rate = len(hint_events) / num_questions

        max_hint_level = 0
        questions_with_hints: set = set()
        for hint in hint_events:
            level = _safe_int(hint.payload.get("hint_level"), 0)
            if level > max_hint_level:
                max_hint_level = level
            qid = hint.payload.get("question_id")
            if qid is not None:
                questions_with_hints.add(qid)
        # Clamp to valid range [0, 3].
        max_hint_level = max(0, min(3, max_hint_level))

        correct_with_hints = 0
        total_correct = 0
        for qid, submit in final_submissions.items():
            if bool(submit.payload.get("is_correct", False)):
                total_correct += 1
                if qid in questions_with_hints:
                    correct_with_hints += 1

        dependency_ratio = (
            correct_with_hints / total_correct if total_correct > 0 else 0.0
        )

        return {
            "quiz_hint_request_rate": hint_request_rate,
            "quiz_max_hint_level_used": float(max_hint_level),
            "quiz_hint_dependency_ratio": dependency_ratio,
        }

    
    # Answer change metrics

    def _compute_answer_change_metrics(
        self,
        change_events: List[TelemetryEvent],
        num_questions: int,
    ) -> Dict[str, float]:
        
        rate = len(change_events) / num_questions if num_questions > 0 else 0.0
        return {"quiz_answer_change_rate": rate}
    # Confidence metrics

    def _compute_confidence_metrics(
        self,
        confidence_events: List[TelemetryEvent],
        submit_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        # Last confidence rating per question.
        confidence_by_question: Dict[str, float] = {}
        for event in confidence_events:
            qid = event.payload.get("question_id")
            rating = _safe_float(event.payload.get("rating"), 0.0)
            if qid is None or rating <= 0.0:
                continue
            confidence_by_question[qid] = (
                max(1.0, min(_CONFIDENCE_SCALE_MAX, rating))
            )

        # Final submission per question.
        final_submissions: Dict[str, TelemetryEvent] = {}
        for submit in submit_events:
            qid = submit.payload.get("question_id", str(id(submit)))
            final_submissions[qid] = submit

        # Normalize confidence to [0, 1].
        normalized_confidences = [
            (rating - 1.0) / (_CONFIDENCE_SCALE_MAX - 1.0)
            for rating in confidence_by_question.values()
        ]

        confidence_mean = (
            statistics.fmean(normalized_confidences)
            if normalized_confidences else 0.5
        )

        # Per-question pairs for correlation.
        paired_confidences: List[float] = []
        paired_correctness: List[float] = []
        for qid, conf in confidence_by_question.items():
            if qid in final_submissions:
                normalized = (conf - 1.0) / (_CONFIDENCE_SCALE_MAX - 1.0)
                is_correct = bool(
                    final_submissions[qid].payload.get("is_correct", False)
                )
                paired_confidences.append(normalized)
                paired_correctness.append(1.0 if is_correct else 0.0)

        if len(paired_confidences) >= 2:
            calibration_correlation = _spearman_rank_correlation(
                paired_confidences, paired_correctness,
            )
        else:
            calibration_correlation = 0.0

        # Quiz score for mismatch.
        correct_count = sum(
            1 for s in final_submissions.values()
            if bool(s.payload.get("is_correct", False))
        )
        quiz_score = (
            correct_count / len(final_submissions)
            if final_submissions else 0.0
        )

        confidence_mismatch = confidence_mean - quiz_score
        # Clamp to declared range.
        confidence_mismatch = max(-1.0, min(1.0, confidence_mismatch))

        overconfident = (
            1.0 if confidence_mismatch > _OVERCONFIDENCE_THRESHOLD else 0.0
        )
        underconfident = (
            1.0 if confidence_mismatch < _UNDERCONFIDENCE_THRESHOLD else 0.0
        )

        return {
            "quiz_confidence_mean": confidence_mean,
            "quiz_confidence_accuracy_correlation": calibration_correlation,
            "quiz_confidence_mismatch": confidence_mismatch,
            "quiz_overconfidence_flag": overconfident,
            "quiz_underconfidence_flag": underconfident,
        }
    # First action and abandonment

    def _compute_first_action_and_abandonment(
        self,
        question_display_events: List[TelemetryEvent],
        change_events: List[TelemetryEvent],
        hint_events: List[TelemetryEvent],
        submit_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        # Display timestamp per question.
        display_timestamps: Dict[str, float] = {}
        for event in question_display_events:
            qid = event.payload.get("question_id")
            if qid is not None and qid not in display_timestamps:
                display_timestamps[qid] = event.timestamp

        # First action timestamp per question.
        action_events: List[Tuple[Optional[str], float]] = []
        for event in change_events + hint_events + submit_events:
            qid = event.payload.get("question_id")
            action_events.append((qid, event.timestamp))

        first_action_by_question: Dict[str, float] = {}
        for qid, ts in action_events:
            if qid is None or qid not in display_timestamps:
                continue
            if ts < display_timestamps[qid]:
                continue
            if qid not in first_action_by_question:
                first_action_by_question[qid] = ts
            else:
                first_action_by_question[qid] = min(
                    first_action_by_question[qid], ts,
                )

        latencies: List[float] = []
        for qid, action_ts in first_action_by_question.items():
            latencies.append(action_ts - display_timestamps[qid])

        mean_first_action = (
            statistics.fmean(latencies) if latencies else 0.0
        )

        # Abandonment: response time below threshold.
        first_submit_by_question: Dict[str, float] = {}
        for event in submit_events:
            qid = event.payload.get("question_id")
            if qid is not None and qid not in first_submit_by_question:
                first_submit_by_question[qid] = event.timestamp

        total_questions = len(display_timestamps)
        abandoned_count = 0
        for qid, submit_ts in first_submit_by_question.items():
            if qid in display_timestamps:
                response_time = submit_ts - display_timestamps[qid]
                if response_time < _MIN_MEANINGFUL_ATTEMPT_S:
                    abandoned_count += 1

        abandonment_rate = (
            abandoned_count / total_questions if total_questions > 0 else 0.0
        )

        return {
            "quiz_time_to_first_action_s": mean_first_action,
            "quiz_abandonment_rate": abandonment_rate,
        }
