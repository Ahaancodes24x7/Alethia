from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EventInput(BaseModel):
    event_type: str
    timestamp: int | float
    payload: dict[str, Any]


class PredictionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    features: Optional[dict[str, Any]] = None
    events: Optional[list[EventInput]] = None
    user_id: str = "anonymous"
    content_id: str = "unknown"
    content_type: str = "general"
    learning_mode: str = "learning"


PredictRequest = PredictionRequest


class PredictResponse(BaseModel):
    session_id: str
    overall_learning_score: int
    learning_state: str
    confidence: float
    metrics: dict[str, Any]
    risks: list[str]
    recommendations: list[str]
    model_outputs: dict[str, Any]
    rule_engine: dict[str, Any]
