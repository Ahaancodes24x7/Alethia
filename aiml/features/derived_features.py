
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .base import (
    EPSILON,
    FeatureMetadata,
    FeatureResult,
    validate_feature_value,
)
# Constants

STRUGGLE_ZSCORE_THRESHOLD: float = 2.0
STRUGGLE_THEN_SUCCESS_SCORE_THRESHOLD: float = 0.7
STRUGGLE_THEN_FAILURE_SCORE_THRESHOLD: float = 0.4

STRUGGLE_FEATURES: tuple[str, ...] = (
    "video_rewind_density",
    "video_same_segment_replay_count",
    "scroll_reversal_rate",
    "scroll_concept_loop_count",
    "typing_correction_burst_rate",
    "typing_iki_cv",
    "quiz_answer_change_rate",
)

CONFUSION_FEATURES: tuple[str, ...] = (
    "video_rewind_density",
    "video_same_segment_replay_count",
    "video_slowdown_ratio",
    "scroll_reversal_rate",
    "scroll_revisit_rate",
    "scroll_concept_loop_count",
    "typing_backspace_rate",
    "typing_correction_burst_rate",
    "quiz_answer_change_rate",
    "quiz_confidence_mismatch",
)

INSTABILITY_FEATURES: tuple[str, ...] = (
    "typing_iki_cv",
    "typing_iki_std_ms",
    "scroll_velocity_std_px_s",
    "scroll_dwell_time_variance_s",
    "focus_return_latency_std_s",
    "quiz_time_to_answer_cv",
)

FATIGUE_FEATURES: tuple[str, ...] = (
    "typing_iki_mean_ms",
    "typing_iki_std_ms",
    "typing_dwell_time_mean_ms",
    "focus_idle_ratio",
    "focus_loss_ratio",
)
# User Baseline

@dataclass
class UserBaseline:

    user_id: str
    session_count: int = 0
    feature_means: Dict[str, float] = field(default_factory=dict)
    feature_stds: Dict[str, float] = field(default_factory=dict)
    quiz_score_mean: float = 0.0
    quiz_score_std: float = 0.0
    engagement_history: List[float] = field(default_factory=list)
    confidence_mismatch_history: List[float] = field(default_factory=list)
    last_concept_engagement: Dict[str, float] = field(default_factory=dict)

    def has_baseline_for(self, feature_name: str) -> bool:
        
        return (
            feature_name in self.feature_means
            and feature_name in self.feature_stds
        )

    def zscore(self, feature_name: str, value: float) -> float:
        if not self.has_baseline_for(feature_name):
            return 0.0
        mean = self.feature_means[feature_name]
        std = max(self.feature_stds[feature_name], EPSILON)
        return (value - mean) / std
# Session Context

@dataclass
class SessionContext:

    session_id: str
    user_id: str
    concept_ids: List[str] = field(default_factory=list)
    session_start_time: float = 0.0
    session_duration_s: float = 0.0
    micro_window_results: List[FeatureResult] = field(default_factory=list)
# Helpers

def _sigmoid(value: float) -> float:
    if value >= 50.0:
        return 1.0
    if value <= -50.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _bounded_ratio(value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return max(0.0, min(1.0, value / scale))
# Derived Feature Extractor

class DerivedFeatureExtractor:

    _MODALITY: str = "derived"
    def get_modality(self) -> str:
        return self._MODALITY

    @property
    def modality(self) -> str:
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        return {
            "personal_drift_zscore": FeatureMetadata(
                name="personal_drift_zscore",
                display_name="Personal Drift Z-Score",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=10.0,
                higher_means="ambiguous",
                requires_baseline=True,
                unit="zscore",
                description="Mean absolute drift from the user's baseline.",
            ),
            "confidence_gap": FeatureMetadata(
                name="confidence_gap",
                display_name="Confidence Gap",
                modality="derived",
                tier=1,
                range_min=-1.0,
                range_max=1.0,
                higher_means="more_confusion",
                requires_baseline=False,
                unit="signed_ratio",
                description="Self-reported confidence minus quiz score.",
            ),
            "multi_modal_confusion_score": FeatureMetadata(
                name="multi_modal_confusion_score",
                display_name="Multi-Modal Confusion Score",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_confusion",
                requires_baseline=False,
                unit="ratio",
                description="Composite confusion signal across available modalities.",
            ),
            "productive_struggle_score": FeatureMetadata(
                name="productive_struggle_score",
                display_name="Productive Struggle Score",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_mastery",
                requires_baseline=False,
                unit="ratio",
                description="High struggle paired with successful quiz outcomes.",
            ),
            "unproductive_struggle_score": FeatureMetadata(
                name="unproductive_struggle_score",
                display_name="Unproductive Struggle Score",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_confusion",
                requires_baseline=False,
                unit="ratio",
                description="High struggle paired with weak quiz outcomes.",
            ),
            "engagement_deviation": FeatureMetadata(
                name="engagement_deviation",
                display_name="Engagement Deviation",
                modality="derived",
                tier=2,
                range_min=-10.0,
                range_max=10.0,
                higher_means="more_engagement",
                requires_baseline=True,
                unit="zscore",
                description="Current active engagement relative to history.",
            ),
            "behavioral_instability_index": FeatureMetadata(
                name="behavioral_instability_index",
                display_name="Behavioral Instability Index",
                modality="derived",
                tier=2,
                range_min=0.0,
                range_max=1.0,
                higher_means="ambiguous",
                requires_baseline=False,
                unit="ratio",
                description="Composite of within-window behavioral variability.",
            ),
            "concept_loop_score": FeatureMetadata(
                name="concept_loop_score",
                display_name="Concept Loop Score",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_confusion",
                requires_baseline=False,
                unit="ratio",
                description="Repeated returns to previously visited concepts or segments.",
            ),
            "retention_risk_proxy": FeatureMetadata(
                name="retention_risk_proxy",
                display_name="Retention Risk Proxy",
                modality="derived",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_confusion",
                requires_baseline=False,
                unit="ratio",
                description="Proxy risk from low mastery, high dependency, and fatigue.",
            ),
            "fatigue_proxy": FeatureMetadata(
                name="fatigue_proxy",
                display_name="Fatigue Proxy",
                modality="derived",
                tier=2,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_fatigue",
                requires_baseline=False,
                unit="ratio",
                description="Composite fatigue signal from typing and focus features.",
            ),
        }

    def extract(
        self,
        modality_results: Dict[str, FeatureResult],
        baseline: Optional[UserBaseline] = None,
        context: Optional[SessionContext] = None,
        window_id: Optional[str] = None,
    ) -> FeatureResult:
        features = self._flatten_features(modality_results)
        source_quality = self._flatten_quality(modality_results)
        warnings: List[str] = []

        if not modality_results:
            warnings.append("No modality results supplied for derived features.")
        if baseline is None:
            warnings.append("No user baseline supplied; baseline features use neutral defaults.")

        struggle_score = self._compute_struggle_score(features, baseline)
        raw_features: Dict[str, float] = {
            "personal_drift_zscore": self._compute_personal_drift_zscore(
                features, baseline, warnings,
            ),
            "confidence_gap": self._compute_confidence_gap(features),
            "multi_modal_confusion_score": self._compute_confusion_score(
                features, baseline,
            ),
            "productive_struggle_score": self._compute_productive_struggle_score(
                struggle_score, features,
            ),
            "unproductive_struggle_score": self._compute_unproductive_struggle_score(
                struggle_score, features,
            ),
            "engagement_deviation": self._compute_engagement_deviation(
                features, baseline,
            ),
            "behavioral_instability_index": self._compute_instability_index(
                features, context,
            ),
            "concept_loop_score": self._compute_concept_loop_score(features),
            "retention_risk_proxy": self._compute_retention_risk_proxy(
                features, struggle_score,
            ),
            "fatigue_proxy": self._compute_fatigue_proxy(features, baseline),
        }

        metadata = self.get_feature_metadata()
        validated_features: Dict[str, float] = {}
        validated_metadata: Dict[str, FeatureMetadata] = {}
        quality: Dict[str, float] = {}
        missing: List[str] = []

        for feature_name, feature_metadata in metadata.items():
            if feature_name not in raw_features:
                missing.append(feature_name)
                continue
            value, value_warnings = validate_feature_value(
                float(raw_features[feature_name]), feature_metadata,
            )
            validated_features[feature_name] = value
            validated_metadata[feature_name] = feature_metadata
            quality[feature_name] = self._compute_quality(
                feature_name, source_quality, baseline,
            )
            warnings.extend(value_warnings)

        output_window_id = (
            window_id
            or self._first_window_id(modality_results)
            or (context.session_id if context is not None else "")
        )

        return FeatureResult(
            features=validated_features,
            metadata=validated_metadata,
            quality=quality,
            missing=missing,
            modality=self.get_modality(),
            window_id=output_window_id,
            event_count=sum(result.event_count for result in modality_results.values()),
            warnings=warnings,
        )
    # Feature computations

    def _compute_personal_drift_zscore(
        self,
        features: Dict[str, float],
        baseline: Optional[UserBaseline],
        warnings: List[str],
    ) -> float:
        if baseline is None:
            return 0.0
        zscores = [
            abs(baseline.zscore(name, value))
            for name, value in features.items()
            if baseline.has_baseline_for(name)
        ]
        if not zscores:
            warnings.append("No overlapping baseline features for personal drift.")
            return 0.0
        return _mean(zscores)

    def _compute_confidence_gap(self, features: Dict[str, float]) -> float:
        if "quiz_confidence_mismatch" in features:
            return features["quiz_confidence_mismatch"]
        return features.get("quiz_confidence_mean", 0.5) - features.get(
            "quiz_score", 0.5,
        )

    def _compute_confusion_score(
        self,
        features: Dict[str, float],
        baseline: Optional[UserBaseline],
    ) -> float:
        signals: List[float] = []
        for name in CONFUSION_FEATURES:
            if name not in features:
                continue
            value = features[name]
            if baseline is not None and baseline.has_baseline_for(name):
                signals.append(_sigmoid(baseline.zscore(name, value)))
            else:
                signals.append(self._normalize_feature(name, value))
        return _mean(signals)

    def _compute_struggle_score(
        self,
        features: Dict[str, float],
        baseline: Optional[UserBaseline],
    ) -> float:
        signals: List[float] = []
        for name in STRUGGLE_FEATURES:
            if name not in features:
                continue
            value = features[name]
            if baseline is not None and baseline.has_baseline_for(name):
                zscore = baseline.zscore(name, value)
                signals.append(_sigmoid(zscore - STRUGGLE_ZSCORE_THRESHOLD))
            else:
                signals.append(self._normalize_feature(name, value))
        return _mean(signals)

    def _compute_productive_struggle_score(
        self,
        struggle_score: float,
        features: Dict[str, float],
    ) -> float:
        quiz_score = features.get("quiz_score", 0.0)
        if quiz_score < STRUGGLE_THEN_SUCCESS_SCORE_THRESHOLD:
            return 0.0
        success_strength = _bounded_ratio(
            quiz_score - STRUGGLE_THEN_SUCCESS_SCORE_THRESHOLD,
            1.0 - STRUGGLE_THEN_SUCCESS_SCORE_THRESHOLD,
        )
        return struggle_score * success_strength

    def _compute_unproductive_struggle_score(
        self,
        struggle_score: float,
        features: Dict[str, float],
    ) -> float:
        quiz_score = features.get("quiz_score", 0.5)
        failure_strength = _bounded_ratio(
            STRUGGLE_THEN_FAILURE_SCORE_THRESHOLD - quiz_score,
            STRUGGLE_THEN_FAILURE_SCORE_THRESHOLD,
        )
        confidence_penalty = max(0.0, self._compute_confidence_gap(features))
        return min(1.0, struggle_score * max(failure_strength, confidence_penalty))

    def _compute_engagement_deviation(
        self,
        features: Dict[str, float],
        baseline: Optional[UserBaseline],
    ) -> float:
        engagement = features.get("focus_active_engagement_ratio")
        if engagement is None:
            return 0.0
        if baseline is not None and baseline.has_baseline_for(
            "focus_active_engagement_ratio"
        ):
            return baseline.zscore("focus_active_engagement_ratio", engagement)
        if baseline is not None and len(baseline.engagement_history) >= 2:
            mean_value = statistics.fmean(baseline.engagement_history)
            std_value = max(statistics.stdev(baseline.engagement_history), EPSILON)
            return (engagement - mean_value) / std_value
        return 0.0

    def _compute_instability_index(
        self,
        features: Dict[str, float],
        context: Optional[SessionContext],
    ) -> float:
        signals = [
            self._normalize_feature(name, features[name])
            for name in INSTABILITY_FEATURES
            if name in features
        ]
        micro_engagements = self._collect_micro_feature_values(
            context, "focus_active_engagement_ratio",
        )
        if len(micro_engagements) >= 2:
            signals.append(min(1.0, statistics.stdev(micro_engagements)))
        return _mean(signals)

    def _compute_concept_loop_score(self, features: Dict[str, float]) -> float:
        signals = [
            _bounded_ratio(features.get("scroll_concept_loop_count", 0.0), 3.0),
            features.get("scroll_revisit_rate", 0.0),
            _bounded_ratio(
                features.get("video_same_segment_replay_count", 0.0), 3.0,
            ),
        ]
        return _mean(signals)

    def _compute_retention_risk_proxy(
        self,
        features: Dict[str, float],
        struggle_score: float,
    ) -> float:
        quiz_risk = 1.0 - features.get("quiz_score", 0.5)
        first_attempt_risk = 1.0 - features.get("quiz_first_attempt_accuracy", 0.5)
        hint_dependency = features.get("quiz_hint_dependency_ratio", 0.0)
        coverage_risk = 1.0 - max(
            features.get("video_completion_ratio", 0.0),
            features.get("scroll_reading_coverage", 0.0),
        )
        fatigue = self._compute_fatigue_proxy(features, None)
        return _mean([
            quiz_risk,
            first_attempt_risk,
            hint_dependency,
            coverage_risk,
            fatigue,
            struggle_score,
        ])

    def _compute_fatigue_proxy(
        self,
        features: Dict[str, float],
        baseline: Optional[UserBaseline],
    ) -> float:
        signals: List[float] = []
        for name in FATIGUE_FEATURES:
            if name not in features:
                continue
            value = features[name]
            if baseline is not None and baseline.has_baseline_for(name):
                signals.append(_sigmoid(baseline.zscore(name, value)))
            else:
                signals.append(self._normalize_feature(name, value))

        acceleration = features.get("typing_acceleration")
        if acceleration is not None:
            signals.append(_bounded_ratio(max(0.0, -acceleration), 50.0))

        engagement = features.get("focus_active_engagement_ratio")
        if engagement is not None:
            signals.append(1.0 - engagement)

        return _mean(signals)
    # Utility methods

    def _normalize_feature(self, feature_name: str, value: float) -> float:
        scales: Dict[str, float] = {
            "video_rewind_density": 5.0,
            "video_same_segment_replay_count": 3.0,
            "video_slowdown_ratio": 1.0,
            "scroll_reversal_rate": 6.0,
            "scroll_revisit_rate": 1.0,
            "scroll_concept_loop_count": 3.0,
            "typing_backspace_rate": 0.5,
            "typing_correction_burst_rate": 3.0,
            "typing_iki_cv": 2.0,
            "typing_iki_mean_ms": 2000.0,
            "typing_iki_std_ms": 2000.0,
            "typing_dwell_time_mean_ms": 500.0,
            "quiz_answer_change_rate": 3.0,
            "quiz_confidence_mismatch": 1.0,
            "scroll_velocity_std_px_s": 2000.0,
            "scroll_dwell_time_variance_s": 900.0,
            "focus_return_latency_std_s": 120.0,
            "quiz_time_to_answer_cv": 2.0,
            "focus_idle_ratio": 1.0,
            "focus_loss_ratio": 1.0,
        }
        if feature_name == "quiz_confidence_mismatch":
            return max(0.0, min(1.0, value))
        return _bounded_ratio(max(0.0, value), scales.get(feature_name, 1.0))

    def _compute_quality(
        self,
        feature_name: str,
        source_quality: Dict[str, float],
        baseline: Optional[UserBaseline],
    ) -> float:
        if feature_name in {
            "personal_drift_zscore",
            "engagement_deviation",
        } and baseline is None:
            return 0.0
        if not source_quality:
            return 0.0
        return _mean(list(source_quality.values()))

    @staticmethod
    def _flatten_features(
        modality_results: Dict[str, FeatureResult],
    ) -> Dict[str, float]:
        features: Dict[str, float] = {}
        for result in modality_results.values():
            features.update(result.features)
        return features

    @staticmethod
    def _flatten_quality(
        modality_results: Dict[str, FeatureResult],
    ) -> Dict[str, float]:
        quality: Dict[str, float] = {}
        for result in modality_results.values():
            quality.update(result.quality)
        return quality

    @staticmethod
    def _first_window_id(
        modality_results: Dict[str, FeatureResult],
    ) -> Optional[str]:
        for result in modality_results.values():
            return result.window_id
        return None

    @staticmethod
    def _collect_micro_feature_values(
        context: Optional[SessionContext],
        feature_name: str,
    ) -> List[float]:
        if context is None:
            return []
        values: List[float] = []
        for result in context.micro_window_results:
            if feature_name in result.features:
                values.append(result.features[feature_name])
        return values
