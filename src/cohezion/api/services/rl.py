"""
RL Service - Logic for training and running RL policies on Flume environments.
"""

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# --- Models ---


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
    state: list[float]  # 256D state vector


class RlStepResponse(BaseModel):
    action: list[float]  # 256D action vector
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
    training_metrics: Any | None = None


# --- Service Logic ---

_rl_policy = None


def get_rl_policy_singleton():
    """Lazy-load the trained RL policy singleton."""
    global _rl_policy
    if _rl_policy is None:
        import torch

        from cohezion.rl.trainer import PolicyNetwork

        _rl_policy = PolicyNetwork(state_dim=256, action_dim=256, hidden=128)
        ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
        if ckpt_path.exists():
            _rl_policy.load_state_dict(torch.load(ckpt_path, map_location="cpu", weights_only=True))
            _rl_policy.eval()
            logger.info("Loaded RL policy from %s", ckpt_path)
        else:
            logger.warning("No RL checkpoint at %s — using random policy", ckpt_path)
    return _rl_policy


async def train_rl_service(request: RLTrainRequest) -> RLTrainResponse:
    """Trigger RL policy training on FlumeNav-v0."""
    import numpy as np

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
        logger.error(f"RL training failed: {e}")
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


async def get_rl_policy_service(agent_id: str) -> RLPolicyResponse:
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
        logger.warning(f"Failed to inspect policy checkpoint: {e}")
        return RLPolicyResponse(exists=True, checkpoint_path=str(ckpt_path))


async def rl_step_service(request: RlStepRequest) -> RlStepResponse:
    """Run a single RL step."""
    import numpy as np

    from cohezion.api.services.flume import compute_coherence

    if len(request.state) != 256:
        raise HTTPException(
            status_code=422,
            detail=f"State must be 256D, got {len(request.state)}D",
        )

    policy = get_rl_policy_singleton()
    state = np.array(request.state, dtype=np.float32)
    action, _log_prob = policy.get_action(state)

    next_state = state + action * 0.01
    coherence = compute_coherence(next_state.tolist(), 256)

    return RlStepResponse(
        action=action.tolist(),
        coherence=coherence,
    )


async def rl_episode_service() -> RlEpisodeResponse:
    """Run a full RL episode."""
    import gymnasium as gym
    import numpy as np

    policy = get_rl_policy_singleton()
    env = gym.make("cohezion/FlumeNav-v0", max_steps=200)

    try:
        obs, info = env.reset(seed=42)
        trajectory = []
        total_reward = 0.0
        coherences = [info["coherence"]]

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


async def rl_policy_info_service() -> RlPolicyInfoResponse:
    """Return policy metadata."""

    ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
    if not ckpt_path.exists():
        return RlPolicyInfoResponse(loaded=False)

    policy = get_rl_policy_singleton()
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


# --- Benchmark Endpoints ---


class BenchmarkRunRequest(BaseModel):
    """Request to run a benchmark evaluation."""

    tasks: list[str] | None = None
    num_episodes: int = 10
    output_path: str | None = None
    seed: int | None = None
    verbose: bool = False


class BenchmarkRunResponse(BaseModel):
    """Response from a benchmark run."""

    run_id: str
    num_episodes: int
    num_tasks: int
    total_duration_seconds: float
    results_summary: dict[str, Any]


class BenchmarkScorecardResponse(BaseModel):
    """Response with full scorecard report."""

    run_id: str
    report: dict[str, Any]


class BenchmarkRadarResponse(BaseModel):
    """Response with radar chart as base64-encoded SVG."""

    run_id: str
    format: str
    data: str


# Module-level scorecard registry
_benchmark_scorecards: dict[str, Any] = {}


async def run_benchmark_service(request: BenchmarkRunRequest) -> BenchmarkRunResponse:
    """Run a FLUME journey benchmark evaluation.

    Uses the BenchmarkSuite to evaluate a trained policy on one or more
    benchmark tasks, then stores the resulting scorecard for retrieval.
    """
    import time
    import uuid
    from pathlib import Path

    from cohezion.benchmarks.benchmark_suite import BenchmarkSuite

    policy = get_rl_policy_singleton()

    class PolicyAdapter:
        """Adapt PolicyNetwork.get_action to BenchmarkSuite protocol."""

        def __init__(self, net):
            self._net = net

        def get_action(self, state):
            action, log_prob = self._net.get_action(state)
            return action, float(log_prob.item()), 0.5

    adapter = PolicyAdapter(policy)
    suite = BenchmarkSuite()

    start_time = time.monotonic()

    results = suite.run(
        policy=adapter,
        tasks=request.tasks,
        num_episodes=request.num_episodes,
        output_path=Path(request.output_path) if request.output_path else None,
        seed=request.seed,
        verbose=request.verbose,
    )

    total_duration = time.monotonic() - start_time

    run_id = str(uuid.uuid4())[:8]

    results_summary = {}
    for task_name, result in results.items():
        results_summary[task_name] = {
            "num_episodes": result.num_episodes,
            "mean_reward": result.mean_reward,
            "mean_coherence": result.mean_coherence,
            "success_rate": result.success_rate,
            "mean_steps": result.mean_steps,
            "total_duration_seconds": result.total_duration_seconds,
        }

    scorecard_path = Path("data/rl/benchmarks")
    scorecard_path.mkdir(parents=True, exist_ok=True)
    import json

    scorecard_file = scorecard_path / f"scorecard_{run_id}.json"
    with open(scorecard_file, "w") as f:
        json.dump(results_summary, f)

    return BenchmarkRunResponse(
        run_id=run_id,
        num_episodes=request.num_episodes,
        num_tasks=len(results),
        total_duration_seconds=total_duration,
        results_summary=results_summary,
    )


async def get_benchmark_scorecard_service(run_id: str) -> BenchmarkScorecardResponse:
    """Get the full scorecard report for a completed benchmark run."""
    scorecard_path = Path(f"data/rl/benchmarks/scorecard_{run_id}.json")

    if not scorecard_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")

    import json

    with open(scorecard_path) as f:
        report = json.load(f)

    return BenchmarkScorecardResponse(run_id=run_id, report=report)


async def get_benchmark_radar_service(run_id: str) -> BenchmarkRadarResponse:
    """Get a radar chart SVG for a completed benchmark run.

    Requires plotly. Returns base64-encoded SVG if unavailable.
    """
    scorecard_path = Path(f"data/rl/benchmarks/scorecard_{run_id}.json")

    if not scorecard_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")

    try:
        import json

        from cohezion.eval.capability_scorecard import CapabilityScorecard

        with open(scorecard_path) as f:
            data = json.load(f)

        scorecard = CapabilityScorecard()

        episode_summaries = []
        for _task_name, task_data in data.items():
            n_eps = task_data.get("num_episodes", 10)
            for i in range(n_eps):
                episode_summaries.append(
                    {
                        "episode": i,
                        "reward": task_data.get("mean_reward", 0.0),
                        "coherence": task_data.get("mean_coherence", 0.5),
                        "final_coherence": task_data.get("mean_coherence", 0.5),
                        "success": task_data.get("success_rate", 0.0) > 0.5,
                        "steps": int(task_data.get("mean_steps", 100)),
                    }
                )

        scorecard.record_run(f"bench_{run_id}", episode_summaries)

        fig = scorecard.plot_radar(run_id=f"bench_{run_id}")

        try:
            svg_data = fig.to_image(format="svg")
        except Exception:
            import io

            buf = io.BytesIO()
            fig.write_image(buf, format="svg")
            buf.seek(0)
            svg_data = buf.read()

        import base64

        encoded = base64.b64encode(svg_data).decode()

        return BenchmarkRadarResponse(run_id=run_id, format="svg+base64", data=encoded)

    except Exception as e:
        logger.error(f"Radar chart generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Radar chart unavailable: {e}") from None
