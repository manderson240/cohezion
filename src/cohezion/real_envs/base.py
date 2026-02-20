"""Base classes for real embodied environments.

Defines the protocol and shared structures for environments that interact
with real systems (browser, shell, API) and capture execution traces.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Protocol, TypeVar

import numpy as np


logger = logging.getLogger(__name__)


TAction = TypeVar("TAction", bound="RealAction")
TObservation = TypeVar("TObservation", bound="RealObservation")
TState = TypeVar("TState", bound="RealState")


@dataclass(frozen=True)
class RealAction:
    """Base class for all actions in real environments.

    Actions are immutable and hashable for trajectory tracking.
    """

    action_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
        }

    def compute_hash(self) -> str:
        """Compute deterministic hash for deduplication."""
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class RealObservation:
    """Base class for all observations from real environments.

    Observations capture the result of actions and current state.
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms,
        }


@dataclass
class RealState:
    """Base class for environment state.

    States are snapshots that can be saved, restored, and compared.
    """

    state_type: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_embedding(self) -> list[float]:
        """Compute 256D embedding for FLUME trajectory tracking."""
        # Deterministic embedding from state content
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        hash_bytes = hashlib.sha256(content.encode()).digest()
        # Expand 32 bytes to 256 floats using PRNG
        np.random.seed(int.from_bytes(hash_bytes[:8], "big"))
        embedding = np.random.normal(0.5, 0.1, 256).tolist()
        np.random.seed()  # Reset seed
        return embedding

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_type": self.state_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class EnvironmentStep(Generic[TAction, TObservation, TState]):
    """A single step in an environment episode.

    Captures action, observation, state, and reward for RL training.
    """

    step_number: int
    action: TAction
    observation: TObservation
    state: TState
    reward: float = 0.0
    done: bool = False
    info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "action": self.action.to_dict(),
            "observation": self.observation.to_dict(),
            "state": self.state.to_dict(),
            "reward": self.reward,
            "done": self.done,
            "info": self.info,
        }


@dataclass
class TrajectorySegment:
    """A segment of an agent's trajectory through a real environment.

    Compatible with FLUME 12D manifold tracking.
    """

    segment_id: str
    environment_type: str
    task_id: str
    start_time: float
    end_time: float | None = None
    steps: list[EnvironmentStep] = field(default_factory=list)

    # 12D FLUME coordinates
    coherence: float = 0.5
    convergence: float = 0.0
    smoothness: float = 0.0

    def compute_metrics(self) -> dict[str, float]:
        """Compute trajectory quality metrics."""
        if not self.steps:
            return {"phi_score": 0.5, "success_rate": 0.0}

        success_count = sum(1 for s in self.steps if s.observation.success)
        success_rate = success_count / len(self.steps)

        # Compute smoothness as inverse of action variance
        if len(self.steps) > 1:
            rewards = [s.reward for s in self.steps]
            reward_variance = np.var(rewards) if rewards else 0.0
            self.smoothness = 1.0 / (1.0 + reward_variance)

        # PHI score: weighted combination
        phi = self.coherence * 0.5 + self.smoothness * 0.3 + self.convergence * 0.2

        return {
            "phi_score": phi,
            "success_rate": success_rate,
            "num_steps": len(self.steps),
            "total_reward": sum(s.reward for s in self.steps),
            "coherence": self.coherence,
            "smoothness": self.smoothness,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "environment_type": self.environment_type,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time or time.time(),
            "steps": [s.to_dict() for s in self.steps],
            **self.compute_metrics(),
        }


class RealEnvironment(ABC, Generic[TAction, TObservation, TState]):
    """Abstract base class for real embodied environments.

    All real environments must implement:
    - reset(): Initialize environment state
    - step(action): Execute action, return observation
    - get_state(): Return current state
    - evaluate(): Check if task is complete and compute reward
    """

    def __init__(
        self,
        task_description: str,
        max_steps: int = 100,
        output_dir: str = "data/real_envs",
    ):
        self.task_description = task_description
        self.max_steps = max_steps
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.current_step = 0
        self.trajectory: list[EnvironmentStep] = []
        self.segment: TrajectorySegment | None = None

        self._state: TState | None = None
        self._is_done = False

        logger.info(
            f"Initialized {self.__class__.__name__} for task: {task_description[:50]}..."
        )

    @abstractmethod
    def reset(self, seed: int | None = None) -> tuple[TObservation, TState]:
        """Reset environment to initial state.

        Returns:
            Initial observation and state
        """
        pass

    @abstractmethod
    async def step(
        self, action: TAction
    ) -> tuple[TObservation, float, bool, dict[str, Any]]:
        """Execute one step in the environment.

        Args:
            action: Action to execute

        Returns:
            (observation, reward, done, info)
        """
        pass

    @abstractmethod
    def get_state(self) -> TState:
        """Get current environment state."""
        pass

    @abstractmethod
    def evaluate_task(self) -> tuple[bool, float, dict[str, Any]]:
        """Evaluate if task is complete and compute reward.

        Returns:
            (is_complete, reward, metrics)
        """
        pass

    def start_segment(self, task_id: str) -> TrajectorySegment:
        """Start a new trajectory segment for tracking."""
        segment_id = f"{task_id}_{int(time.time() * 1000)}"
        self.segment = TrajectorySegment(
            segment_id=segment_id,
            environment_type=self.__class__.__name__,
            task_id=task_id,
            start_time=time.time(),
        )
        self.trajectory = []
        self.current_step = 0
        self._is_done = False
        return self.segment

    def end_segment(self) -> TrajectorySegment:
        """End current trajectory segment and return it."""
        if self.segment:
            self.segment.end_time = time.time()
            self.segment.steps = self.trajectory.copy()
            metrics = self.segment.compute_metrics()
            logger.info(f"Trajectory segment complete: {metrics}")
            return self.segment
        raise RuntimeError("No active segment to end")

    def save_trajectory(self, filename: str | None = None) -> Path:
        """Save trajectory to disk."""
        if not self.segment:
            raise RuntimeError("No segment to save")

        filename = filename or f"{self.segment.segment_id}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(self.segment.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved trajectory to {filepath}")
        return filepath

    def _compute_coherence(self) -> float:
        """Compute HIHO coherence for current trajectory."""
        if not self.trajectory:
            return 0.5

        # Coherence based on success rate and reward variance
        success_rate = sum(1 for s in self.trajectory if s.observation.success) / len(
            self.trajectory
        )
        rewards = [s.reward for s in self.trajectory]
        reward_variance = np.var(rewards) if len(rewards) > 1 else 0.0

        # HIHO optimal is at 0.5 - balance between order and chaos
        variance_penalty = min(reward_variance * 2, 0.5)
        coherence = 0.5 + (success_rate - 0.5) * 0.3 - variance_penalty * 0.2

        return max(0.0, min(1.0, coherence))
