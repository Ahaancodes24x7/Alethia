# ALETHIA

## Measuring Understanding, Not Just Activity

### The Problem

Every year, millions of students spend thousands of hours watching lectures, attending classes, reading notes, and solving assignments. Modern learning platforms can tell us how long a student watched a video, how many modules were completed, or how many quizzes were attempted. However, they fail to answer the most important question in education:

**Did the student actually understand what they were learning?**

A learner may complete a two-hour lecture and still remain confused about the core concept. This confusion often remains invisible until an examination, interview, coding assessment, or real-world application exposes the gap.

Current educational technology measures engagement. ALETHIA measures understanding.

---

## What is ALETHIA?

ALETHIA is an AI-powered Comprehension Intelligence Platform designed to identify cognitive drift, learning fatigue, attention loss, confidence mismatches, and comprehension breakdowns in real time.

Instead of relying solely on assessment scores or completion rates, ALETHIA analyzes behavioral learning signals to estimate a learner's actual understanding while the learning process is taking place.

The platform continuously observes how students interact with educational content and transforms those interactions into meaningful cognitive insights.

Rather than asking:

*"Did the student complete the lesson?"*

ALETHIA asks:

*"Did the student understand the lesson?"*

---

## The Core Idea

A student begins a learning session by defining a goal.

Examples include:

* Learn Dynamic Programming
* Practice Binary Trees
* Study Operating Systems
* Prepare for an upcoming examination
* Complete a Machine Learning module

ALETHIA then monitors the learning session through behavioral telemetry collected from educational resources such as YouTube, Coursera, NPTEL, GeeksForGeeks, LeetCode, university learning management systems, and other digital learning environments.

During the session, ALETHIA analyzes:

* Video rewinds and pauses
* Scroll patterns and reading behavior
* Typing dynamics and interaction rhythms
* Focus changes and tab switching
* Assessment performance
* Confidence ratings
* Hint dependency and external assistance patterns

These signals collectively provide a behavioral fingerprint of the learner's cognitive state.

---

## How ALETHIA Works

### Stage 1 — Behavioral Telemetry Collection

ALETHIA collects learning interaction data from the browser environment while respecting user privacy.

Examples include:

* Video replay frequency
* Pause density
* Focus loss events
* Scroll reversals
* Typing consistency
* Quiz attempts
* Hint usage

These raw events form the foundation of the cognitive analysis pipeline.

---

### Stage 2 — Feature Engineering Layer

Raw behavioral events are transformed into structured learning indicators.

ALETHIA currently generates a rich set of behavioral features including:

* Video Rewind Density
* Focus Loss Ratio
* Attention Stability Score
* Typing Instability
* Confidence Gap
* Productive Struggle Score
* Hint Dependency
* Learning Persistence Indicators

This layer transforms millions of low-level interactions into meaningful educational signals.

---

### Stage 3 — Cognitive Rule Engine

The Rule Engine acts as ALETHIA's first reasoning layer.

Using explainable behavioral rules, it identifies patterns such as:

* Cognitive Drift
* Attention Dropout
* Learning Fatigue
* Panic Guessing
* Confidence Mismatch
* Repeated Concept Confusion

Unlike black-box AI systems, every conclusion produced by the Rule Engine can be explained and traced back to observable learner behavior.

---

### Stage 4 — Machine Learning Intelligence

ALETHIA uses multiple AI models working together to build a comprehensive understanding of the learner.

#### Comprehension Model (LightGBM)

Predicts:

* Understanding Confidence
* Learning Success Probability
* Concept Assimilation Strength

#### Fatigue Detection Network

Identifies:

* Cognitive Overload
* Mental Fatigue
* Declining Attention Capacity

using behavioral and interaction patterns.

#### Knowledge Tracing Engine

Tracks:

* Concept Mastery
* Learning Progression
* Topic-Level Understanding

over time.

#### Retention Prediction Engine

Estimates:

* Knowledge Retention
* Forgetting Risk
* Revision Requirements

before performance declines.

---

### Stage 5 — Adaptive Intervention Layer

Most systems stop after identifying a problem.

ALETHIA goes further.

When learning difficulties are detected, ALETHIA generates personalized interventions such as:

* Concept Checkpoints
* Recovery Quizzes
* Revision Suggestions
* Learning Summaries
* Difficulty Adjustments
* Break Recommendations

The objective is not simply to diagnose confusion, but to help learners recover from it.

---

## Why ALETHIA Is Different

Traditional Platforms Measure:

* Time Spent
* Attendance
* Completion Rate
* Quiz Scores

ALETHIA Measures:

* Understanding
* Cognitive Drift
* Productive Struggle
* Fatigue
* Attention Stability
* Retention Risk
* Confidence Alignment

This transforms learning from a passive content-consumption process into an intelligent feedback system.

---

## AIML Intelligence Layer

### Overview

ALETHIA AIML converts behavioral telemetry into cognitive intelligence. Raw learning activity is transformed into 89 cognitive and behavioral features, evaluated by specialized models, checked by an explainable rule engine, and fused into a backend-ready learning-state response.

### Architecture

```text
Browser Extension / Frontend
        |
        v
Backend
        |
        v
FastAPI AIML Service
        |
        v
Raw telemetry event adapter
        |
        v
FeaturePipeline.extract_all()
        |
        v
89 engineered cognitive features
        |
        v
LightGBM Comprehension + XGBoost Fatigue + XGBoost Retention
        |
        v
Fusion Layer + Rule Engine
        |
        v
Backend-ready learning report
```

### Feature Engineering

The backend sends raw telemetry events to the AIML FastAPI service. AIML performs feature extraction internally and converts events into model-ready signals across video behavior, typing patterns, scrolling behavior, focus signals, quiz performance, and interaction features. These include rewind density, pause behavior, typing latency, typing rhythm entropy, scroll reversal patterns, focus loss, quiz accuracy, hint dependency, confidence mismatch, fatigue proxies, and retention-risk proxies.

### Models

#### LightGBM Comprehension

Purpose: predict learner comprehension confidence from behavioral features.

Algorithm: LightGBM regression.

Metrics: MAE, RMSE, R2, Pearson correlation.

#### XGBoost Fatigue

Purpose: predict cognitive fatigue probability and fatigue state.

Algorithm: XGBoost binary classification.

Metrics: Accuracy, Precision, Recall, F1 Score, ROC-AUC, Confusion Matrix.

#### XGBoost Retention

Purpose: predict retention risk and future forgetting likelihood.

Algorithm: XGBoost regression.

Metrics: MAE, RMSE, R2, Bucket Accuracy.

### Fusion Layer

The fusion layer is deterministic rather than another machine learning model. This keeps ALETHIA explainable: model outputs remain visible, rule-engine traces remain transparent, and recommendations can be mapped back to observable cognitive signals. Fusion combines comprehension, retention strength, fatigue-derived cognitive energy, and rule-engine risk into one learning score, learning state, risk list, and intervention plan.

### Execution Commands

Generate dataset:

```bash
python -m aiml.data.synthetic_dataset_generator
```

Train models:

```bash
python -m aiml.models.comprehension_gbm.train
python -m aiml.models.fatigue_xgb.train
python -m aiml.models.retention_xgb.train --data aiml/data/synthetic_comprehension_dataset.csv
```

Evaluate models:

```bash
python -m aiml.models.comprehension_gbm.evaluate
python -m aiml.models.fatigue_xgb.evaluate
python -m aiml.models.retention_xgb.evaluate
```

Run inference:

```bash
python -m aiml.inference.predict
```

Run AIML API:

```bash
python -m uvicorn aiml.api.main:app --host 127.0.0.1 --port 8000
```

API contract:

```text
GET /
GET /health
POST /predict
```

Backend raw event request:

```json
{
  "session_id": "test123",
  "events": [
    {
      "event_type": "SCROLL",
      "timestamp": 17174300,
      "payload": {
        "domain": "leetcode.com",
        "scroll_delta": 350,
        "scroll_position": 2400
      }
    }
  ]
}
```

The service also accepts the legacy feature-dictionary request format for backward compatibility:

```json
{
  "session_id": "abc",
  "features": {
    "quiz_score": 0.8,
    "typing_speed_cpm": 200
  }
}
```

Prediction response:

```json
{
  "session_id": "test123",
  "overall_learning_score": 55,
  "learning_state": "Needs Strategy Change",
  "confidence": 0.7581,
  "metrics": {},
  "risks": [],
  "recommendations": [],
  "model_outputs": {},
  "rule_engine": {}
}
```

---

## Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Chrome Extension APIs
* Tailwind CSS

### Backend

* FastAPI
* Node.js
* Redis
* MongoDB

### Artificial Intelligence & Machine Learning

* Python
* NumPy
* Pandas
* Scikit-Learn
* LightGBM
* PyTorch

### Infrastructure

* WebSockets
* Redis Streams
* Docker
* GitHub

---

## Current Development Status

### Completed

✓ Feature Engineering Layer

✓ Cognitive Rule Engine

✓ Behavioral Telemetry Framework

✓ Repository Architecture

✓ Data Pipeline Design

### In Progress

• LightGBM Comprehension Model

• Fatigue Detection System

• Chrome Extension Integration

• Instructor Analytics Dashboard

### Planned

• Knowledge Tracing Engine

• Retention Prediction Engine

• Adaptive Learning Personalization

• Institution-Level Analytics

---

## Future Vision

Education should not end with content delivery.

The future of learning lies in understanding the learner.

ALETHIA aims to become the intelligence layer that bridges the gap between content consumption and genuine understanding.

By detecting learning breakdowns before they become performance failures, ALETHIA seeks to help students learn more effectively, educators teach more intelligently, and educational systems become truly adaptive.

Because completing a lesson is not the same as understanding it.
