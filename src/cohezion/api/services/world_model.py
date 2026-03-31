"""World Model API Service.

Exposes the JEPA world model for training, prediction, simulation,
and surprise scoring. Connects to the Genesis Engine's physics layer
and SurrealDB persistence.

Endpoints:
  GET  /world-model/status       — Model status and training metrics
  POST /world-model/train        — Train on synthetic or stored data
  POST /world-model/predict      — Predict next state from current + action
  POST /world-model/simulate     — Roll out N-step trajectory
  POST /world-model/surprise     — Compute surprise for observed transition
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

world_model_router = APIRouter(prefix="/world-model", tags=["world-model"])

# Singleton world model
_MODEL = None


def _get_model():
    """Get or create the singleton JEPA world model.

    Auto-trains on first access with 200 synthetic samples if untrained,
    so predictions are meaningful from the first API call.
    """
    global _MODEL
    if _MODEL is None:
        from cohezion.world_model.jepa_world_model import JEPAWorldModel

        _MODEL = JEPAWorldModel(state_dim=12, action_dim=12, embed_dim=64)

    # Lazy auto-train: train on synthetic data if never trained
    if not _MODEL._trained:
        try:
            from cohezion.world_model.jepa_world_model import generate_synthetic_training_data

            data = generate_synthetic_training_data(n_samples=200)
            _MODEL.train_epoch(data, batch_size=32)
            logger.info("JEPA world model auto-trained on 200 synthetic samples")
        except Exception as e:
            logger.debug("JEPA auto-train failed (non-blocking): %s", e)

    return _MODEL


# --- Request/Response Models ---


class TrainRequest(BaseModel):
    n_samples: int = Field(500, ge=50, le=10000, description="Number of synthetic training samples")
    n_epochs: int = Field(10, ge=1, le=100, description="Training epochs")
    batch_size: int = Field(32, ge=8, le=256, description="Batch size")


class PredictRequest(BaseModel):
    state: list[float] = Field(..., min_length=12, max_length=12)
    action: list[float] = Field(..., min_length=12, max_length=12)


class SimulateRequest(BaseModel):
    initial_state: list[float] = Field(default_factory=lambda: [0.5] * 12)
    actions: list[list[float]] = Field(default_factory=lambda: [[0.01] * 12] * 10)


class SurpriseRequest(BaseModel):
    state: list[float] = Field(..., min_length=12, max_length=12)
    action: list[float] = Field(..., min_length=12, max_length=12)
    observed_next: list[float] = Field(..., min_length=12, max_length=12)


# --- Endpoints ---


@world_model_router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get world model status — parameters, training progress, metrics."""
    model = _get_model()
    return model.status()


@world_model_router.post("/train")
async def train_model(req: TrainRequest) -> dict[str, Any]:
    """Train the JEPA world model on synthetic Lagrangian trajectory data.

    Generates (state, action, next_state) tuples from Lagrangian dynamics
    on the 12D manifold and trains the predictor.
    """
    from cohezion.world_model.jepa_world_model import generate_synthetic_training_data

    model = _get_model()
    data = generate_synthetic_training_data(n_samples=req.n_samples, state_dim=12)

    all_metrics = []
    for epoch in range(req.n_epochs):
        metrics = model.train_epoch(data, batch_size=req.batch_size)
        all_metrics.append({"epoch": epoch + 1, **metrics})
        logger.info(
            "World model epoch %d: pred=%.6f kl=%.4f",
            epoch + 1,
            metrics["prediction_loss"],
            metrics["kl_loss"],
        )

    return {
        "status": "trained",
        "epochs": req.n_epochs,
        "samples": len(data),
        "final_metrics": all_metrics[-1],
        "loss_curve": [m["total_loss"] for m in all_metrics],
        "model_status": model.status(),
    }


@world_model_router.post("/predict")
async def predict_next(req: PredictRequest) -> dict:
    """Predict the next 12D state given current state + action."""
    model = _get_model()
    state = np.array(req.state, dtype=np.float32)
    action = np.array(req.action, dtype=np.float32)
    predicted = model.predict_next_state(state, action)
    return {
        "predicted_state": predicted.tolist(),
        "input_state": req.state,
        "action": req.action,
    }


@world_model_router.post("/simulate")
async def simulate_trajectory(req: SimulateRequest) -> dict:
    """Simulate a multi-step trajectory using the world model.

    Autoregressively predicts future states from a sequence of actions.
    Returns the full predicted trajectory.
    """
    model = _get_model()
    initial = np.array(req.initial_state[:12], dtype=np.float32)
    actions = [np.array(a[:12], dtype=np.float32) for a in req.actions]
    trajectory = model.simulate_trajectory(initial, actions)
    return {
        "trajectory": [t.tolist() for t in trajectory],
        "n_steps": len(trajectory),
        "initial_state": req.initial_state,
    }


@world_model_router.post("/surprise")
async def compute_surprise(req: SurpriseRequest) -> dict:
    """Compute surprise score for an observed transition.

    High surprise = the world model didn't predict this behavior.
    Low surprise = expected transition.
    """
    model = _get_model()
    state = np.array(req.state, dtype=np.float32)
    action = np.array(req.action, dtype=np.float32)
    observed = np.array(req.observed_next, dtype=np.float32)
    score = model.surprise_score(state, action, observed)
    return {
        "surprise_score": score,
        "interpretation": "expected"
        if score < 0.1
        else "surprising"
        if score < 1.0
        else "anomalous",
    }
