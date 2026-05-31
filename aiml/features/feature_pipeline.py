from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .base import FeatureExtractor, FeatureMetadata, FeatureResult, TelemetryWindow
from .derived_features import DerivedFeatureExtractor, SessionContext, UserBaseline
from .external_hint_features import ExternalHintFeatureExtractor
from .focus_features import FocusFeatureExtractor
from .quiz_features import QuizFeatureExtractor
from .scroll_features import ScrollFeatureExtractor
from .typing_features import TypingFeatureExtractor
from .video_features import VideoFeatureExtractor


class FeaturePipeline:

    _MODALITY: str = "derived"

    def __init__(
        self,
        extractors: Optional[Iterable[FeatureExtractor]] = None,
        derived_extractor: Optional[DerivedFeatureExtractor] = None,
    ) -> None:
        
        self.extractors: Dict[str, FeatureExtractor] = {}
        self.warnings: List[str] = []
        self.derived_extractor = (
            derived_extractor
            if derived_extractor is not None
            else DerivedFeatureExtractor()
        )

        default_extractors: Iterable[FeatureExtractor] = (
            extractors if extractors is not None else self._build_default_extractors()
        )
        for extractor in default_extractors:
            self.register_extractor(extractor)

    def register_extractor(self, extractor: FeatureExtractor) -> None:
        self.extractors[extractor.get_modality()] = extractor

    def run_modality_extractors(
        self,
        window: TelemetryWindow,
    ) -> Dict[str, FeatureResult]:
        results: Dict[str, FeatureResult] = {}
        for modality, extractor in self.extractors.items():
            try:
                results[modality] = extractor.extract(window)
            except Exception as exc:
                self.warnings.append(
                    f"{extractor.__class__.__name__} failed for modality "
                    f"'{modality}': {type(exc).__name__}: {exc}"
                )
        return results

    def run_derived_extractor(
        self,
        modality_results: Dict[str, FeatureResult],
        baseline: Optional[UserBaseline] = None,
        context: Optional[SessionContext] = None,
        window_id: Optional[str] = None,
    ) -> FeatureResult:
        
        return self.derived_extractor.extract(
            modality_results=modality_results,
            baseline=baseline,
            context=context,
            window_id=window_id,
        )

    def merge_features(
        self,
        modality_results: Dict[str, FeatureResult],
        derived_result: FeatureResult,
        window: TelemetryWindow,
    ) -> FeatureResult:
        
        features: Dict[str, float] = {}
        metadata: Dict[str, FeatureMetadata] = {}
        quality: Dict[str, float] = {}
        missing: List[str] = []
        warnings: List[str] = []
        event_count = 0

        for result in list(modality_results.values()) + [derived_result]:
            features.update(result.features)
            metadata.update(result.metadata)
            quality.update(result.quality)
            missing.extend(result.missing)
            warnings.extend(result.warnings)
            event_count += result.event_count
        warnings.extend(self.warnings)

        return FeatureResult(
            features=features,
            metadata=metadata,
            quality=quality,
            missing=missing,
            modality=self._MODALITY,
            window_id=window.window_id,
            event_count=event_count,
            warnings=warnings,
        )

    def extract_all(
        self,
        window: TelemetryWindow,
        baseline: Optional[UserBaseline] = None,
        context: Optional[SessionContext] = None,
    ) -> FeatureResult:
        
        self.warnings = []
        modality_results = self.run_modality_extractors(window)
        derived_result = self.run_derived_extractor(
            modality_results=modality_results,
            baseline=baseline,
            context=context,
            window_id=window.window_id,
        )
        return self.merge_features(modality_results, derived_result, window)

    def _build_default_extractors(self) -> List[FeatureExtractor]:
        
        return [
            VideoFeatureExtractor(),
            ScrollFeatureExtractor(),
            TypingFeatureExtractor(),
            FocusFeatureExtractor(),
            QuizFeatureExtractor(),
            ExternalHintFeatureExtractor(),
        ]
