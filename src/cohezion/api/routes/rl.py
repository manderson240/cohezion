"""RL training + inference + policy-info routes.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).

Re-uses ``cohezion.api._get_rl_policy`` and ``cohezion.api._compute_coherence``
so existing test patches keep working.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

rl_router = APIRouter(tags=["rl"])


class RLTrainRequest(BaseModel):
    n_episodes: int = 100
    max_steps: int = 200
    lr: float = 3e-4
    gamma: float = 0.99


class RLTrainResponse(BaseModel):
    episodes_completed: int
    final_reward: float
    final_coherence: float
    mean_reward: float
    checkpoint_path: str


class RLPolicyResponse(BaseModel):
    exists: bool
    checkpoint_path: str | None = None
    parameters: int | None = None
    state_dim: int | None = None
    action_dim: int | None = None


class RlStepRequest(BaseModel):
    state: list[float]


class RlStepResponse(BaseModel):
    action: list[float]
    coherence: float


class RlEpisodeResponse(BaseModel):
    steps: int
    total_reward: float
    mean_coherence: float
    final_coherence: float
    trajectory: list[dict[str, Any]]


class RlPolicyInfoResponse(BaseModel):
    loaded: bool
    architecture: str | None = None
    state_dim: int | None = None
    action_dim: int | None = None
    hidden_dim: int | None = None
    parameters: int | None = None
    checkpoint_path: str | None = None
    training_metrics: list[dict[str, Any]] | dict[str, Any] | None = None


@rl_router.post("/rl/train", response_model=RLTrainResponse)
async def train_rl(request: RLTrainRequest):
    """Trigger RL policy training on FlumeNav-v0."""
    from cohezion.rl.trainer import TrainingConfig, train

    config = TrainingConfig(
        n_episodes=request.n_episodes,
        max_steps=request.max_steps,
        lr=request.lr,
        gamma=request.gamma,
    )

    try:
        results = train(config)
    except Exception as e:
        # FastAPI endpoint — convert any RL training failure to clean 500 with logged detail.
        logger.error("RL training failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Training failed") from e

    final = results[-1]
    import numpy as np

    mean_reward = float(np.mean([r.total_reward for r in results]))
    checkpoint_dir = Path(config.output_dir)
    ckpt = checkpoint_dir / "policy_final.pt"

    return RLTrainResponse(
        episodes_completed=len(results),
        final_reward=final.total_reward,
        final_coherence=final.mean_coherence,
        mean_reward=mean_reward,
        checkpoint_path=str(ckpt) if ckpt.exists() else "",
    )


@rl_router.get("/rl/policy/{agent_id}", response_model=RLPolicyResponse)
async def get_rl_policy(agent_id: str):
    """Inspect a trained RL policy checkpoint."""
    checkpoint_dir = Path("data/rl/checkpoints")
    ckpt_path = checkpoint_dir / f"policy_{agent_id}.pt"

    # Also check for the default final checkpoint
    if not ckpt_path.exists():
        ckpt_path = checkpoint_dir / "policy_final.pt"

    if not ckpt_path.exists():
        return RLPolicyResponse(exists=False)

    import torch

    try:
        state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        n_params = sum(v.numel() for v in state_dict.values())

        # Infer dimensions from the first linear layer
        state_dim = None
        action_dim = None
        if "shared.0.weight" in state_dict:
            state_dim = state_dict["shared.0.weight"].shape[1]
        if "mean_head.weight" in state_dict:
            action_dim = state_dict["mean_head.weight"].shape[0]

        return RLPolicyResponse(
            exists=True,
            checkpoint_path=str(ckpt_path),
            parameters=n_params,
            state_dim=state_dim,
            action_dim=action_dim,
        )
    except (OSError, KeyError, ValueError, RuntimeError, AttributeError) as e:
        logger.warning("Failed to inspect policy checkpoint: %s", e, exc_info=True)
        return RLPolicyResponse(exists=True, checkpoint_path=str(ckpt_path))


@rl_router.post("/rl/step", response_model=RlStepResponse)
async def rl_step(request: RlStepRequest):
    """Run a single RL step: state -> policy -> action + coherence."""
    import numpy as np

    from cohezion.api import _compute_coherence, _get_rl_policy

    if len(request.state) != 256:
        raise HTTPException(
            status_code=422,
            detail=f"State must be 256D, got {len(request.state)}D",
        )

    policy = _get_rl_policy()
    state = np.array(request.state, dtype=np.float32)
    action, _log_prob = policy.get_action(state)

    # Compute coherence of resulting state (state + scaled action)
    next_state = state + action * 0.01
    coherence = _compute_coherence(next_state.tolist(), 256)

    return RlStepResponse(
        action=action.tolist(),
        coherence=coherence,
    )


@rl_router.post("/rl/episode", response_model=RlEpisodeResponse)
async def rl_episode():
    """Run a full RL episode (up to 200 steps) with the trained policy."""
    import gymnasium as gym
    import numpy as np

    import cohezion.rl.environment  # noqa: F401 — registers Gymnasium env
    from cohezion.api import _get_rl_policy

    policy = _get_rl_policy()
    env = gym.make("cohezion/FlumeNav-v0", max_steps=200)

    try:
        obs, info = env.reset(seed=42)
        trajectory: list[dict[str, Any]] = []
        total_reward = 0.0
        coherences: list[float] = [info["coherence"]]

        for _step in range(200):
            action, _log_prob = policy.get_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)

            total_reward += reward
            coherences.append(info["coherence"])
            trajectory.append(
                {
                    "state_mean": float(np.mean(obs)),
                    "state_std": float(np.std(obs)),
                    "action_norm": float(np.linalg.norm(action)),
                    "reward": reward,
                    "coherence": info["coherence"],
                }
            )

            if terminated or truncated:
                break
    finally:
        env.close()

    return RlEpisodeResponse(
        steps=len(trajectory),
        total_reward=total_reward,
        mean_coherence=float(np.mean(coherences)),
        final_coherence=coherences[-1],
        trajectory=trajectory,
    )


@rl_router.get("/rl/policy-info", response_model=RlPolicyInfoResponse)
async def rl_policy_info():
    """Return policy metadata: architecture, parameters, training metrics."""
    import json

    from cohezion.api import _get_rl_policy

    ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
    if not ckpt_path.exists():
        return RlPolicyInfoResponse(loaded=False)

    policy = _get_rl_policy()
    n_params = sum(p.numel() for p in policy.parameters())

    # Load training metrics if available
    metrics_path = Path("data/rl/checkpoints/training_metrics.json")
    training_metrics = None
    if metrics_path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            training_metrics = json.loads(metrics_path.read_text())

    return RlPolicyInfoResponse(
        loaded=True,
        architecture="PolicyNetwork(shared=[Linear+ReLU x2], mean_head=Linear, log_std=Parameter)",
        state_dim=256,
        action_dim=256,
        hidden_dim=128,
        parameters=n_params,
        checkpoint_path=str(ckpt_path),
        training_metrics=training_metrics,
    )
