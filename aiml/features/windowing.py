from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .base import TelemetryEvent, TelemetryWindow, VALID_MODES

# Event Type to Modality Mapping

EVENT_TYPE_TO_MODALITY: Dict[str, str] = {
    # Video events
    "video_play": "video",
    "video_pause": "video",
    "video_seek_backward": "video",
    "video_seek_forward": "video",
    "video_speed_change": "video",
    "video_buffer": "video",
    "video_end": "video",
    "video_position": "video",
    # Scroll events
    "scroll": "scroll",
    "visibility": "scroll",
    # Typing events
    "keydown": "typing",
    "keyup": "typing",
    # Focus events
    "focus_gain": "focus",
    "focus_loss": "focus",
    "tab_switch": "focus",
    "idle_start": "focus",
    "idle_end": "focus",
    # Quiz events
    "quiz_start": "quiz",
    "question_display": "quiz",
    "answer_change": "quiz",
    "hint_request": "quiz",
    "answer_submit": "quiz",
    "confidence_rating": "quiz",
    "quiz_end": "quiz",
    # External events
    "external_tab_open": "external",
    "external_tab_close": "external",
}


@dataclass(frozen=True)
class WindowConfig:
    #breaking one session into multiple small windows

    micro_window_size_s: float = 30.0
    micro_window_slide_s: float = 15.0
    micro_window_min_events: int = 5
    session_max_duration_s: float = 7200.0
    session_min_duration_s: float = 60.0
    gap_split_threshold_s: float = 300.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.micro_window_size_s <= 0:
            raise ValueError("micro_window_size_s must be positive.")
        if self.micro_window_slide_s <= 0:
            raise ValueError("micro_window_slide_s must be positive.")
        if self.micro_window_slide_s > self.micro_window_size_s:
            raise ValueError(
                "micro_window_slide_s must not exceed micro_window_size_s."
            )
        if self.micro_window_min_events < 0:
            raise ValueError("micro_window_min_events must be non-negative.")
        if self.session_min_duration_s <= 0:
            raise ValueError("session_min_duration_s must be positive.")
        if self.session_max_duration_s <= self.session_min_duration_s:
            raise ValueError(
                "session_max_duration_s must exceed session_min_duration_s."
            )
        if self.gap_split_threshold_s <= 0:
            raise ValueError("gap_split_threshold_s must be positive.")

#grouping events by type, so that indivitual feature files dont use high complexity loops to search
def group_events_by_type(
    events: List[TelemetryEvent],
) -> Dict[str, List[TelemetryEvent]]:
    
    grouped: Dict[str, List[TelemetryEvent]] = defaultdict(list)
    for event in events:
        grouped[event.event_type].append(event)
    return dict(grouped)

#Helps determine which particular modality is present in a given window.
def compute_modality_coverage(events: List[TelemetryEvent]) -> Set[str]:
    
    coverage: Set[str] = set()
    for event in events:
        modality = EVENT_TYPE_TO_MODALITY.get(event.event_type)
        if modality is not None:
            coverage.add(modality)
    return coverage


def detect_gaps(
    events: List[TelemetryEvent],
    max_gap_s: float,
) -> List[Tuple[int, float]]:
    
    gaps: List[Tuple[int, float]] = []
    if len(events) < 2:
        return gaps

    for i in range(1, len(events)):
        gap = events[i].timestamp - events[i - 1].timestamp
        if gap > max_gap_s:
            gaps.append((i, gap))

    return gaps


def _sort_events(events: List[TelemetryEvent]) -> List[TelemetryEvent]:
    
    return sorted(events, key=lambda e: e.timestamp)


def _build_window(
    events: List[TelemetryEvent],
    start_time: float,
    end_time: float,
    session_id: str,
    user_id: str,
    content_type: str,
    content_id: str,
    mode: str,
) -> TelemetryWindow:
    
    sorted_events = _sort_events(events)
    return TelemetryWindow(
        window_id=str(uuid.uuid4()),
        start_time=start_time,
        end_time=end_time,
        events=sorted_events,
        events_by_type=group_events_by_type(sorted_events),
        session_id=session_id,
        user_id=user_id,
        content_type=content_type,
        content_id=content_id,
        mode=mode,
        modality_coverage=compute_modality_coverage(sorted_events),
    )


# ============================================================================
# Window Generator
# ============================================================================

class WindowGenerator:
    #Divides the data into two windows: micro-windows and session windows. Micro-windows are short, fixed-size windows that slide across the session, while session windows cover the entire session duration (with potential truncation for long sessions).

    def __init__(self, config: Optional[WindowConfig] = None) -> None:
        
        self.config: WindowConfig = config if config is not None else WindowConfig()

    def create_micro_windows(
        self,
        events: List[TelemetryEvent],
        session_id: str,
        user_id: str,
        content_type: str,
        content_id: str,
        mode: str,
    ) -> List[TelemetryWindow]:
        
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {sorted(VALID_MODES)}."
            )
        if not events:
            return []

        sorted_events = _sort_events(events)
        first_timestamp = sorted_events[0].timestamp
        last_timestamp = sorted_events[-1].timestamp
        total_duration = last_timestamp - first_timestamp

        if total_duration < self.config.session_min_duration_s:
            return []

        windows: List[TelemetryWindow] = []
        window_size = self.config.micro_window_size_s
        slide = self.config.micro_window_slide_s

        # Iterate window start times across the session.
        current_start = first_timestamp
        while current_start <= last_timestamp:
            current_end = current_start + window_size

            window_events = [
                event for event in sorted_events
                if current_start <= event.timestamp < current_end
            ]

            if len(window_events) >= self.config.micro_window_min_events:
                windows.append(
                    _build_window(
                        events=window_events,
                        start_time=current_start,
                        end_time=current_end,
                        session_id=session_id,
                        user_id=user_id,
                        content_type=content_type,
                        content_id=content_id,
                        mode=mode,
                    )
                )

            current_start += slide

        return windows

    def create_session_window(
        self,
        events: List[TelemetryEvent],
        session_id: str,
        user_id: str,
        content_type: str,
        content_id: str,
        mode: str,
    ) -> Optional[TelemetryWindow]:
        
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {sorted(VALID_MODES)}."
            )
        if not events:
            return None

        sorted_events = _sort_events(events)
        first_timestamp = sorted_events[0].timestamp
        last_timestamp = sorted_events[-1].timestamp
        total_duration = last_timestamp - first_timestamp

        if total_duration < self.config.session_min_duration_s:
            return None

        # Truncate overly long sessions at the largest gap if possible.
        if total_duration > self.config.session_max_duration_s:
            sorted_events, last_timestamp = self._truncate_long_session(
                sorted_events, first_timestamp,
            )

        return _build_window(
            events=sorted_events,
            start_time=first_timestamp,
            end_time=last_timestamp,
            session_id=session_id,
            user_id=user_id,
            content_type=content_type,
            content_id=content_id,
            mode=mode,
        )

    def _truncate_long_session(
        self,
        sorted_events: List[TelemetryEvent],
        first_timestamp: float,
    ) -> Tuple[List[TelemetryEvent], float]:
        
        max_allowed_end = first_timestamp + self.config.session_max_duration_s
        gaps = detect_gaps(sorted_events, self.config.gap_split_threshold_s)

        # Prefer truncating at a natural gap within the allowed window.
        candidate_gaps = [
            (idx, gap_size) for idx, gap_size in gaps
            if sorted_events[idx - 1].timestamp <= max_allowed_end
        ]

        if candidate_gaps:
            # Choose the latest gap within the allowed window.
            best_idx = max(candidate_gaps, key=lambda g: g[0])[0]
            truncated = sorted_events[:best_idx]
            new_last = truncated[-1].timestamp
            return truncated, new_last

        # Hard truncation by timestamp.
        truncated = [
            event for event in sorted_events
            if event.timestamp <= max_allowed_end
        ]
        new_last = truncated[-1].timestamp if truncated else first_timestamp
        return truncated, new_last