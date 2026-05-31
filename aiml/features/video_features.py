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

_SEGMENT_TOLERANCE_S: float = 10.0

_SEGMENT_BUCKET_SIZE_S: float = 5.0

_REPLAY_THRESHOLD: int = 3

_SECONDS_PER_MINUTE: float = 60.0

def _build_metadata_registry() -> Dict[str, FeatureMetadata]:
    return {
        "video_pause_density": FeatureMetadata(
            name="video_pause_density",
            display_name="Video Pause Density",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="per_minute",
            description="Pauses per minute of active watching.",
        ),
        "video_rewind_density": FeatureMetadata(
            name="video_rewind_density",
            display_name="Video Rewind Density",
            modality="video",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=True,
            unit="per_minute",
            description="Backward seeks per minute. Strong confusion signal.",
        ),
        "video_rewind_distance_mean_s": FeatureMetadata(
            name="video_rewind_distance_mean_s",
            display_name="Mean Rewind Distance",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Average rewind distance in seconds.",
        ),
        "video_same_segment_replay_count": FeatureMetadata(
            name="video_same_segment_replay_count",
            display_name="Same-Segment Replay Count",
            modality="video",
            tier=1,
            range_min=0.0,
            range_max=None,
            higher_means="more_confusion",
            requires_baseline=False,
            unit="count",
            description="Segments (within tolerance) viewed 3+ times.",
        ),
        "video_forward_skip_density": FeatureMetadata(
            name="video_forward_skip_density",
            display_name="Forward Skip Density",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="per_minute",
            description="Forward seeks per minute.",
        ),
        "video_forward_skip_distance_mean_s": FeatureMetadata(
            name="video_forward_skip_distance_mean_s",
            display_name="Mean Forward Skip Distance",
            modality="video",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Average forward skip distance.",
        ),
        "video_slowdown_ratio": FeatureMetadata(
            name="video_slowdown_ratio",
            display_name="Slowdown Ratio",
            modality="video",
            tier=1,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_confusion",
            requires_baseline=True,
            unit="ratio",
            description="Proportion of time at playback speed below 1x.",
        ),
        "video_speedup_ratio": FeatureMetadata(
            name="video_speedup_ratio",
            display_name="Speedup Ratio",
            modality="video",
            tier=3,
            range_min=0.0,
            range_max=1.0,
            higher_means="ambiguous",
            requires_baseline=True,
            unit="ratio",
            description="Proportion of time at playback speed above 1x.",
        ),
        "video_speed_change_count": FeatureMetadata(
            name="video_speed_change_count",
            display_name="Speed Change Count",
            modality="video",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="count",
            description="Number of playback speed changes.",
        ),
        "video_completion_ratio": FeatureMetadata(
            name="video_completion_ratio",
            display_name="Video Completion Ratio",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_engagement",
            requires_baseline=False,
            unit="ratio",
            description="Furthest position reached divided by video duration.",
        ),
        "video_effective_watch_ratio": FeatureMetadata(
            name="video_effective_watch_ratio",
            display_name="Effective Watch Ratio",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="ratio",
            description="Actual watch time divided by video duration.",
        ),
        "video_segment_coverage": FeatureMetadata(
            name="video_segment_coverage",
            display_name="Segment Coverage",
            modality="video",
            tier=2,
            range_min=0.0,
            range_max=1.0,
            higher_means="more_engagement",
            requires_baseline=False,
            unit="ratio",
            description="Proportion of unique segments actually viewed.",
        ),
        "video_pause_duration_mean_s": FeatureMetadata(
            name="video_pause_duration_mean_s",
            display_name="Mean Pause Duration",
            modality="video",
            tier=3,
            range_min=0.0,
            range_max=None,
            higher_means="ambiguous",
            requires_baseline=False,
            unit="seconds",
            description="Average duration of pause events.",
        ),
    }

class VideoFeatureExtractor(FeatureExtractor):

    _MODALITY: str = "video"
    _METADATA_REGISTRY: Dict[str, FeatureMetadata] = _build_metadata_registry()
    _MIN_EVENTS: int = 10

    def get_modality(self) -> str:
        """Return the modality identifier."""
        return self._MODALITY

    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        return dict(self._METADATA_REGISTRY)

    def get_required_event_types(self) -> List[str]:
        return [
            "video_play",
            "video_pause",
            "video_seek_backward",
            "video_seek_forward",
            "video_speed_change",
            "video_position",
            "video_end",
        ]

    def get_minimum_events(self) -> int:
        return self._MIN_EVENTS

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        if self._MODALITY not in window.modality_coverage:
            return self._build_empty_result(
                window, "No video events present in window.",
            )

        video_events = self._collect_video_events(window)
        if not video_events:
            return self._build_empty_result(
                window, "Video modality flagged but no relevant events found.",
            )

        active_watch_minutes = self._estimate_active_watch_minutes(window)
        video_duration = self._estimate_video_duration(window)
        warnings: List[str] = []

        if active_watch_minutes <= 0.0:
            warnings.append(
                "Active watch time is zero; rate-based features set to 0."
            )

        raw_features: Dict[str, float] = {}
        raw_features.update(
            self._compute_pause_metrics(window, active_watch_minutes)
        )
        raw_features.update(
            self._compute_rewind_metrics(window, active_watch_minutes)
        )
        raw_features.update(
            self._compute_forward_skip_metrics(window, active_watch_minutes)
        )
        raw_features.update(
            self._compute_replay_metrics(window)
        )
        raw_features.update(
            self._compute_speed_metrics(window)
        )
        raw_features.update(
            self._compute_completion_metrics(window, video_duration)
        )

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=len(video_events),
            warnings=warnings,
        )
    def _collect_video_events(
        self,
        window: TelemetryWindow,
    ) -> List[TelemetryEvent]:
        """
        Gather all video-related events from the window.

        Args:
            window: Source window.

        Returns:
            Flat list of all video events.
        """
        collected: List[TelemetryEvent] = []
        for event_type in self.get_required_event_types():
            collected.extend(window.events_by_type.get(event_type, []))
        return sorted(collected, key=lambda e: e.timestamp)

    def _estimate_active_watch_minutes(self, window: TelemetryWindow) -> float:
        
        play_events = window.events_by_type.get("video_play", [])
        pause_events = window.events_by_type.get("video_pause", [])
        end_events = window.events_by_type.get("video_end", [])

        if not play_events:
            # If no explicit plays, assume continuous play across window.
            return window.duration_s / _SECONDS_PER_MINUTE

        # Build interleaved play/pause boundaries.
        boundaries: List[Tuple[float, str]] = []
        for event in play_events:
            boundaries.append((event.timestamp, "play"))
        for event in pause_events:
            boundaries.append((event.timestamp, "pause"))
        for event in end_events:
            boundaries.append((event.timestamp, "pause"))
        boundaries.sort(key=lambda b: b[0])

        total_active_s = 0.0
        currently_playing = False
        play_start: float = window.start_time

        for timestamp, kind in boundaries:
            if kind == "play" and not currently_playing:
                play_start = timestamp
                currently_playing = True
            elif kind == "pause" and currently_playing:
                total_active_s += max(0.0, timestamp - play_start)
                currently_playing = False

        # If still playing at window end, accumulate remainder.
        if currently_playing:
            total_active_s += max(0.0, window.end_time - play_start)

        return total_active_s / _SECONDS_PER_MINUTE

    def _estimate_video_duration(self, window: TelemetryWindow) -> float:
        for event_type in self.get_required_event_types():
            for event in window.events_by_type.get(event_type, []):
                duration = event.payload.get("duration")
                if isinstance(duration, (int, float)) and duration > 0:
                    return float(duration)
        return 0.0

    def _compute_pause_metrics(
        self,
        window: TelemetryWindow,
        active_watch_minutes: float,
    ) -> Dict[str, float]:
        pause_events = window.events_by_type.get("video_pause", [])
        play_events = window.events_by_type.get("video_play", [])

        pause_count = len(pause_events)
        density = (
            pause_count / active_watch_minutes
            if active_watch_minutes > 0
            else 0.0
        )

        # Compute pause durations by pairing pauses with subsequent plays.
        pause_durations: List[float] = []
        play_timestamps = sorted(e.timestamp for e in play_events)
        for pause_event in pause_events:
            next_play = next(
                (t for t in play_timestamps if t > pause_event.timestamp),
                None,
            )
            if next_play is not None:
                pause_durations.append(next_play - pause_event.timestamp)

        mean_duration = (
            statistics.fmean(pause_durations) if pause_durations else 0.0
        )

        return {
            "video_pause_density": density,
            "video_pause_duration_mean_s": mean_duration,
        }

    # ------------------------------------------------------------------
    # Rewind metrics
    # ------------------------------------------------------------------

    def _compute_rewind_metrics(
        self,
        window: TelemetryWindow,
        active_watch_minutes: float,
    ) -> Dict[str, float]:
        rewind_events = window.events_by_type.get("video_seek_backward", [])

        density = (
            len(rewind_events) / active_watch_minutes
            if active_watch_minutes > 0
            else 0.0
        )

        distances: List[float] = []
        for event in rewind_events:
            from_pos = event.payload.get("from_position")
            to_pos = event.payload.get("to_position")
            if isinstance(from_pos, (int, float)) and isinstance(
                to_pos, (int, float)
            ):
                distances.append(abs(float(from_pos) - float(to_pos)))

        mean_distance = statistics.fmean(distances) if distances else 0.0

        return {
            "video_rewind_density": density,
            "video_rewind_distance_mean_s": mean_distance,
        }

    def _compute_forward_skip_metrics(
        self,
        window: TelemetryWindow,
        active_watch_minutes: float,
    ) -> Dict[str, float]:
        forward_events = window.events_by_type.get("video_seek_forward", [])

        density = (
            len(forward_events) / active_watch_minutes
            if active_watch_minutes > 0
            else 0.0
        )

        distances: List[float] = []
        for event in forward_events:
            from_pos = event.payload.get("from_position")
            to_pos = event.payload.get("to_position")
            if isinstance(from_pos, (int, float)) and isinstance(
                to_pos, (int, float)
            ):
                distances.append(max(0.0, float(to_pos) - float(from_pos)))

        mean_distance = statistics.fmean(distances) if distances else 0.0

        return {
            "video_forward_skip_density": density,
            "video_forward_skip_distance_mean_s": mean_distance,
        }

    # ------------------------------------------------------------------
    # Replay metrics
    # ------------------------------------------------------------------

    def _compute_replay_metrics(
        self,
        window: TelemetryWindow,
    ) -> Dict[str, float]:
        position_events = window.events_by_type.get("video_position", [])

        # Bucket positions and count distinct visits.
        # A "visit" is a position event that follows a gap or direction change.
        visits_by_bucket: Dict[int, int] = {}
        last_bucket: int = -1

        for event in position_events:
            position = event.payload.get("position")
            if not isinstance(position, (int, float)):
                continue
            bucket = int(float(position) / _SEGMENT_TOLERANCE_S)
            if bucket != last_bucket:
                visits_by_bucket[bucket] = visits_by_bucket.get(bucket, 0) + 1
                last_bucket = bucket

        # Also count rewinds that land in a previously-visited bucket as
        # additional visits.
        for event in window.events_by_type.get("video_seek_backward", []):
            to_pos = event.payload.get("to_position")
            if isinstance(to_pos, (int, float)):
                bucket = int(float(to_pos) / _SEGMENT_TOLERANCE_S)
                visits_by_bucket[bucket] = visits_by_bucket.get(bucket, 0) + 1

        replay_count = sum(
            1 for count in visits_by_bucket.values()
            if count >= _REPLAY_THRESHOLD
        )

        return {
            "video_same_segment_replay_count": float(replay_count),
        }

    def _compute_speed_metrics(
        self,
        window: TelemetryWindow,
    ) -> Dict[str, float]:
        speed_events = window.events_by_type.get("video_speed_change", [])
        speed_change_count = len(speed_events)

        total_duration = window.duration_s
        if total_duration <= 0:
            return {
                "video_slowdown_ratio": 0.0,
                "video_speedup_ratio": 0.0,
                "video_speed_change_count": float(speed_change_count),
            }

        # Build time segments with constant speed.
        segments: List[Tuple[float, float]] = []
        current_speed: float = 1.0
        last_timestamp: float = window.start_time

        for event in speed_events:
            new_speed = event.payload.get("speed")
            if not isinstance(new_speed, (int, float)):
                continue
            duration = max(0.0, event.timestamp - last_timestamp)
            segments.append((current_speed, duration))
            current_speed = float(new_speed)
            last_timestamp = event.timestamp

        # Final segment to window end.
        segments.append(
            (current_speed, max(0.0, window.end_time - last_timestamp))
        )

        slow_time = sum(dur for speed, dur in segments if speed < 1.0)
        fast_time = sum(dur for speed, dur in segments if speed > 1.0)

        return {
            "video_slowdown_ratio": slow_time / total_duration,
            "video_speedup_ratio": fast_time / total_duration,
            "video_speed_change_count": float(speed_change_count),
        }
    def _compute_completion_metrics(
        self,
        window: TelemetryWindow,
        video_duration: float,
    ) -> Dict[str, float]:
        position_events = window.events_by_type.get("video_position", [])
        positions: List[float] = []
        for event in position_events:
            position = event.payload.get("position")
            if isinstance(position, (int, float)):
                positions.append(float(position))

        max_position = max(positions) if positions else 0.0

        if video_duration > 0:
            completion = min(1.0, max_position / video_duration)
        else:
            completion = 0.0

        # Effective watch ratio: total time spent watching / video duration.
        # Approximate as total window duration spent in playing state.
        active_watch_s = (
            self._estimate_active_watch_minutes(window) * _SECONDS_PER_MINUTE
        )
        if video_duration > 0:
            effective_ratio = active_watch_s / video_duration
        else:
            effective_ratio = 0.0

        # Segment coverage: distinct buckets visited / total buckets in video.
        unique_buckets: set = set()
        for position in positions:
            unique_buckets.add(int(position / _SEGMENT_BUCKET_SIZE_S))
        if video_duration > 0:
            total_buckets = max(
                1,
                int(video_duration / _SEGMENT_BUCKET_SIZE_S),
            )
            coverage = min(1.0, len(unique_buckets) / total_buckets)
        else:
            coverage = 0.0

        return {
            "video_completion_ratio": completion,
            "video_effective_watch_ratio": effective_ratio,
            "video_segment_coverage": coverage,
        }