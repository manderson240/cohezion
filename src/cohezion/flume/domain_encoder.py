"""Encode competition-specific states into 12D FLUME manifold vectors.

Each competition domain (math, kernel optimization, interactive games) has
unique state signals.  ``DomainEncoder`` subclasses map those signals to
the shared 12D axiomatic space used by JourneyTracker and the JEPA world
model, enabling **cross-competition** trajectory analysis.

Encoding contract:
  - Every encoder produces ``np.ndarray`` of shape ``(12,)`` dtype ``float32``.
  - Values are individually normalised to roughly [-1, 1].
  - ``GenericEncoder`` provides a deterministic hash-based fallback for
    previously unseen competition types.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

import numpy as np


# Shared constant from the FLUME manifold (JourneyTracker.AXIOMATIC_DIMS)
MANIFOLD_DIM = 12


@dataclass
class EncodedTrajectoryPoint:
    """A single point in a competition trajectory, FLUME-encoded."""

    domain: str
    state_12d: np.ndarray  # shape (12,)
    action_description: str
    reward: float
    surprise: float | None = None  # JEPA prediction error (computed later)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state_12d"] = self.state_12d.tolist()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> EncodedTrajectoryPoint:
        data = dict(data)
        data["state_12d"] = np.asarray(data["state_12d"], dtype=np.float32)
        return cls(**data)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class DomainEncoder(ABC):
    """Encode competition-specific state into the 12D FLUME manifold."""

    @abstractmethod
    def encode(self, raw_state: dict) -> np.ndarray:
        """Map *raw_state* -> 12D float32 vector."""

    @abstractmethod
    def domain_name(self) -> str:
        """Canonical domain identifier (e.g. ``'aimo'``)."""

    # Convenience: build a full trajectory point in one call.
    def encode_point(
        self,
        raw_state: dict,
        action: str,
        reward: float,
        **metadata: object,
    ) -> EncodedTrajectoryPoint:
        return EncodedTrajectoryPoint(
            domain=self.domain_name(),
            state_12d=self.encode(raw_state),
            action_description=action,
            reward=reward,
            metadata=dict(metadata),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(state: dict, key: str, default: float = 0.0) -> float:
    v = state.get(key)
    if v is None:
        return default
    return float(v)


def _log_norm(val: float, scale: float = 10.0) -> float:
    """log1p normalisation into roughly [0, 1]."""
    return math.log1p(abs(val)) / scale


def _clip(val: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, val))


# ---------------------------------------------------------------------------
# Concrete encoders
# ---------------------------------------------------------------------------


class MathProblemEncoder(DomainEncoder):
    """Encode math competition state (AIMO-style).

    Dimensions:
        0 problem_length  1 difficulty  2 topic_hash  3 step_count
        4 confidence  5 verification_status  6 time_spent  7 tokens_used
        8 attempt_number  9 coherence  10 novelty  11 correctness
    """

    def domain_name(self) -> str:
        return "aimo"

    def encode(self, raw_state: dict) -> np.ndarray:
        vec = np.zeros(MANIFOLD_DIM, dtype=np.float32)
        vec[0] = _clip(_log_norm(_safe_float(raw_state, "problem_length"), 8.0))
        vec[1] = _clip(_safe_float(raw_state, "difficulty") / 10.0)
        # Topic hash: deterministic [0,1] from topic string
        topic = raw_state.get("topic", "")
        vec[2] = _topic_hash(str(topic))
        vec[3] = _clip(_log_norm(_safe_float(raw_state, "step_count"), 4.0))
        vec[4] = _clip(_safe_float(raw_state, "confidence"))
        vec[5] = 1.0 if raw_state.get("verification_status") else 0.0
        vec[6] = _clip(_log_norm(_safe_float(raw_state, "time_spent"), 8.0))
        vec[7] = _clip(_log_norm(_safe_float(raw_state, "tokens_used"), 15.0))
        vec[8] = _clip(_safe_float(raw_state, "attempt_number") / 10.0)
        vec[9] = _clip(_safe_float(raw_state, "coherence"))
        vec[10] = _clip(_safe_float(raw_state, "novelty"))
        vec[11] = _clip(_safe_float(raw_state, "correctness"))
        return vec


class KernelOptimizationEncoder(DomainEncoder):
    """Encode GPU kernel optimisation state (Luma GEMM-style).

    Dimensions:
        0 geomean_us  1 shape_count  2 ksplit_mean  3 split_k_mean
        4 improvement_ratio  5 stagnation_count  6 best_vs_leader_gap
        7 parameter_entropy  8 submission_count  9 test_pass_rate
        10 benchmark_variance  11 time_budget_remaining
    """

    def domain_name(self) -> str:
        return "luma-gemm"

    def encode(self, raw_state: dict) -> np.ndarray:
        vec = np.zeros(MANIFOLD_DIM, dtype=np.float32)
        vec[0] = _clip(_log_norm(_safe_float(raw_state, "geomean_us"), 10.0))
        vec[1] = _clip(_log_norm(_safe_float(raw_state, "shape_count"), 5.0))
        vec[2] = _clip(_safe_float(raw_state, "ksplit_mean") / 16.0)
        vec[3] = _clip(_safe_float(raw_state, "split_k_mean") / 16.0)
        vec[4] = _clip(_safe_float(raw_state, "improvement_ratio"))
        vec[5] = _clip(_safe_float(raw_state, "stagnation_count") / 20.0)
        vec[6] = _clip(_safe_float(raw_state, "best_vs_leader_gap"))
        vec[7] = _clip(_safe_float(raw_state, "parameter_entropy"))
        vec[8] = _clip(_log_norm(_safe_float(raw_state, "submission_count"), 5.0))
        vec[9] = _clip(_safe_float(raw_state, "test_pass_rate"))
        vec[10] = _clip(_safe_float(raw_state, "benchmark_variance"))
        vec[11] = _clip(_safe_float(raw_state, "time_budget_remaining"))
        return vec


class InteractiveGameEncoder(DomainEncoder):
    """Encode ARC-AGI-3 interactive game state.

    Dimensions:
        0 grid_entropy  1 action_count  2 level_progress  3 unique_states_seen
        4 undo_count  5 interaction_count  6 pattern_complexity  7 symmetry_score
        8 goal_proximity  9 exploration_coverage  10 model_confidence
        11 time_remaining
    """

    def domain_name(self) -> str:
        return "arc-agi"

    def encode(self, raw_state: dict) -> np.ndarray:
        vec = np.zeros(MANIFOLD_DIM, dtype=np.float32)
        vec[0] = _clip(_safe_float(raw_state, "grid_entropy"))
        vec[1] = _clip(_log_norm(_safe_float(raw_state, "action_count"), 6.0))
        vec[2] = _clip(_safe_float(raw_state, "level_progress"))
        vec[3] = _clip(_log_norm(_safe_float(raw_state, "unique_states_seen"), 6.0))
        vec[4] = _clip(_log_norm(_safe_float(raw_state, "undo_count"), 4.0))
        vec[5] = _clip(_log_norm(_safe_float(raw_state, "interaction_count"), 6.0))
        vec[6] = _clip(_safe_float(raw_state, "pattern_complexity"))
        vec[7] = _clip(_safe_float(raw_state, "symmetry_score"))
        vec[8] = _clip(_safe_float(raw_state, "goal_proximity"))
        vec[9] = _clip(_safe_float(raw_state, "exploration_coverage"))
        vec[10] = _clip(_safe_float(raw_state, "model_confidence"))
        vec[11] = _clip(_safe_float(raw_state, "time_remaining"))
        return vec


class GenericEncoder(DomainEncoder):
    """Fallback encoder for unknown competition types.

    Uses deterministic feature hashing to project arbitrary dicts into 12D.
    """

    def __init__(self, domain: str = "generic") -> None:
        self._domain = domain

    def domain_name(self) -> str:
        return self._domain

    def encode(self, raw_state: dict) -> np.ndarray:
        text = "|".join(f"{k}={v}" for k, v in sorted(raw_state.items()))
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = np.zeros(MANIFOLD_DIM, dtype=np.float32)
        for i in range(MANIFOLD_DIM):
            byte_val = digest[i % len(digest)]
            phase = (2.0 * math.pi * i) / MANIFOLD_DIM
            vec[i] = (byte_val / 255.0 - 0.5) * 2.0 * 0.6 + 0.1 * math.sin(phase)
        return vec


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ENCODER_REGISTRY: dict[str, type[DomainEncoder]] = {
    "aimo": MathProblemEncoder,
    "luma-gemm": KernelOptimizationEncoder,
    "arc-agi": InteractiveGameEncoder,
}


def register_encoder(domain: str, encoder_cls: type[DomainEncoder]) -> None:
    """Register a custom encoder for a competition domain."""
    _ENCODER_REGISTRY[domain] = encoder_cls


def get_encoder(domain: str) -> DomainEncoder:
    """Return the right encoder for *domain*, falling back to ``GenericEncoder``."""
    cls = _ENCODER_REGISTRY.get(domain)
    if cls is not None:
        return cls()
    return GenericEncoder(domain=domain)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _topic_hash(topic: str) -> float:
    """Deterministic hash of a topic string into [0, 1]."""
    digest = hashlib.md5(topic.encode("utf-8")).digest()  # noqa: S324
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
