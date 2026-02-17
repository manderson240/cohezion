"""RL policy training and inference endpoints."""

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException

from cohezion.api.helpers import compute_coherence
from cohezion.api.models import (
    RlEpisodeResponse,
    RlPolicyInfoResponse,
    RLPolicyResponse,
    RlStepRequest,
    RlStepResponse,
    RLTrainRequest,
    RLTrainResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rl", tags=["rl"])


@router.post("/train", response_model=RLTrainResponse)
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
        logger.error('RL training failed: %s', e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    final = results[-1]

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


@router.get("/policy/{agent_id}", response_model=RLPolicyResponse)
async def get_rl_policy(agent_id: str):
    """Inspect a trained RL policy checkpoint."""
    checkpoint_dir = Path("data/rl/checkpoints")
    ckpt_path = checkpoint_dir / f"policy_{agent_id}.pt"

    if not ckpt_path.exists():
        ckpt_path = checkpoint_dir / "policy_final.pt"

    if not ckpt_path.exists():
        return RLPolicyResponse(exists=False)

    import torch

    try:
        state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        n_params = sum(v.numel() for v in state_dict.values())

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
    except Exception as e:
        logger.warning('Failed to inspect policy checkpoint: %s', e)
        return RLPolicyResponse(exists=True, checkpoint_path=str(ckpt_path))


def _get_rl_policy():
    """Lazy-load the trained RL policy singleton via helpers."""
    from cohezion.api.helpers import get_rl_policy

    return get_rl_policy()


@router.post("/step", response_model=RlStepResponse)
async def rl_step(request: RlStepRequest):
    """Run a single RL step: state -> policy -> action + coherence."""

    if len(request.state) != 256:
        raise HTTPException(
            status_code=422,
            detail=f"State must be 256D, got {len(request.state)}D",
        )

    policy = _get_rl_policy()
    state = np.array(request.state, dtype=np.float32)
    action, _log_prob = policy.get_action(state)

    next_state = state + action * 0.01
    coherence = compute_coherence(next_state.tolist(), 256)

    return RlStepResponse(
        action=action.tolist(),
        coherence=coherence,
    )


@router.post("/episode", response_model=RlEpisodeResponse)
async def rl_episode():
    """Run a full RL episode (up to 200 steps) with the trained policy."""
    import gymnasium as gym

    import cohezion.rl.environment  # noqa: F401

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


@router.get("/policy-info", response_model=RlPolicyInfoResponse)
async def rl_policy_info():
    """Return policy metadata: architecture, parameters, training metrics."""

    ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
    if not ckpt_path.exists():
        return RlPolicyInfoResponse(loaded=False)

    policy = _get_rl_policy()
    n_params = sum(p.numel() for p in policy.parameters())

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


if __name__ == "__main__":
    import uvicorn

    from cohezion.api import app

    uvicorn.run(app, host="0.0.0.0", port=8080)
