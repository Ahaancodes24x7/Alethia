from __future__ import annotations

import statistics

from .base import (
    EPSILON,
    FeatureExtractor,
    FeatureMetadata,
    FeatureResult,
    TelemetryEvent,
    TelemetryWindow,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSESSMENT_MODE: str = "assessment"
"""Window mode under which external hint features are computed."""

DOMAIN_CATEGORY_LLM: str = "llm"
DOMAIN_CATEGORY_SEARCH: str = "search"
DOMAIN_CATEGORY_REFERENCE: str = "reference"

HELP_SEEKING_WEIGHT_LLM: float = 1.0
HELP_SEEKING_WEIGHT_REFERENCE: float = 0.5
HELP_SEEKING_WEIGHT_SEARCH: float = 0.3

BORROWED_KNOWLEDGE_HELP_THRESHOLD: float = 0.5
BORROWED_KNOWLEDGE_SCORE_THRESHOLD: float = 0.7

# External Hint Feature Extractor

class ExternalHintFeatureExtractor(FeatureExtractor):
    

    @property
    def modality(self) -> str:
        """Modality identifier."""
        return "external"

    def get_modality(self) -> str:
        """Return the modality identifier."""
        return self.modality

    def get_required_event_types(self) -> list[str]:
        """Event types consumed by this extractor."""
        return [
            "external_tab_open",
            "external_tab_close",
            "answer_submit",
            "quiz_start",
            "quiz_end",
        ]

    def get_minimum_events(self) -> int:
        """Minimum events for reliable extraction."""
        return 1

    def get_feature_metadata(self) -> dict[str, FeatureMetadata]:
        """Return metadata for all 10 external assistance features."""
        return {
            "external_reference_count": FeatureMetadata(
                name="external_reference_count",
                display_name="External Reference Count",
                modality="external",
                tier=2,
                range_min=0.0,
                range_max=None,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="count",
                description=(
                    "Total external tab opens during assessment."
                ),
            ),
            "external_llm_reference_count": FeatureMetadata(
                name="external_llm_reference_count",
                display_name="LLM Reference Count",
                modality="external",
                tier=2,
                range_min=0.0,
                range_max=None,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="count",
                description="Opens to LLM domains during assessment.",
            ),
            "external_search_reference_count": FeatureMetadata(
                name="external_search_reference_count",
                display_name="Search Reference Count",
                modality="external",
                tier=3,
                range_min=0.0,
                range_max=None,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="count",
                description="Opens to search engines during assessment.",
            ),
            "external_reference_site_count": FeatureMetadata(
                name="external_reference_site_count",
                display_name="Reference Site Count",
                modality="external",
                tier=3,
                range_min=0.0,
                range_max=None,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="count",
                description=(
                    "Opens to documentation/reference sites during "
                    "assessment."
                ),
            ),
            "external_time_ratio": FeatureMetadata(
                name="external_time_ratio",
                display_name="External Time Ratio",
                modality="external",
                tier=2,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="ratio",
                description=(
                    "Fraction of assessment time spent on external tabs."
                ),
            ),
            "external_llm_time_ratio": FeatureMetadata(
                name="external_llm_time_ratio",
                display_name="LLM Time Ratio",
                modality="external",
                tier=3,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="ratio",
                description=(
                    "Fraction of assessment time spent on LLM tabs."
                ),
            ),
            "external_mean_duration_s": FeatureMetadata(
                name="external_mean_duration_s",
                display_name="Mean External Visit Duration",
                modality="external",
                tier=3,
                range_min=0.0,
                range_max=None,
                higher_means="ambiguous",
                requires_baseline=False,
                unit="seconds",
                description="Average time per external resource visit.",
            ),
            "external_before_answer_rate": FeatureMetadata(
                name="external_before_answer_rate",
                display_name="External-Before-Answer Rate",
                modality="external",
                tier=2,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="ratio",
                description=(
                    "Fraction of answers preceded by external lookups."
                ),
            ),
            "external_help_seeking_index": FeatureMetadata(
                name="external_help_seeking_index",
                display_name="Help-Seeking Index",
                modality="external",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="ratio",
                description=(
                    "Weighted composite of help-seeking signals."
                ),
            ),
            "external_borrowed_knowledge_flag": FeatureMetadata(
                name="external_borrowed_knowledge_flag",
                display_name="Borrowed Knowledge Flag",
                modality="external",
                tier=1,
                range_min=0.0,
                range_max=1.0,
                higher_means="more_help_seeking",
                requires_baseline=False,
                unit="indicator",
                description=(
                    "1 when help-seeking is high and quiz score is high "
                    "(indicates externally-acquired correctness)."
                ),
            ),
        }

    def extract(self, window: TelemetryWindow) -> FeatureResult:
        if window.mode != ASSESSMENT_MODE:
            return self._build_inactive_result(
                window, "session not in assessment mode"
            )

        tab_open_events = window.events_by_type.get("external_tab_open", [])
        tab_close_events = window.events_by_type.get("external_tab_close", [])
        submit_events = window.events_by_type.get("answer_submit", [])

        if not tab_open_events:
            return self._build_zero_result(window)

        event_count = self._count_relevant_events(window)

        category_counts = self._count_by_category(tab_open_events)
        durations_by_category = self._compute_durations_by_category(
            tab_open_events, tab_close_events, window.end_time
        )
        time_ratios = self._compute_time_ratios(
            durations_by_category, window.duration_s
        )
        before_answer_rate = self._compute_before_answer_rate(
            tab_open_events, submit_events
        )
        mean_duration = self._compute_mean_duration(durations_by_category)
        help_index = self._compute_help_seeking_index(
            category_counts, len(submit_events)
        )
        borrowed_flag = self._detect_borrowed_knowledge(
            help_index, submit_events
        )

        raw_features: dict[str, float] = {
            "external_reference_count": float(
                category_counts["total"]
            ),
            "external_llm_reference_count": float(
                category_counts[DOMAIN_CATEGORY_LLM]
            ),
            "external_search_reference_count": float(
                category_counts[DOMAIN_CATEGORY_SEARCH]
            ),
            "external_reference_site_count": float(
                category_counts[DOMAIN_CATEGORY_REFERENCE]
            ),
            "external_time_ratio": time_ratios["total"],
            "external_llm_time_ratio": time_ratios[DOMAIN_CATEGORY_LLM],
            "external_mean_duration_s": mean_duration,
            "external_before_answer_rate": before_answer_rate,
            "external_help_seeking_index": help_index,
            "external_borrowed_knowledge_flag": borrowed_flag,
        }

        return self._build_result(
            window=window,
            raw_features=raw_features,
            event_count=event_count,
        )

    # Internal computation helper

    def _count_relevant_events(self, window: TelemetryWindow) -> int:
        return sum(
            len(window.events_by_type.get(event_type, []))
            for event_type in self.get_required_event_types()
        )

    def _build_zero_result(self, window: TelemetryWindow) -> FeatureResult:
        metadata = self.get_feature_metadata()
        zero_features = {name: 0.0 for name in metadata}
        quality = {name: 1.0 for name in metadata}
        return FeatureResult(
            features=zero_features,
            metadata=metadata,
            quality=quality,
            missing=[],
            modality=self.modality,
            event_count=0,
            warnings=[],
            window_id=window.window_id,
        )

    def _build_inactive_result(
        self,
        window: TelemetryWindow,
        reason: str,
    ) -> FeatureResult:
        return self._build_empty_result(window, reason)

    @staticmethod
    def _count_by_category(
        tab_open_events: list[TelemetryEvent],
    ) -> dict[str, int]:
        counts: dict[str, int] = {
            DOMAIN_CATEGORY_LLM: 0,
            DOMAIN_CATEGORY_SEARCH: 0,
            DOMAIN_CATEGORY_REFERENCE: 0,
            "total": 0,
        }
        for event in tab_open_events:
            category = event.payload.get("domain_category")
            if not isinstance(category, str):
                continue
            counts["total"] += 1
            if category in counts:
                counts[category] += 1
        return counts

    @staticmethod
    def _compute_durations_by_category(
        open_events: list[TelemetryEvent],
        close_events: list[TelemetryEvent],
        window_end_time: float,
    ) -> dict[str, list[float]]:
        sorted_opens = sorted(open_events, key=lambda e: e.timestamp)
        sorted_closes = sorted(close_events, key=lambda e: e.timestamp)
        durations: dict[str, list[float]] = {
            DOMAIN_CATEGORY_LLM: [],
            DOMAIN_CATEGORY_SEARCH: [],
            DOMAIN_CATEGORY_REFERENCE: [],
            "total": [],
        }
        close_pointer = 0

        for opener in sorted_opens:
            category = opener.payload.get("domain_category")
            if not isinstance(category, str):
                continue
            while (
                close_pointer < len(sorted_closes)
                and sorted_closes[close_pointer].timestamp <= opener.timestamp
            ):
                close_pointer += 1
            if close_pointer < len(sorted_closes):
                duration = (
                    sorted_closes[close_pointer].timestamp - opener.timestamp
                )
                close_pointer += 1
            else:
                duration = window_end_time - opener.timestamp
            if duration <= 0:
                duration = 0.0
            durations["total"].append(duration)
            if category in durations:
                durations[category].append(duration)
        return durations

    @staticmethod
    def _compute_time_ratios(
        durations_by_category: dict[str, list[float]],
        window_duration_s: float,
    ) -> dict[str, float]:
        if window_duration_s <= 0:
            return {
                "total": 0.0,
                DOMAIN_CATEGORY_LLM: 0.0,
            }
        total_time = sum(durations_by_category.get("total", []))
        llm_time = sum(
            durations_by_category.get(DOMAIN_CATEGORY_LLM, [])
        )
        return {
            "total": min(total_time / window_duration_s, 1.0),
            DOMAIN_CATEGORY_LLM: min(llm_time / window_duration_s, 1.0),
        }

    @staticmethod
    def _compute_mean_duration(
        durations_by_category: dict[str, list[float]],
    ) -> float:
        
        all_durations = durations_by_category.get("total", [])
        if not all_durations:
            return 0.0
        return statistics.fmean(all_durations)

    @staticmethod
    def _compute_before_answer_rate(
        tab_open_events: list[TelemetryEvent],
        submit_events: list[TelemetryEvent],
    ) -> float:
        
        if not submit_events:
            return 0.0
        sorted_opens = sorted(tab_open_events, key=lambda e: e.timestamp)
        if not sorted_opens:
            return 0.0

        preceded_count = 0
        for submit in submit_events:
            for opener in sorted_opens:
                if 0 < submit.timestamp - opener.timestamp <= 300.0:
                    preceded_count += 1
                    break
                if opener.timestamp > submit.timestamp:
                    break
        return preceded_count / len(submit_events)

    @staticmethod
    def _compute_help_seeking_index(
        category_counts: dict[str, int],
        question_count: int,
    ) -> float:
        
        weighted = (
            HELP_SEEKING_WEIGHT_LLM
            * category_counts.get(DOMAIN_CATEGORY_LLM, 0)
            + HELP_SEEKING_WEIGHT_REFERENCE
            * category_counts.get(DOMAIN_CATEGORY_REFERENCE, 0)
            + HELP_SEEKING_WEIGHT_SEARCH
            * category_counts.get(DOMAIN_CATEGORY_SEARCH, 0)
        )
        normalization = max(question_count, 1) * 2.0
        return min(weighted / max(normalization, EPSILON), 1.0)

    @staticmethod
    def _detect_borrowed_knowledge(
        help_seeking_index: float,
        submit_events: list[TelemetryEvent],
    ) -> float:
        
        if help_seeking_index < BORROWED_KNOWLEDGE_HELP_THRESHOLD:
            return 0.0
        if not submit_events:
            return 0.0
        latest_per_question: dict[str, TelemetryEvent] = {}
        for event in sorted(submit_events, key=lambda e: e.timestamp):
            qid = event.payload.get("question_id")
            if isinstance(qid, str):
                latest_per_question[qid] = event
        if not latest_per_question:
            return 0.0
        correct_count = sum(
            1
            for e in latest_per_question.values()
            if bool(e.payload.get("is_correct"))
        )
        score = correct_count / len(latest_per_question)
        return 1.0 if score > BORROWED_KNOWLEDGE_SCORE_THRESHOLD else 0.0
