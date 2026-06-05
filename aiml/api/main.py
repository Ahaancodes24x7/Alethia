from __future__ import annotations

import uuid
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException

from aiml.api.schemas import EventInput, PredictionRequest, PredictResponse
from aiml.features import FeaturePipeline, TelemetryEvent, TelemetryWindow
from aiml.features.windowing import compute_modality_coverage, group_events_by_type
from aiml.inference.predict import predict_learning_state
from aiml.models.comprehension_gbm.config import MODEL_PATH as COMPREHENSION_MODEL_PATH
from aiml.models.fatigue_xgb.config import MODEL_PATH as FATIGUE_MODEL_PATH
from aiml.models.retention_xgb.config import MODEL_PATH as RETENTION_MODEL_PATH


app = FastAPI(title="ALETHIA AIML", version="1.0.0")
feature_pipeline = FeaturePipeline()

_EVENT_TYPE_ALIASES = {
    "SCROLL": "scroll",
    "VIDEO": "video_position",
    "FOCUS": "focus_gain",
    "TYPING": "keydown",
    "QUIZ": "answer_submit",
}


def _artifact_state(path) -> str:
    return "loaded" if path.exists() else "missing"


def _build_telemetry_window(request: PredictionRequest) -> TelemetryWindow:
    events = _convert_events(request.events or [])
    if not events:
        raise ValueError("events must contain at least one valid telemetry event.")

    sorted_events = sorted(events, key=lambda event: event.timestamp)
    start_time = sorted_events[0].timestamp
    end_time = max(sorted_events[-1].timestamp, start_time + 1.0)
    mode = request.learning_mode if request.learning_mode in {"learning", "assessment"} else "learning"

    return TelemetryWindow(
        window_id=str(uuid.uuid4()),
        start_time=start_time,
        end_time=end_time,
        events=sorted_events,
        events_by_type=group_events_by_type(sorted_events),
        session_id=request.session_id,
        user_id=request.user_id or "anonymous",
        content_type=request.content_type or "general",
        content_id=request.content_id or "unknown",
        mode=mode,
        modality_coverage=compute_modality_coverage(sorted_events),
    )


def _convert_events(events: Iterable[EventInput]) -> list[TelemetryEvent]:
    telemetry_events: list[TelemetryEvent] = []
    for event in events:
        if not isinstance(event.payload, dict):
            raise ValueError(f"payload for event_type '{event.event_type}' must be an object.")
        telemetry_events.extend(_expand_backend_event(event))
    return telemetry_events


def _expand_backend_event(event: EventInput) -> list[TelemetryEvent]:
    event_type = _canonical_event_type(event.event_type)
    payload = _normalize_payload(event_type, event.payload)
    timestamp = float(event.timestamp)

    if event_type == "focus_gain" and event.event_type.strip().upper() == "FOCUS":
        return _focus_events(timestamp, payload)
    if event_type == "video_position" and event.event_type.strip().upper() == "VIDEO":
        return _video_events(timestamp, payload)
    if event_type == "keydown" and event.event_type.strip().upper() == "TYPING":
        return _typing_events(timestamp, payload)
    if event_type == "answer_submit" and event.event_type.strip().upper() == "QUIZ":
        return _quiz_events(timestamp, payload)

    return [TelemetryEvent(event_type=event_type, timestamp=timestamp, payload=payload)]


def _canonical_event_type(event_type: str) -> str:
    stripped = event_type.strip()
    return _EVENT_TYPE_ALIASES.get(stripped.upper(), stripped.lower())


def _normalize_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    if event_type == "scroll":
        if "scroll_y" not in normalized and "scroll_position" in normalized:
            normalized["scroll_y"] = normalized["scroll_position"]
        if "delta_y" not in normalized and "scroll_delta" in normalized:
            normalized["delta_y"] = normalized["scroll_delta"]
        if "document_height" not in normalized:
            position = normalized.get("scroll_y")
            if isinstance(position, (int, float)) and position > 0:
                normalized["document_height"] = max(float(position), 1.0)

    if event_type == "video_position":
        if "position" not in normalized and "watch_time" in normalized:
            normalized["position"] = normalized["watch_time"]
        if "duration" not in normalized and "watch_time" in normalized and "completion_ratio" in normalized:
            try:
                completion = float(normalized["completion_ratio"])
                if completion > 0:
                    normalized["duration"] = float(normalized["watch_time"]) / completion
            except (TypeError, ValueError):
                pass

    if event_type == "answer_submit":
        if "is_correct" not in normalized and "correctness" in normalized:
            normalized["is_correct"] = normalized["correctness"]
        if "attempt_number" not in normalized and "attempts" in normalized:
            normalized["attempt_number"] = normalized["attempts"]
        normalized.setdefault("question_id", "q1")

    return normalized


def _focus_events(timestamp: float, payload: dict[str, Any]) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    inactive_time = _positive_float(payload.get("inactive_time"))
    active_time = _positive_float(payload.get("active_time"))
    tab_switches = int(_positive_float(payload.get("tab_switches"), 0.0))

    if inactive_time > 0:
        events.append(TelemetryEvent("focus_loss", timestamp, payload))
        events.append(TelemetryEvent("focus_gain", timestamp + inactive_time, payload))
    elif active_time > 0:
        events.append(TelemetryEvent("focus_gain", timestamp, payload))

    for index in range(tab_switches):
        events.append(TelemetryEvent("tab_switch", timestamp + index, payload))

    return events or [TelemetryEvent("focus_gain", timestamp, payload)]


def _video_events(timestamp: float, payload: dict[str, Any]) -> list[TelemetryEvent]:
    events = [TelemetryEvent("video_position", timestamp, payload)]
    pause_count = int(_positive_float(payload.get("pause_count"), 0.0))
    rewind_count = int(_positive_float(payload.get("rewind_count"), 0.0))
    watch_time = _positive_float(payload.get("watch_time"), 0.0)

    for index in range(pause_count):
        events.append(TelemetryEvent("video_pause", timestamp + index + 0.1, payload))
    for index in range(rewind_count):
        seek_payload = {
            **payload,
            "from_position": watch_time,
            "to_position": max(0.0, watch_time - 10.0),
        }
        events.append(TelemetryEvent("video_seek_backward", timestamp + index + 0.2, seek_payload))
    return events


def _typing_events(timestamp: float, payload: dict[str, Any]) -> list[TelemetryEvent]:
    key_latency = _positive_float(payload.get("key_latency"), 0.2)
    typing_speed = _positive_float(payload.get("typing_speed"), 0.0)
    key_count = max(2, min(20, int(typing_speed / 60) if typing_speed > 0 else 2))
    events: list[TelemetryEvent] = []
    for index in range(key_count):
        keydown_timestamp = timestamp + index * key_latency
        events.append(TelemetryEvent("keydown", keydown_timestamp, payload))
        events.append(TelemetryEvent("keyup", keydown_timestamp + min(key_latency / 2, 0.2), payload))
    return events


def _quiz_events(timestamp: float, payload: dict[str, Any]) -> list[TelemetryEvent]:
    normalized = _normalize_payload("answer_submit", payload)
    return [
        TelemetryEvent("question_display", max(0.0, timestamp - 1.0), normalized),
        TelemetryEvent("answer_submit", timestamp, normalized),
    ]


def _positive_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, number)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "ALETHIA AIML",
        "status": "running",
    }


@app.get("/health")
def health() -> dict:
    models = {
        "comprehension": _artifact_state(COMPREHENSION_MODEL_PATH),
        "fatigue": _artifact_state(FATIGUE_MODEL_PATH),
        "retention": _artifact_state(RETENTION_MODEL_PATH),
    }
    status = "healthy" if all(state == "loaded" for state in models.values()) else "unhealthy"
    return {
        "status": status,
        "models": models,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictionRequest) -> dict:
    if request.features is not None:
        feature_input = request.features
    elif request.events is not None:
        if not request.events:
            raise HTTPException(status_code=422, detail="events must not be empty.")
        try:
            window = _build_telemetry_window(request)
            feature_input = feature_pipeline.extract_all(window)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Feature extraction failed: {exc}",
            ) from exc
    else:
        raise HTTPException(
            status_code=422,
            detail="Request must include either features or events.",
        )

    try:
        result = predict_learning_state(feature_input)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed: {exc}",
        ) from exc

    return {
        "session_id": request.session_id,
        "overall_learning_score": result["overall_learning_score"],
        "learning_state": result["learning_state"],
        "confidence": result["confidence"],
        "metrics": result["cognitive_metrics"],
        "risks": result["risks"],
        "recommendations": result["recommendations"],
        "model_outputs": result["model_outputs"],
        "rule_engine": result["rule_engine"],
    }
