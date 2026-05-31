

from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Dict, List, Optional

from .base import (
    EPSILON,
    FeatureExtractor,
    FeatureMetadata,
    FeatureResult,
    TelemetryEvent,
    TelemetryWindow,
)



_LONG_PAUSE_THRESHOLD_MS: float = 2000.0


_CORRECTION_BURST_MIN_LENGTH: int = 3


_RHYTHM_ENTROPY_BINS: int = 10


_MS_PER_SECOND: float = 1000.0
_SECONDS_PER_MINUTE: float = 60.0
_KEY_CATEGORY_BACKSPACE: str = "backspace"


def _build_metadata_registry() -> Dict[str, FeatureMetadata]:
    
    return {
        "typing_iki_mean_ms": FeatureMetadata(
            name="typing_iki_mean_ms",
            display_name="Mean Inter-Key Interval",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=True,
            unit="milliseconds",
            description="Mean time between consecutive keystrokes.",
        ),
        "typing_iki_std_ms": FeatureMetadata(
            name="typing_iki_std_ms",
            display_name="IKI Standard Deviation",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=True,
            unit="milliseconds",
            description="Variability of inter-key intervals.",
        ),
        "typing_iki_cv": FeatureMetadata(
            name="typing_iki_cv",
            display_name="IKI Coefficient of Variation",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=False,
            unit="ratio",
            description="Normalized IKI variability (std/mean).",
        ),
        "typing_speed_cpm": FeatureMetadata(
            name="typing_speed_cpm",
            display_name="Typing Speed",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="characters_per_minute",
            description="Characters typed per minute.",
        ),
        "typing_dwell_time_mean_ms": FeatureMetadata(
            name="typing_dwell_time_mean_ms",
            display_name="Mean Key Dwell Time",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=True,
            unit="milliseconds",
            description="Average time a key is held down.",
        ),
        "typing_dwell_time_std_ms": FeatureMetadata(
            name="typing_dwell_time_std_ms",
            display_name="Dwell Time Variability",
            modality="typing",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=False,
            unit="milliseconds",
            description="Standard deviation of key hold durations.",
        ),
        "typing_flight_time_mean_ms": FeatureMetadata(
            name="typing_flight_time_mean_ms",
            display_name="Mean Flight Time",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=True,
            unit="milliseconds",
            description="Average time between keyup and next keydown.",
        ),
        "typing_flight_time_std_ms": FeatureMetadata(
            name="typing_flight_time_std_ms",
            display_name="Flight Time Variability",
            modality="typing",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="more_fatigue",
            requires_baseline=False,
            unit="milliseconds",
            description="Standard deviation of flight times.",
        ),
        "typing_backspace_rate": FeatureMetadata(
            name="typing_backspace_rate",
            display_name="Backspace Rate",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=True,
            unit="ratio",
            description="Backspace count divided by total keystrokes.",
        ),
        "typing_correction_burst_rate": FeatureMetadata(
            name="typing_correction_burst_rate",
            display_name="Correction Burst Rate",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=True,
            unit="per_minute",
            description="Clusters of 3+ consecutive backspaces per minute.",
        ),
        "typing_correction_burst_length_mean": FeatureMetadata(
            name="typing_correction_burst_length_mean",
            display_name="Mean Correction Burst Length",
            modality="typing",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="count",
            description="Average length of correction bursts.",
        ),
        "typing_pause_before_typing_ms": FeatureMetadata(
            name="typing_pause_before_typing_ms",
            display_name="Pre-Typing Pause",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="milliseconds",
            description="Time gap from window start to first keystroke.",
        ),
        "typing_rhythm_entropy": FeatureMetadata(
            name="typing_rhythm_entropy",
            display_name="Typing Rhythm Entropy",
            modality="typing",
            tier=1,
            range_min=0.0,
            range_max=math.log(_RHYTHM_ENTROPY_BINS),
            higher_means="ambiguous",
            requires_baseline=True,
            unit="nats",
            description="Shannon entropy of binned IKI distribution.",
        ),
        "typing_long_pause_rate": FeatureMetadata(
            name="typing_long_pause_rate",
            display_name="Long Pause Rate",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of IKI gaps exceeding 2 seconds.",
        ),
        "typing_acceleration": FeatureMetadata(
            name="typing_acceleration",
            display_name="Typing Acceleration",
            modality="typing",
            tier=1,
            range_min=-1.0e6,
            range_max=1.0e6,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="cpm_per_second",
            description="Slope of typing speed over window. Negative = fatiguing.",
        ),
        "typing_error_correction_ratio": FeatureMetadata(
            name="typing_error_correction_ratio",
            display_name="Error Correction Ratio",
            modality="typing",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="ratio",
            description="Characters deleted divided by characters typed.",
        ),
    }


def _is_backspace(event: TelemetryEvent) -> bool:
    
    return event.payload.get("key_category") == _KEY_CATEGORY_BACKSPACE


def _pair_dwell_times(
    keydown_events: List[TelemetryEvent],
    keyup_events: List[TelemetryEvent],
) -> List[float]:
    
    if not keydown_events or not keyup_events:
        return []

    dwells: List[float] = []
    keyup_iter = iter(keyup_events)
    next_keyup: Optional[TelemetryEvent] = next(keyup_iter, None)

    for keydown in keydown_events:
        # Advance through keyups until one is at or after the keydown.
        while next_keyup is not None and next_keyup.timestamp < keydown.timestamp:
            next_keyup = next(keyup_iter, None)
        if next_keyup is None:
            break
        dwell_s = next_keyup.timestamp - keydown.timestamp
        if dwell_s >= 0:
            dwells.append(dwell_s * _MS_PER_SECOND)
        next_keyup = next(keyup_iter, None)

    return dwells


def _compute_flight_times(
    keydown_events: List[TelemetryEvent],
    keyup_events: List[TelemetryEvent],
) -> List[float]:
    
    if len(keydown_events) < 2 or not keyup_events:
        return []

    flights: List[float] = []
    keyup_timestamps = sorted(e.timestamp for e in keyup_events)
    keyup_idx = 0

    for i in range(len(keydown_events) - 1):
        current_down = keydown_events[i].timestamp
        next_down = keydown_events[i + 1].timestamp

        # Find the keyup that occurs after current_down and before next_down.
        while (
            keyup_idx < len(keyup_timestamps)
            and keyup_timestamps[keyup_idx] < current_down
        ):
            keyup_idx += 1

        if (
            keyup_idx < len(keyup_timestamps)
            and keyup_timestamps[keyup_idx] <= next_down
        ):
            flight_s = next_down - keyup_timestamps[keyup_idx]
            if flight_s >= 0:
                flights.append(flight_s * _MS_PER_SECOND)

    return flights


def _detect_correction_bursts(
    keydown_events: List[TelemetryEvent],
) -> List[int]:

    bursts: List[int] = []
    current_run: int = 0

    for event in keydown_events:
        if _is_backspace(event):
            current_run += 1
        else:
            if current_run >= _CORRECTION_BURST_MIN_LENGTH:
                bursts.append(current_run)
            current_run = 0

    if current_run >= _CORRECTION_BURST_MIN_LENGTH:
        bursts.append(current_run)

    return bursts


def _shannon_entropy(values: List[float], num_bins: int) -> float:
    if len(values) < 2:
        return 0.0

    min_val = min(values)
    max_val = max(values)
    if max_val - min_val < EPSILON:
        return 0.0

    bin_width = (max_val - min_val) / num_bins
    counts: Counter = Counter()
    for value in values:
        bin_index = min(num_bins - 1, int((value - min_val) / bin_width))
        counts[bin_index] += 1

    total = sum(counts.values())
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            probability = count / total
            entropy -= probability * math.log(probability)

    return entropy


def _linear_regression_slope(
    x_values: List[float],
    y_values: List[float],
) -> float:
    
    n = len(x_values)
    if n < 2 or n != len(y_values):
        return 0.0

    mean_x = statistics.fmean(x_values)
    mean_y = statistics.fmean(y_values)

    numerator = sum(
        (x - mean_x) * (y - mean_y)
        for x, y in zip(x_values, y_values)
    )
    denominator = sum((x - mean_x) ** 2 for x in x_values)

    if denominator < EPSILON:
        return 0.0
    return numerator / denominator


class TypingFeatureExtractor(FeatureExtractor):

    _MODALITY: str = "typing"
    _METADATA_REGISTRY: Dict[str, FeatureMetadata] = _build_metadata_registry()
    _MIN_EVENTS: int = 10

    def get_modality(self) -> str:
        """Return the modality identifier."""
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        """Return the complete metadata registry for typing features."""
        return dict(self._METADATA_REGISTRY)

    def get_required_event_types(self) -> List[str]:
        """Return event types required by this extractor."""
        return ["keydown", "keyup"]

    def get_minimum_events(self) -> int:
        """Return the minimum event count for reliable estimates."""
        return self._MIN_EVENTS

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        """
        Compute all typing features from the window.

        Args:
            window: TelemetryWindow potentially containing typing events.

        Returns:
            FeatureResult with typing features.
        """
        if self._MODALITY not in window.modality_coverage:
            return self._build_empty_result(
                window, "No typing events present in window.",
            )

        keydown_events = sorted(
            window.events_by_type.get("keydown", []),
            key=lambda e: e.timestamp,
        )
        keyup_events = sorted(
            window.events_by_type.get("keyup", []),
            key=lambda e: e.timestamp,
        )

        if len(keydown_events) < 2:
            return self._build_empty_result(
                window,
                "Typing modality flagged but fewer than 2 keydown events.",
            )

        warnings: List[str] = []
        raw_features: Dict[str, float] = {}

        iki_values_ms = self._compute_iki_values_ms(keydown_events)

        raw_features.update(self._compute_iki_metrics(iki_values_ms))
        raw_features.update(
            self._compute_dwell_flight_metrics(keydown_events, keyup_events)
        )
        raw_features.update(
            self._compute_correction_metrics(
                keydown_events, window.duration_s,
            )
        )
        raw_features.update(
            self._compute_speed_metrics(
                keydown_events, window.duration_s,
            )
        )
        raw_features.update(
            self._compute_pause_metrics(keydown_events, window.start_time, iki_values_ms)
        )
        raw_features.update(
            {"typing_rhythm_entropy": _shannon_entropy(
                iki_values_ms, _RHYTHM_ENTROPY_BINS,
            )}
        )
        raw_features.update(
            self._compute_acceleration(keydown_events, window.start_time)
        )

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=len(keydown_events),
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # IKI computation
    # ------------------------------------------------------------------

    def _compute_iki_values_ms(
        self,
        keydown_events: List[TelemetryEvent],
    ) -> List[float]:
        """
        Compute inter-key intervals in milliseconds.

        Args:
            keydown_events: Sorted keydown events.

        Returns:
            List of IKI values in milliseconds.
        """
        ikis: List[float] = []
        for i in range(1, len(keydown_events)):
            dt_s = keydown_events[i].timestamp - keydown_events[i - 1].timestamp
            if dt_s >= 0:
                ikis.append(dt_s * _MS_PER_SECOND)
        return ikis

    def _compute_iki_metrics(
        self,
        iki_values_ms: List[float],
    ) -> Dict[str, float]:
        """
        Compute IKI mean, standard deviation, and coefficient of variation.

        Args:
            iki_values_ms: List of inter-key intervals in milliseconds.

        Returns:
            Dictionary of IKI feature values.
        """
        if not iki_values_ms:
            return {
                "typing_iki_mean_ms": 0.0,
                "typing_iki_std_ms": 0.0,
                "typing_iki_cv": 0.0,
            }

        mean_iki = statistics.fmean(iki_values_ms)
        std_iki = (
            statistics.stdev(iki_values_ms)
            if len(iki_values_ms) > 1 else 0.0
        )
        cv = std_iki / mean_iki if mean_iki > EPSILON else 0.0

        return {
            "typing_iki_mean_ms": mean_iki,
            "typing_iki_std_ms": std_iki,
            "typing_iki_cv": cv,
        }  
    # Dwell and flight metrics
    

    def _compute_dwell_flight_metrics(
        self,
        keydown_events: List[TelemetryEvent],
        keyup_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        dwells_ms = _pair_dwell_times(keydown_events, keyup_events)
        flights_ms = _compute_flight_times(keydown_events, keyup_events)

        if dwells_ms:
            mean_dwell = statistics.fmean(dwells_ms)
            std_dwell = (
                statistics.stdev(dwells_ms) if len(dwells_ms) > 1 else 0.0
            )
        else:
            mean_dwell = 0.0
            std_dwell = 0.0

        if flights_ms:
            mean_flight = statistics.fmean(flights_ms)
            std_flight = (
                statistics.stdev(flights_ms) if len(flights_ms) > 1 else 0.0
            )
        else:
            mean_flight = 0.0
            std_flight = 0.0

        return {
            "typing_dwell_time_mean_ms": mean_dwell,
            "typing_dwell_time_std_ms": std_dwell,
            "typing_flight_time_mean_ms": mean_flight,
            "typing_flight_time_std_ms": std_flight,
        }

    def _compute_correction_metrics(
        self,
        keydown_events: List[TelemetryEvent],
        window_duration_s: float,
    ) -> Dict[str, float]:
        total_keystrokes = len(keydown_events)
        backspace_count = sum(1 for e in keydown_events if _is_backspace(e))

        backspace_rate = (
            backspace_count / total_keystrokes if total_keystrokes > 0 else 0.0
        )

        bursts = _detect_correction_bursts(keydown_events)
        minutes = window_duration_s / _SECONDS_PER_MINUTE
        burst_rate = len(bursts) / minutes if minutes > 0 else 0.0
        mean_burst_length = statistics.fmean(bursts) if bursts else 0.0

        # Error correction ratio: deletes / non-deletes (characters typed).
        non_backspace_count = total_keystrokes - backspace_count
        error_ratio = (
            backspace_count / non_backspace_count
            if non_backspace_count > 0 else 0.0
        )

        return {
            "typing_backspace_rate": backspace_rate,
            "typing_correction_burst_rate": burst_rate,
            "typing_correction_burst_length_mean": mean_burst_length,
            "typing_error_correction_ratio": error_ratio,
        }


    def _compute_speed_metrics(
        self,
        keydown_events: List[TelemetryEvent],
        window_duration_s: float,
    ) -> Dict[str, float]:

        non_backspace_count = sum(
            1 for e in keydown_events if not _is_backspace(e)
        )
        minutes = window_duration_s / _SECONDS_PER_MINUTE
        cpm = non_backspace_count / minutes if minutes > 0 else 0.0
        return {"typing_speed_cpm": cpm}

    def _compute_pause_metrics(
        self,
        keydown_events: List[TelemetryEvent],
        window_start: float,
        iki_values_ms: List[float],
    ) -> Dict[str, float]:
        pause_before = (
            (keydown_events[0].timestamp - window_start) * _MS_PER_SECOND
            if keydown_events else 0.0
        )
        pause_before = max(0.0, pause_before)

        long_pause_count = sum(
            1 for iki in iki_values_ms if iki > _LONG_PAUSE_THRESHOLD_MS
        )
        long_pause_rate = (
            long_pause_count / len(iki_values_ms) if iki_values_ms else 0.0
        )

        return {
            "typing_pause_before_typing_ms": pause_before,
            "typing_long_pause_rate": long_pause_rate,
        }

    def _compute_acceleration(
        self,
        keydown_events: List[TelemetryEvent],
        window_start: float,
    ) -> Dict[str, float]:
        
        if len(keydown_events) < 4:
            return {"typing_acceleration": 0.0}

        timestamps = [e.timestamp for e in keydown_events]
        window_end = timestamps[-1]
        window_span = window_end - window_start
        if window_span < EPSILON:
            return {"typing_acceleration": 0.0}

        num_buckets = 4
        bucket_duration = window_span / num_buckets
        if bucket_duration < EPSILON:
            return {"typing_acceleration": 0.0}

        bucket_counts: List[int] = [0] * num_buckets
        for ts in timestamps:
            bucket_idx = min(
                num_buckets - 1,
                int((ts - window_start) / bucket_duration),
            )
            bucket_counts[bucket_idx] += 1

        # Convert counts to per-minute rates for each bucket midpoint.
        bucket_midpoints_s: List[float] = [
            (i + 0.5) * bucket_duration for i in range(num_buckets)
        ]
        bucket_cpm: List[float] = [
            count / (bucket_duration / _SECONDS_PER_MINUTE)
            if bucket_duration > 0 else 0.0
            for count in bucket_counts
        ]

        slope = _linear_regression_slope(bucket_midpoints_s, bucket_cpm)
        return {"typing_acceleration": slope}
