from __future__ import annotations

from fastapi import FastAPI, HTTPException

from aiml.api.schemas import PredictRequest, PredictResponse
from aiml.inference.predict import predict_learning_state
from aiml.models.comprehension_gbm.config import MODEL_PATH as COMPREHENSION_MODEL_PATH
from aiml.models.fatigue_xgb.config import MODEL_PATH as FATIGUE_MODEL_PATH
from aiml.models.retention_xgb.config import MODEL_PATH as RETENTION_MODEL_PATH


app = FastAPI(title="ALETHIA AIML", version="1.0.0")


def _artifact_state(path) -> str:
    return "loaded" if path.exists() else "missing"


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
def predict(request: PredictRequest) -> dict:
    try:
        result = predict_learning_state(request.features)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
