"""Monadic Local Markov Planning & State Penalty Engine.

Implements the hard-learned architectural lessons from ARC-3 & ARC-2:
1. Local State Action Penalties vs Fatal Global Constraint Pollution:
   Never ban environment colors or object types globally based on local collisions.
   Maintain local coordinate-state penalties and SplitMix64 Zobrist state hashing.
2. Step Budget Conservation:
   Preserve non-linear score economy by terminating exploratory excursions early
   when state novelty collapses.
3. Monotonic Improvement Invariant:
   Secondary heuristic policies never clobber valid high-confidence primary policies.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar
import numpy as np

logger = logging.getLogger(__name__)

S = TypeVar("S")  # State type
A = TypeVar("A")  # Action type


def splitmix64(z: int) -> int:
    """SplitMix64 deterministic pseudo-random hash generator for Zobrist state hashing."""
    z = (z + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & 0xFFFFFFFFFFFFFFFF
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & 0xFFFFFFFFFFFFFFFF
    return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF


@dataclass
class LocalState:
    """Local, immutable state snapshot with cycle detection and cost tracking."""

    coordinates: Tuple[int, ...]
    zobrist_hash: int
    step_count: int = 0
    accumulated_cost: float = 0.0
    recent_actions: Tuple[Any, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, coordinates: Tuple[int, ...], metadata: Optional[Dict[str, Any]] = None) -> LocalState:
        # Generate initial 64-bit Zobrist hash from coordinates
        h = 0
        for i, c in enumerate(coordinates):
            h ^= splitmix64((c << 16) + i)
        return cls(
            coordinates=coordinates,
            zobrist_hash=h,
            metadata=metadata or {},
        )

    def transition(
        self,
        new_coordinates: Tuple[int, ...],
        action: Any,
        cost: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocalState:
        # Incremental Zobrist update
        h = self.zobrist_hash
        for i, c in enumerate(new_coordinates):
            h ^= splitmix64((c << 16) + (self.step_count + 1) * 31 + i)
        recent = (self.recent_actions + (action,))[-8:]  # Keep last 8 actions
        meta = {**self.metadata, **(metadata or {})}
        return LocalState(
            coordinates=new_coordinates,
            zobrist_hash=h,
            step_count=self.step_count + 1,
            accumulated_cost=self.accumulated_cost + cost,
            recent_actions=recent,
            metadata=meta,
        )


class LocalMarkovPlanner:
    """Planner that uses local state penalties and cycle evasion without global pollution."""

    def __init__(
        self,
        step_budget: int = 45,
        wall_bump_penalty: float = 100.0,
        revisit_decay: float = 2.0,
    ) -> None:
        self.step_budget = step_budget
        self.wall_bump_penalty = wall_bump_penalty
        self.revisit_decay = revisit_decay
        # Local state-action penalty table: (state_hash, action) -> penalty
        self._local_penalties: Dict[Tuple[int, Any], float] = {}
        # Visited state counts: zobrist_hash -> visit_count
        self._visited_hashes: Dict[int, int] = {}

    def penalize_local_action(self, state: LocalState, action: Any, penalty: Optional[float] = None) -> None:
        """Applies a penalty to taking action `a` strictly at local state `s`."""
        p = penalty if penalty is not None else self.wall_bump_penalty
        key = (state.zobrist_hash, action)
        self._local_penalties[key] = self._local_penalties.get(key, 0.0) + p

    def get_action_penalty(self, state: LocalState, action: Any) -> float:
        """Returns the local penalty for an action at the current state."""
        base_p = self._local_penalties.get((state.zobrist_hash, action), 0.0)
        # Revisit penalty to prevent infinite loops
        visits = self._visited_hashes.get(state.zobrist_hash, 0)
        revisit_p = visits * self.revisit_decay
        return base_p + revisit_p

    def record_visit(self, state: LocalState) -> None:
        self._visited_hashes[state.zobrist_hash] = (
            self._visited_hashes.get(state.zobrist_hash, 0) + 1
        )

    def is_cycle(self, state: LocalState, threshold: int = 3) -> bool:
        """Detects if the agent is trapped in a local cycle."""
        return self._visited_hashes.get(state.zobrist_hash, 0) >= threshold

    def is_budget_exhausted(self, state: LocalState) -> bool:
        return state.step_count >= self.step_budget
