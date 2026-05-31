from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
#Prevents pipeline from crashing from floating point issues in feature calculations
EPSILON: float = 1e-9

VALID_MODALITIES: Set[str] = {
    "video",
    "scroll",
    "typing",
    "focus",
    "quiz",
    "external",
    "derived",
}


VALID_HIGHER_MEANS: Set[str] = {
    "more_confusion",
    "more_engagement",
    "more_mastery",
    "more_fatigue",
    "more_help_seeking",
    "ambiguous",
}
VALID_TIERS: Set[int] = {1, 2, 3}


VALID_MODES: Set[str] = {"learning", "assessment"}


@dataclass(frozen=True)
class FeatureMetadata:
    #Metadata describing a single feature, used for validation and interpretability.

    name: str
    display_name: str
    modality: str
    tier: int
    range_min: float
    range_max: Optional[float]
    higher_means: str
    requires_baseline: bool
    unit: str
    description: str

    def __post_init__(self) -> None:
        
        if self.modality not in VALID_MODALITIES:
            raise ValueError(
                f"Invalid modality '{self.modality}' for feature '{self.name}'. "
                f"Must be one of {sorted(VALID_MODALITIES)}."
            )
        if self.tier not in VALID_TIERS:
            raise ValueError(
                f"Invalid tier {self.tier} for feature '{self.name}'. "
                f"Must be one of {sorted(VALID_TIERS)}."
            )
        if self.higher_means not in VALID_HIGHER_MEANS:
            raise ValueError(
                f"Invalid higher_means '{self.higher_means}' for feature "
                f"'{self.name}'. Must be one of {sorted(VALID_HIGHER_MEANS)}."
            )
        if self.range_max is not None and self.range_max < self.range_min:
            raise ValueError(
                f"range_max ({self.range_max}) < range_min ({self.range_min}) "
                f"for feature '{self.name}'."
            )


@dataclass
class TelemetryEvent:
    

    event_type: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        
        if not isinstance(self.event_type, str) or not self.event_type:
            raise ValueError("event_type must be a non-empty string.")
        if not isinstance(self.timestamp, (int, float)):
            raise TypeError(
                f"timestamp must be numeric, got {type(self.timestamp).__name__}."
            )
        if math.isnan(self.timestamp) or math.isinf(self.timestamp):
            raise ValueError("timestamp must be a finite number.")


@dataclass
class TelemetryWindow:
    

    window_id: str
    start_time: float
    end_time: float
    events: List[TelemetryEvent]
    events_by_type: Dict[str, List[TelemetryEvent]]
    session_id: str
    user_id: str
    content_type: str
    content_id: str
    mode: str
    modality_coverage: Set[str]

    def __post_init__(self) -> None:
        
        if self.end_time < self.start_time:
            raise ValueError(
                f"Window end_time ({self.end_time}) < start_time ({self.start_time})."
            )
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{self.mode}'. Must be one of {sorted(VALID_MODES)}."
            )

    @property
    def duration_s(self) -> float:
        """Window duration in seconds."""
        return self.end_time - self.start_time

    @property
    def event_count(self) -> int:
        """Total number of events in this window."""
        return len(self.events)


@dataclass
class FeatureResult:
    

    features: Dict[str, float]
    metadata: Dict[str, FeatureMetadata]
    quality: Dict[str, float]
    missing: List[str]
    modality: str
    window_id: str
    event_count: int
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        
        if self.modality not in VALID_MODALITIES:
            raise ValueError(
                f"Invalid modality '{self.modality}'. "
                f"Must be one of {sorted(VALID_MODALITIES)}."
            )
        # Every present feature must have metadata and quality.
        for feature_name in self.features:
            if feature_name not in self.metadata:
                raise ValueError(
                    f"Feature '{feature_name}' has no metadata entry."
                )
            if feature_name not in self.quality:
                raise ValueError(
                    f"Feature '{feature_name}' has no quality score."
                )

        for feature_name, quality_score in self.quality.items():
            if (
                not isinstance(quality_score, (int, float))
                or not 0.0 <= quality_score <= 1.0
            ):
                raise ValueError(
                    f"Feature '{feature_name}' has invalid quality score "
                    f"{quality_score}. Must be in [0.0, 1.0]."
                )

    def is_empty(self) -> bool:
        """Return True if no features were successfully computed."""
        return len(self.features) == 0


def validate_feature_value(
    value: float,
    metadata: FeatureMetadata,
) -> Tuple[float, List[str]]:
    
    warnings: List[str] = []

    if math.isnan(value):
        warnings.append(
            f"Feature '{metadata.name}' produced NaN; replaced with range_min."
        )
        return metadata.range_min, warnings

    if math.isinf(value):
        warnings.append(
            f"Feature '{metadata.name}' produced Inf; replaced with range bound."
        )
        return (
            metadata.range_max if value > 0 and metadata.range_max is not None
            else metadata.range_min,
            warnings,
        )

    if value < metadata.range_min:
        warnings.append(
            f"Feature '{metadata.name}' value {value} below range_min "
            f"{metadata.range_min}; clamped."
        )
        return metadata.range_min, warnings

    if metadata.range_max is not None and value > metadata.range_max:
        warnings.append(
            f"Feature '{metadata.name}' value {value} above range_max "
            f"{metadata.range_max}; clamped."
        )
        return metadata.range_max, warnings

    return value, warnings


def compute_quality_score(event_count: int, min_events: int) -> float:
    
    if min_events <= 0:
        return 1.0
    if event_count <= 0:
        return 0.0
    return min(1.0, event_count / min_events)


class FeatureExtractor(ABC):
    

    @abstractmethod
    def extract(self, window: TelemetryWindow) -> FeatureResult:
        """
        Compute all features for this modality from the given window.

        """

    @abstractmethod
    def get_feature_metadata(self) -> Dict[str, FeatureMetadata]:
        """
        Return metadata for every feature this extractor can produce.

        """

    @abstractmethod
    def get_required_event_types(self) -> List[str]:
        """
        Return the list of event types this extractor needs to function.

        """

    @abstractmethod
    def get_minimum_events(self) -> int:
        """
        Return the minimum number of relevant events for a reliable estimate.
        """

    @abstractmethod
    def get_modality(self) -> str:
        """
        Return the modality identifier for this extractor.
        """

    def _build_empty_result(
        self,
        window: TelemetryWindow,
        reason: str,
    ) -> FeatureResult:
        
        metadata = self.get_feature_metadata()
        return FeatureResult(
            features={},
            metadata={},
            quality={},
            missing=list(metadata.keys()),
            modality=self.get_modality(),
            window_id=window.window_id,
            event_count=0,
            warnings=[reason],
        )

    def _build_result(
        self,
        window: TelemetryWindow,
        raw_features: Dict[str, float],
        event_count: int,
        warnings: Optional[List[str]] = None,
    ) -> FeatureResult:
        
    
        metadata_registry = self.get_feature_metadata()
        min_events = self.get_minimum_events()
        quality_score = compute_quality_score(event_count, min_events)

        validated_features: Dict[str, float] = {}
        validated_metadata: Dict[str, FeatureMetadata] = {}
        quality_map: Dict[str, float] = {}
        all_warnings: List[str] = list(warnings) if warnings else []
        missing: List[str] = []

        for feature_name, feature_metadata in metadata_registry.items():
            if feature_name not in raw_features:
                missing.append(feature_name)
                continue

            raw_value = float(raw_features[feature_name])
            validated_value, value_warnings = validate_feature_value(
                raw_value, feature_metadata,
            )
            validated_features[feature_name] = validated_value
            validated_metadata[feature_name] = feature_metadata
            quality_map[feature_name] = quality_score
            all_warnings.extend(value_warnings)

        return FeatureResult(
            features=validated_features,
            metadata=validated_metadata,
            quality=quality_map,
            missing=missing,
            modality=self.get_modality(),
            window_id=window.window_id,
            event_count=event_count,
            warnings=all_warnings,
        )
