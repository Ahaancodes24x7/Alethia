from __future__ import annotations

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

# Constants

_SECTION_BUCKET_PX: float = 800.0

_MIN_DWELL_S: float = 0.5


_LOOP_GAP_PX: float = 400.0


_SECONDS_PER_MINUTE: float = 60.0


_WORDS_PER_PIXEL_APPROX: float = 0.04

# Feature Metadata Registry

def _build_metadata_registry() -> Dict[str, FeatureMetadata]:
    return {
        "scroll_velocity_mean_px_s": FeatureMetadata(
            name="scroll_velocity_mean_px_s",
            display_name="Mean Scroll Velocity",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="pixels_per_second",
            description="Average scroll speed in pixels per second.",
        ),
        "scroll_velocity_std_px_s": FeatureMetadata(
            name="scroll_velocity_std_px_s",
            display_name="Scroll Velocity Variability",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="pixels_per_second",
            description="Standard deviation of scroll velocity.",
        ),
        "scroll_reversal_rate": FeatureMetadata(
            name="scroll_reversal_rate",
            display_name="Scroll Reversal Rate",
            modality="scroll",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=True,
            unit="per_minute",
            description="Scroll direction changes per minute of reading.",
        ),
        "scroll_reversal_depth_mean_px": FeatureMetadata(
            name="scroll_reversal_depth_mean_px",
            display_name="Mean Reversal Depth",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="pixels",
            description="Average upward distance of reversal scrolls.",
        ),
        "scroll_revisit_rate": FeatureMetadata(
            name="scroll_revisit_rate",
            display_name="Section Revisit Rate",
            modality="scroll",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of sections visited more than once.",
        ),
        "scroll_concept_loop_count": FeatureMetadata(
            name="scroll_concept_loop_count",
            display_name="Concept Loop Count",
            modality="scroll",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="count",
            description="Returns to a section after leaving it.",
        ),
        "scroll_reading_coverage": FeatureMetadata(
            name="scroll_reading_coverage",
            display_name="Reading Coverage",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_engagement",
            requires_baseline=False,
            unit="ratio",
            description="Maximum scroll position divided by document height.",
        ),
        "scroll_dwell_time_mean_s": FeatureMetadata(
            name="scroll_dwell_time_mean_s",
            display_name="Mean Section Dwell Time",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="seconds",
            description="Average time spent per content section.",
        ),
        "scroll_dwell_time_variance_s": FeatureMetadata(
            name="scroll_dwell_time_variance_s",
            display_name="Section Dwell Variance",
            modality="scroll",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds_squared",
            description="Variance of per-section dwell times.",
        ),
        "scroll_linear_reading_ratio": FeatureMetadata(
            name="scroll_linear_reading_ratio",
            display_name="Linear Reading Ratio",
            modality="scroll",
            tier=3,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_engagement",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of scrolling that is monotonically downward.",
        ),
        "scroll_section_skip_count": FeatureMetadata(
            name="scroll_section_skip_count",
            display_name="Section Skip Count",
            modality="scroll",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="count",
            description="Number of sections with zero dwell time.",
        ),
        "scroll_reading_speed_wpm_estimate": FeatureMetadata(
            name="scroll_reading_speed_wpm_estimate",
            display_name="Reading Speed Estimate",
            modality="scroll",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="words_per_minute",
            description="Estimated reading speed based on scroll dynamics.",
        ),
    }


def _extract_scroll_position(event: TelemetryEvent) -> Optional[float]:
    
    position = event.payload.get("scroll_y")
    if isinstance(position, (int, float)):
        return float(position)
    return None


def _extract_document_height(events: List[TelemetryEvent]) -> Optional[float]:
    for event in events:
        height = event.payload.get("document_height")
        if isinstance(height, (int, float)) and height > 0:
            return float(height)
    return None

# Extractor
class ScrollFeatureExtractor(FeatureExtractor):

    _MODALITY: str = "scroll"
    _METADATA_REGISTRY: Dict[str, FeatureMetadata] = _build_metadata_registry()
    _MIN_EVENTS: int = 8

    def get_modality(self) -> str:
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        return dict(self._METADATA_REGISTRY)

    def get_required_event_types(self) -> List[str]:
        
        return ["scroll", "visibility"]

    def get_minimum_events(self) -> int:
        
        return self._MIN_EVENTS

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        if self._MODALITY not in window.modality_coverage:
            return self._build_empty_result(
                window, "No scroll events present in window.",
            )

        scroll_events = sorted(
            window.events_by_type.get("scroll", []),
            key=lambda e: e.timestamp,
        )

        if len(scroll_events) < 2:
            return self._build_empty_result(
                window,
                "Scroll modality flagged but fewer than 2 scroll events present.",
            )

        warnings: List[str] = []
        raw_features: Dict[str, float] = {}

        raw_features.update(self._compute_velocity_metrics(scroll_events))
        raw_features.update(
            self._compute_reversal_metrics(scroll_events, window.duration_s)
        )
        raw_features.update(
            self._compute_coverage_metrics(scroll_events)
        )
        raw_features.update(
            self._compute_section_metrics(scroll_events, warnings)
        )
        raw_features.update(
            self._compute_reading_speed_estimate(scroll_events)
        )

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=len(scroll_events),
            warnings=warnings,
        )
    # Velocity metrics
    

    def _compute_velocity_metrics(
        self,
        scroll_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        velocities: List[float] = []
        for i in range(1, len(scroll_events)):
            prev_pos = _extract_scroll_position(scroll_events[i - 1])
            curr_pos = _extract_scroll_position(scroll_events[i])
            if prev_pos is None or curr_pos is None:
                continue
            dt = scroll_events[i].timestamp - scroll_events[i - 1].timestamp
            if dt <= 0:
                continue
            velocities.append(abs(curr_pos - prev_pos) / dt)

        if not velocities:
            return {
                "scroll_velocity_mean_px_s": 0.0,
                "scroll_velocity_std_px_s": 0.0,
            }

        mean_velocity = statistics.fmean(velocities)
        std_velocity = (
            statistics.stdev(velocities) if len(velocities) > 1 else 0.0
        )

        return {
            "scroll_velocity_mean_px_s": mean_velocity,
            "scroll_velocity_std_px_s": std_velocity,
        }

    def _compute_reversal_metrics(
        self,
        scroll_events: List[TelemetryEvent],
        window_duration_s: float,
    ) -> Dict[str, float]:
        
        positions: List[float] = []
        for event in scroll_events:
            position = _extract_scroll_position(event)
            if position is not None:
                positions.append(position)

        if len(positions) < 3:
            return {
                "scroll_reversal_rate": 0.0,
                "scroll_reversal_depth_mean_px": 0.0,
            }

        reversal_count = 0
        reversal_depths: List[float] = []
        last_direction: int = 0  # -1 = up, 0 = none, +1 = down
        reversal_start_pos: Optional[float] = None

        for i in range(1, len(positions)):
            delta = positions[i] - positions[i - 1]
            if abs(delta) < EPSILON:
                continue
            direction = 1 if delta > 0 else -1

            if last_direction == 1 and direction == -1:
                reversal_count += 1
                reversal_start_pos = positions[i - 1]
            elif last_direction == -1 and direction == 1 and reversal_start_pos is not None:
                depth = max(0.0, reversal_start_pos - positions[i - 1])
                if depth > 0:
                    reversal_depths.append(depth)
                reversal_start_pos = None

            last_direction = direction

        minutes = window_duration_s / _SECONDS_PER_MINUTE
        rate = reversal_count / minutes if minutes > 0 else 0.0

        mean_depth = (
            statistics.fmean(reversal_depths) if reversal_depths else 0.0
        )

        return {
            "scroll_reversal_rate": rate,
            "scroll_reversal_depth_mean_px": mean_depth,
        }

    def _compute_coverage_metrics(
        self,
        scroll_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        positions: List[float] = []
        for event in scroll_events:
            position = _extract_scroll_position(event)
            if position is not None:
                positions.append(position)

        if not positions:
            return {
                "scroll_reading_coverage": 0.0,
                "scroll_linear_reading_ratio": 0.0,
            }

        document_height = _extract_document_height(scroll_events)
        max_position = max(positions)

        if document_height is not None and document_height > 0:
            coverage = min(1.0, max_position / document_height)
        else:
            coverage = 0.0

        # Linear reading ratio: fraction of consecutive transitions that
        # are monotonically downward.
        downward_count = 0
        total_transitions = 0
        for i in range(1, len(positions)):
            delta = positions[i] - positions[i - 1]
            if abs(delta) < EPSILON:
                continue
            total_transitions += 1
            if delta > 0:
                downward_count += 1

        linear_ratio = (
            downward_count / total_transitions if total_transitions > 0 else 0.0
        )

        return {
            "scroll_reading_coverage": coverage,
            "scroll_linear_reading_ratio": linear_ratio,
        }

    def _compute_section_metrics(
        self,
        scroll_events: List[TelemetryEvent],
        warnings: List[str],
    ) -> Dict[str, float]:
        
        # Build (timestamp, section_id) sequence.
        section_sequence: List[Tuple[float, int]] = []
        for event in scroll_events:
            position = _extract_scroll_position(event)
            if position is None:
                continue
            section_id = int(position / _SECTION_BUCKET_PX)
            section_sequence.append((event.timestamp, section_id))

        if len(section_sequence) < 2:
            warnings.append(
                "Insufficient scroll positions to compute section metrics."
            )
            return {
                "scroll_revisit_rate": 0.0,
                "scroll_concept_loop_count": 0.0,
                "scroll_dwell_time_mean_s": 0.0,
                "scroll_dwell_time_variance_s": 0.0,
                "scroll_section_skip_count": 0.0,
            }

        # Compute per-section dwell times (sum of time spent in each section).
        dwell_per_section: Dict[int, float] = {}
        visit_count_per_section: Dict[int, int] = {}
        loop_count = 0
        visited_sections: set = set()
        last_section: int = section_sequence[0][1]

        for i in range(1, len(section_sequence)):
            prev_ts, prev_section = section_sequence[i - 1]
            curr_ts, curr_section = section_sequence[i]
            dt = max(0.0, curr_ts - prev_ts)
            dwell_per_section[prev_section] = (
                dwell_per_section.get(prev_section, 0.0) + dt
            )

            if curr_section != prev_section:
                visit_count_per_section[curr_section] = (
                    visit_count_per_section.get(curr_section, 0) + 1
                )
                # Concept loop: returning to an already-visited section
                # after leaving it.
                if curr_section in visited_sections and abs(
                    curr_section - last_section
                ) * _SECTION_BUCKET_PX >= _LOOP_GAP_PX:
                    loop_count += 1
                visited_sections.add(curr_section)
                last_section = curr_section

        # Count the first section as visited.
        first_section = section_sequence[0][1]
        visited_sections.add(first_section)
        visit_count_per_section[first_section] = (
            visit_count_per_section.get(first_section, 0) + 1
        )

        # Revisit rate: fraction of visited sections that were visited >1 times.
        revisited = sum(
            1 for count in visit_count_per_section.values() if count > 1
        )
        revisit_rate = (
            revisited / len(visit_count_per_section)
            if visit_count_per_section else 0.0
        )

        # Filter out trivial dwells.
        meaningful_dwells = [
            dwell for dwell in dwell_per_section.values()
            if dwell >= _MIN_DWELL_S
        ]

        if meaningful_dwells:
            mean_dwell = statistics.fmean(meaningful_dwells)
            variance_dwell = (
                statistics.variance(meaningful_dwells)
                if len(meaningful_dwells) > 1 else 0.0
            )
        else:
            mean_dwell = 0.0
            variance_dwell = 0.0

        # Section skip count: visited sections whose dwell time is essentially zero.
        skip_count = sum(
            1 for dwell in dwell_per_section.values() if dwell < _MIN_DWELL_S
        )

        return {
            "scroll_revisit_rate": revisit_rate,
            "scroll_concept_loop_count": float(loop_count),
            "scroll_dwell_time_mean_s": mean_dwell,
            "scroll_dwell_time_variance_s": variance_dwell,
            "scroll_section_skip_count": float(skip_count),
        }

    def _compute_reading_speed_estimate(
        self,
        scroll_events: List[TelemetryEvent],
    ) -> Dict[str, float]:
        
        positions: List[float] = []
        timestamps: List[float] = []
        for event in scroll_events:
            position = _extract_scroll_position(event)
            if position is not None:
                positions.append(position)
                timestamps.append(event.timestamp)

        if len(positions) < 2:
            return {"scroll_reading_speed_wpm_estimate": 0.0}

        net_distance = max(0.0, positions[-1] - positions[0])
        elapsed_seconds = max(EPSILON, timestamps[-1] - timestamps[0])
        elapsed_minutes = elapsed_seconds / _SECONDS_PER_MINUTE

        if elapsed_minutes <= 0:
            return {"scroll_reading_speed_wpm_estimate": 0.0}

        wpm_estimate = (net_distance * _WORDS_PER_PIXEL_APPROX) / elapsed_minutes
        return {"scroll_reading_speed_wpm_estimate": wpm_estimate}