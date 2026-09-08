r"""Bi-Temporal Knowledge Graph & Sheaf Laplacian Consistency Engine.
======================================================================
Synthesizes:
1. Graphiti (arXiv:2501.13956) bi-temporal edge modeling (valid_time vs assertion_time).
2. A-MEM (arXiv:2501.13783) dynamic synaptic evolution (Hebbian co-activation + exponential decay).
3. Sheaf Laplacian consistency analysis:
   $L_\Sigma = \delta^\dagger \delta$
   Dirichlet energy $E(x) = x^T L_\Sigma x = \|\delta x\|^2$ detects inter-agent epistemic drift.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class BiTemporalFact:
    """Fact representation supporting dual-time grounding (valid_time vs assertion_time)."""

    fact_id: str
    subject: str
    predicate: str
    object_val: Any
    valid_from: datetime
    valid_to: datetime | None = None
    asserted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    retracted_at: datetime | None = None
    agent_id: str = "swarm"
    confidence: float = 1.0

    def is_valid_at(self, as_of: datetime) -> bool:
        """True if the fact is historically true in the domain at `as_of`."""
        if as_of < self.valid_from:
            return False
        return self.valid_to is None or as_of < self.valid_to

    def is_asserted_at(self, as_of: datetime) -> bool:
        """True if the system was aware of/had asserted this fact by `as_of`."""
        return as_of >= self.asserted_at

    def is_active_belief_at(self, as_of: datetime) -> bool:
        """True if the fact was an unretracted belief of the swarm at `as_of`."""
        if not self.is_asserted_at(as_of):
            return False
        return self.retracted_at is None or as_of < self.retracted_at

    def retract(self, retracted_at: datetime | None = None) -> None:
        """Non-destructive retraction preserving observation provenance."""
        self.retracted_at = retracted_at or datetime.now(UTC)

    def to_surrealql(self) -> str:
        """Generate SurrealDB v2 RELATE statement."""
        v_to = f"d'{self.valid_to.isoformat()}'" if self.valid_to else "NONE"
        r_at = f"d'{self.retracted_at.isoformat()}'" if self.retracted_at else "NONE"
        clean_sub = "".join(c for c in self.subject if c.isalnum() or c in "_-")
        clean_pred = "".join(c for c in self.predicate if c.isalnum() or c in "_-")
        clean_obj = "".join(c for c in str(self.object_val) if c.isalnum() or c in "_-")

        return f"""
        RELATE kg_node:{clean_sub}->{clean_pred}->kg_node:{clean_obj} SET
            fact_id = '{self.fact_id}',
            valid_from = d'{self.valid_from.isoformat()}',
            valid_to = {v_to},
            asserted_at = d'{self.asserted_at.isoformat()}',
            retracted_at = {r_at},
            agent_id = '{self.agent_id}',
            confidence = {self.confidence};
        """


@dataclass
class DynamicSynapse:
    """A-MEM dynamic synapse with Hebbian co-activation and temporal decay."""

    source_id: str
    target_id: str
    weight: float = 0.5
    coactivations: int = 0
    decay_rate: float = 0.05
    last_activated: datetime | None = None

    def coactivate(self, timestamp: datetime | None = None, boost: float = 0.1) -> None:
        """Strengthen synapse upon concurrent co-retrieval / co-activation."""
        now = timestamp or datetime.now(UTC)
        self.coactivations += 1
        self.last_activated = now
        # Asymptotic reinforcement toward 1.0
        self.weight = min(1.0, self.weight + boost * (1.0 - self.weight))

    def compute_decayed_weight(self, as_of: datetime | None = None) -> float:
        """Calculate time-decayed weight: w(t) = w0 * exp(-decay_rate * delta_t_days)."""
        if self.last_activated is None:
            return self.weight
        now = as_of or datetime.now(UTC)
        delta_days = max(0.0, (now - self.last_activated).total_seconds() / 86400.0)
        return float(self.weight * math.exp(-self.decay_rate * delta_days))


@dataclass(frozen=True)
class SheafConsistencyResult:
    """Outcome of Sheaf Laplacian consistency and cohomology check."""

    is_consistent: bool
    dirichlet_energy: float
    harmonic_dimension: int
    divergent_edges: list[tuple[str, str, float]] = field(default_factory=list)


class BiTemporalSheafGraphEngine:
    """Engine fusing bi-temporal Graphiti memory with Sheaf Laplacian consistency."""

    def __init__(self, consistency_threshold: float = 0.05, default_stalk_dim: int = 3) -> None:
        self.consistency_threshold = consistency_threshold
        self.default_stalk_dim = default_stalk_dim

    def evaluate_sheaf_laplacian(
        self,
        agent_stalks: dict[str, np.ndarray],
        edges: Sequence[tuple[str, str]],
        restriction_maps: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
    ) -> SheafConsistencyResult:
        r"""Compute Sheaf Laplacian Dirichlet energy: $E(x) = \sum_{e=(u,v)} \|\mathcal{F}_{u \unlhd e} x_u - \mathcal{F}_{v \unlhd e} x_v\|^2$.

        Parameters
        ----------
        agent_stalks : dict[str, np.ndarray]
            Mapping of agent_id -> stalk vector (belief state / embedding).
        edges : Sequence[tuple[str, str]]
            List of directed communication edges between agents.
        restriction_maps : dict[tuple[str, str], tuple[np.ndarray, np.ndarray]]
            Mapping of (u, v) -> (R_u, R_v), where R_u projects stalk u to edge space,
            and R_v projects stalk v to edge space.
        """
        total_energy = 0.0
        divergent_edges: list[tuple[str, str, float]] = []

        for u, v in edges:
            x_u = agent_stalks.get(u)
            x_v = agent_stalks.get(v)
            if x_u is None or x_v is None:
                continue

            # Retrieve restriction matrices
            r_pair = restriction_maps.get((u, v))
            if r_pair is not None:
                r_u, r_v = r_pair
                proj_u = r_u @ x_u
                proj_v = r_v @ x_v
            else:
                # Default identity projection if stalk dimensions match
                proj_u = x_u
                proj_v = x_v

            # Difference along edge stalk: (delta x)_e
            diff = proj_u - proj_v
            edge_energy = float(np.sum(diff**2))
            total_energy += edge_energy

            if edge_energy > self.consistency_threshold:
                divergent_edges.append((u, v, edge_energy))

        # Check harmonic dimension (approximate dim H^0: zero-energy modes)
        stalk_dim = next(iter(agent_stalks.values())).shape[0] if agent_stalks else 0
        harmonic_dim = stalk_dim if total_energy < 1e-6 else 0

        is_consistent = total_energy <= self.consistency_threshold

        return SheafConsistencyResult(
            is_consistent=is_consistent,
            dirichlet_energy=total_energy,
            harmonic_dimension=harmonic_dim,
            divergent_edges=divergent_edges,
        )

    def harmonic_diffusion_step(
        self,
        agent_stalks: dict[str, np.ndarray],
        edges: Sequence[tuple[str, str]],
        restriction_maps: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
        step_size: float = 0.05,
    ) -> dict[str, np.ndarray]:
        r"""Performs one step of Sheaf Laplacian harmonic gradient descent to minimize Dirichlet energy.

        Equation: $x_{u}^{(t+1)} = x_{u}^{(t)} - \gamma \sum_{v \sim u} \mathcal{F}_{u \unlhd e}^T (\mathcal{F}_{u \unlhd e} x_u - \mathcal{F}_{v \unlhd e} x_v)$.
        """
        updated_stalks = {k: v.copy() for k, v in agent_stalks.items()}
        gradients = {k: np.zeros_like(v) for k, v in agent_stalks.items()}

        for u, v in edges:
            x_u = agent_stalks.get(u)
            x_v = agent_stalks.get(v)
            if x_u is None or x_v is None:
                continue

            r_pair = restriction_maps.get((u, v))
            if r_pair is not None:
                r_u, r_v = r_pair
                diff = (r_u @ x_u) - (r_v @ x_v)
                gradients[u] += 2.0 * (r_u.T @ diff)
                gradients[v] -= 2.0 * (r_v.T @ diff)
            else:
                diff = x_u - x_v
                gradients[u] += 2.0 * diff
                gradients[v] -= 2.0 * diff

        for k in updated_stalks:
            updated_stalks[k] -= step_size * gradients[k]

        return updated_stalks

    def diffuse(
        self,
        agent_stalks: dict[str, np.ndarray],
        edges: Sequence[tuple[str, str]],
        restriction_maps: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] | None = None,
        gamma: float = 0.05,
        steps: int = 1,
    ) -> dict[str, np.ndarray]:
        """Iteratively diffuse agent stalks to minimize Sheaf Dirichlet energy."""
        res_maps = restriction_maps if restriction_maps is not None else {}
        current = {k: v.copy() for k, v in agent_stalks.items()}
        for _ in range(steps):
            current = self.harmonic_diffusion_step(current, edges, res_maps, step_size=gamma)
        return current


# Re-export alias for cellular sheaf compatibility
CellularSheafEngine = BiTemporalSheafGraphEngine
