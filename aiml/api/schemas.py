from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class Event(BaseModel):
    event_type: str
    timestamp: int
    payload: dict[str, Any]


class PredictRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    events: list[Event]


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
