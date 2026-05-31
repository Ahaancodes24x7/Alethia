from __future__ import annotations

import statistics
from typing import Dict, List, Tuple

from .base import (
    FeatureExtractor,
    FeatureMetadata,
    FeatureResult,
    TelemetryEvent,
    TelemetryWindow,
)



_RAPID_SWITCH_GAP_S: float = 5.0
"""Tab switches occurring within this many seconds count as rapid switching."""

_IDLE_BOUT_MIN_DURATION_S: float = 30.0
"""Minimum duration for an idle period to count as a distinct bout."""

_SECONDS_PER_MINUTE: float = 60.0


def _build_metadata_registry() -> Dict[str, FeatureMetadata]:
    """
    Construct the complete metadata registry for focus features.

    Returns:
        Mapping of feature name to FeatureMetadata.
    """
    return {
        "focus_loss_count": FeatureMetadata(
            name="focus_loss_count",
            display_name="Focus Loss Count",
            modality="focus",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="count",
            description="Number of focus loss events in the window.",
        ),
        "focus_loss_total_duration_s": FeatureMetadata(
            name="focus_loss_total_duration_s",
            display_name="Total Focus Loss Duration",
            modality="focus",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Total seconds the learning tab was unfocused.",
        ),
        "focus_loss_ratio": FeatureMetadata(
            name="focus_loss_ratio",
            display_name="Focus Loss Ratio",
            modality="focus",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="ratio",
            description="Proportion of window time spent unfocused.",
        ),
        "focus_mean_loss_duration_s": FeatureMetadata(
            name="focus_mean_loss_duration_s",
            display_name="Mean Focus Loss Duration",
            modality="focus",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Mean duration of individual focus loss episodes.",
        ),
        "focus_max_loss_duration_s": FeatureMetadata(
            name="focus_max_loss_duration_s",
            display_name="Max Focus Loss Duration",
            modality="focus",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Longest single focus loss episode.",
        ),
        "focus_rapid_tab_switch_rate": FeatureMetadata(
            name="focus_rapid_tab_switch_rate",
            display_name="Rapid Tab Switch Rate",
            modality="focus",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="per_minute",
            description="Tab switches with under 5s between them, per minute.",
        ),
        "focus_return_latency_mean_s": FeatureMetadata(
            name="focus_return_latency_mean_s",
            display_name="Mean Return Latency",
            modality="focus",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Mean time to return focus after losing it.",
        ),
        "focus_return_latency_std_s": FeatureMetadata(
            name="focus_return_latency_std_s",
            display_name="Return Latency Variability",
            modality="focus",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Standard deviation of return latencies.",
        ),
        "focus_idle_ratio": FeatureMetadata(
            name="focus_idle_ratio",
            display_name="Idle Time Ratio",
            modality="focus",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="ratio",
            description="Proportion of window time with no user activity.",
        ),
        "focus_idle_bout_count": FeatureMetadata(
            name="focus_idle_bout_count",
            display_name="Idle Bout Count",
            modality="focus",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="count",
            description="Number of distinct idle periods exceeding 30s.",
        ),
        "focus_active_engagement_ratio": FeatureMetadata(
            name="focus_active_engagement_ratio",
            display_name="Active Engagement Ratio",
            modality="focus",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_engagement",
            requires_baseline=True,
            unit="ratio",
            description="Estimated active engagement (1 - loss - idle).",
        ),
        "focus_context_flag": FeatureMetadata(
            name="focus_context_flag",
            display_name="Context Flag",
            modality="focus",
            tier=3,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="binary",
            description="1 if assessment mode, 0 if learning mode.",
        ),
    }

# Helpers

def _pair_focus_episodes(
    focus_loss_events: List[TelemetryEvent],
    focus_gain_events: List[TelemetryEvent],
    window_end_s: float,
) -> List[Tuple[float, float]]:
    
    if not focus_loss_events:
        return []

    episodes: List[Tuple[float, float]] = []
    gain_iter = iter(focus_gain_events)
    next_gain = next(gain_iter, None)

    for loss in focus_loss_events:
        while next_gain is not None and next_gain.timestamp <= loss.timestamp:
            next_gain = next(gain_iter, None)
        gain_timestamp = (
            next_gain.timestamp if next_gain is not None else window_end_s
        )
        episodes.append((loss.timestamp, gain_timestamp))
        if next_gain is not None:
            next_gain = next(gain_iter, None)

    return episodes


def _pair_idle_episodes(
    idle_start_events: List[TelemetryEvent],
    idle_end_events: List[TelemetryEvent],
    window_end_s: float,
) -> List[Tuple[float, float]]:
    
    if not idle_start_events:
        return []

    episodes: List[Tuple[float, float]] = []
    end_iter = iter(idle_end_events)
    next_end = next(end_iter, None)

    for start in idle_start_events:
        while next_end is not None and next_end.timestamp <= start.timestamp:
            next_end = next(end_iter, None)
        end_timestamp = (
            next_end.timestamp if next_end is not None else window_end_s
        )
        episodes.append((start.timestamp, end_timestamp))
        if next_end is not None:
            next_end = next(end_iter, None)

    return episodes


# Extractor


class FocusFeatureExtractor(FeatureExtractor):
    

    _MODALITY: str = "focus"
    _METADATA_REGISTRY: Dict[str, FeatureMetadata] = _build_metadata_registry()
    _MIN_EVENTS: int = 4

    def get_modality(self) -> str:
        """Return the modality identifier."""
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        """Return the complete metadata registry for focus features."""
        return dict(self._METADATA_REGISTRY)

    def get_required_event_types(self) -> List[str]:
        """Return event types required by this extractor."""
        return [
            "focus_gain",
            "focus_loss",
            "tab_switch",
            "idle_start",
            "idle_end",
        ]

    def get_minimum_events(self) -> int:
        """Return the minimum event count for reliable estimates."""
        return self._MIN_EVENTS

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        
        focus_loss_events = sorted(
            window.events_by_type.get("focus_loss", []),
            key=lambda e: e.timestamp,
        )
        focus_gain_events = sorted(
            window.events_by_type.get("focus_gain", []),
            key=lambda e: e.timestamp,
        )
        tab_switch_events = sorted(
            window.events_by_type.get("tab_switch", []),
            key=lambda e: e.timestamp,
        )
        idle_start_events = sorted(
            window.events_by_type.get("idle_start", []),
            key=lambda e: e.timestamp,
        )
        idle_end_events = sorted(
            window.events_by_type.get("idle_end", []),
            key=lambda e: e.timestamp,
        )

        total_focus_events = (
            len(focus_loss_events)
            + len(focus_gain_events)
            + len(tab_switch_events)
            + len(idle_start_events)
            + len(idle_end_events)
        )

        raw_features: Dict[str, float] = {}
        warnings: List[str] = []

        raw_features.update(
            self._compute_focus_loss_metrics(
                focus_loss_events,
                focus_gain_events,
                window.duration_s,
                window.end_time,
            )
        )
        raw_features.update(
            self._compute_tab_switch_metrics(
                tab_switch_events,
                window.duration_s,
            )
        )
        raw_features.update(
            self._compute_return_latency_metrics(
                focus_loss_events,
                focus_gain_events,
                window.end_time,
            )
        )
        raw_features.update(
            self._compute_idle_metrics(
                idle_start_events,
                idle_end_events,
                window.duration_s,
                window.end_time,
            )
        )
        raw_features.update(
            self._compute_engagement_ratio(
                raw_features.get("focus_loss_ratio", 0.0),
                raw_features.get("focus_idle_ratio", 0.0),
            )
        )
        raw_features.update(
            {"focus_context_flag": 1.0 if window.mode == "assessment" else 0.0}
        )

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=max(total_focus_events, 1),
            warnings=warnings,
        )

    # Focus loss metrics

    def _compute_focus_loss_metrics(
        self,
        focus_loss_events: List[TelemetryEvent],
        focus_gain_events: List[TelemetryEvent],
        window_duration_s: float,
        window_end_s: float,
    ) -> Dict[str, float]:
        
        episodes = _pair_focus_episodes(
            focus_loss_events, focus_gain_events, window_end_s,
        )
        durations: List[float] = [
            max(0.0, gain - loss) for loss, gain in episodes
        ]

        loss_count = float(len(focus_loss_events))
        total_duration = sum(durations)
        ratio = (
            min(1.0, total_duration / window_duration_s)
            if window_duration_s > 0 else 0.0
        )
        mean_duration = statistics.fmean(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        return {
            "focus_loss_count": loss_count,
            "focus_loss_total_duration_s": total_duration,
            "focus_loss_ratio": ratio,
            "focus_mean_loss_duration_s": mean_duration,
            "focus_max_loss_duration_s": max_duration,
        }
    # Tab switch metrics

    def _compute_tab_switch_metrics(
        self,
        tab_switch_events: List[TelemetryEvent],
        window_duration_s: float,
    ) -> Dict[str, float]:
        if len(tab_switch_events) < 2:
            return {"focus_rapid_tab_switch_rate": 0.0}

        rapid_count = 0
        for i in range(1, len(tab_switch_events)):
            gap = (
                tab_switch_events[i].timestamp
                - tab_switch_events[i - 1].timestamp
            )
            if gap < _RAPID_SWITCH_GAP_S:
                rapid_count += 1

        minutes = window_duration_s / _SECONDS_PER_MINUTE
        rate = rapid_count / minutes if minutes > 0 else 0.0
        return {"focus_rapid_tab_switch_rate": rate}
    # Return latency
    

    def _compute_return_latency_metrics(
        self,
        focus_loss_events: List[TelemetryEvent],
        focus_gain_events: List[TelemetryEvent],
        window_end_s: float,
    ) -> Dict[str, float]:
        episodes = _pair_focus_episodes(
            focus_loss_events, focus_gain_events, window_end_s,
        )

        # Only include episodes where the user actually returned focus
        # within the window (gain_timestamp < window_end_s).
        latencies = [
            max(0.0, gain - loss)
            for loss, gain in episodes
            if gain < window_end_s
        ]

        if not latencies:
            return {
                "focus_return_latency_mean_s": 0.0,
                "focus_return_latency_std_s": 0.0,
            }

        mean_latency = statistics.fmean(latencies)
        std_latency = (
            statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        )

        return {
            "focus_return_latency_mean_s": mean_latency,
            "focus_return_latency_std_s": std_latency,
        }

    # Idle metrics
    

    def _compute_idle_metrics(
        self,
        idle_start_events: List[TelemetryEvent],
        idle_end_events: List[TelemetryEvent],
        window_duration_s: float,
        window_end_s: float,
    ) -> Dict[str, float]:
        episodes = _pair_idle_episodes(
            idle_start_events, idle_end_events, window_end_s,
        )
        durations = [max(0.0, end - start) for start, end in episodes]

        total_idle = sum(durations)
        idle_ratio = (
            min(1.0, total_idle / window_duration_s)
            if window_duration_s > 0 else 0.0
        )
        bout_count = sum(
            1 for d in durations if d >= _IDLE_BOUT_MIN_DURATION_S
        )

        return {
            "focus_idle_ratio": idle_ratio,
            "focus_idle_bout_count": float(bout_count),
        }

    def _compute_engagement_ratio(
        self,
        focus_loss_ratio: float,
        idle_ratio: float,
    ) -> Dict[str, float]:
        
        engagement = max(0.0, 1.0 - focus_loss_ratio - idle_ratio)
        return {"focus_active_engagement_ratio": min(1.0, engagement)}