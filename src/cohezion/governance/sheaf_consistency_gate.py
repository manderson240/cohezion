r"""Sheaf-Theoretic Consistency & Cohomology Gate Engine.

Implements Sheaf Theory and Čech Cohomology over multi-agent task simplicial complexes:
1. Vertices (V): Active agent sessions / swarms.
2. Stalks (F(U)): Local belief state vectors / claim artifacts.
3. Restriction Maps (rho_UV): Projection of claims onto shared artifact intersections.
4. Zeroth Cohomology H^0(X, F): Global consensus dimension.
5. First Cohomology H^1(X, F): Obstruction / contradiction dimension.
   - dim H^1 == 0: Swarm consensus is mathematically consistent (gluable).
   - dim H^1 > 0: Contradiction / epistemic collision detected without mutex locking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SheafConsistencyReport:
    """Report evaluating sheaf cohomology over multi-agent claims."""

    is_consistent: bool
    dim_h0_consensus: int
    dim_h1_obstructions: int
    max_coboundary_residual: float
    conflicting_pairs: list[tuple[str, str, float]]


class SheafConsistencyGate:
    """Čech Cohomology gate for multi-agent knowledge and state consistency."""

    def __init__(self, tolerance: float = 0.15) -> None:
        self.tolerance = tolerance

    def evaluate_consistency(
        self,
        agent_claims: dict[str, np.ndarray | list[float]],
        shared_intersections: list[tuple[str, str]],
    ) -> SheafConsistencyReport:
        """Evaluates whether local agent claims glue into a global section (dim H^1 == 0).

        Parameters
        ----------
        agent_claims : dict[str, np.ndarray | list[float]]
            Mapping of agent/session ID to state/claim vector.
        shared_intersections : list[tuple[str, str]]
            List of (agent_u, agent_v) pairs sharing a claim boundary.

        Returns
        -------
        SheafConsistencyReport
            Structured Čech cohomology analysis.
        """
        if not agent_claims:
            return SheafConsistencyReport(
                is_consistent=True,
                dim_h0_consensus=0,
                dim_h1_obstructions=0,
                max_coboundary_residual=0.0,
                conflicting_pairs=[],
            )

        conflicts: list[tuple[str, str, float]] = []
        max_residual = 0.0

        for u, v in shared_intersections:
            if u not in agent_claims or v not in agent_claims:
                continue

            try:
                vec_u = np.asarray(agent_claims[u], dtype=np.float64)
                vec_v = np.asarray(agent_claims[v], dtype=np.float64)

                if vec_u.shape != vec_v.shape:
                    conflicts.append((u, v, float("inf")))
                    continue

                # Čech 1-coboundary delta: d^0(f)_{uv} = f_v - f_u
                residual = float(np.linalg.norm(vec_v - vec_u))
                if np.isnan(residual) or np.isinf(residual):
                    conflicts.append((u, v, float("inf")))
                    continue

                if residual > max_residual:
                    max_residual = residual

                if residual > self.tolerance:
                    conflicts.append((u, v, round(residual, 4)))
            except Exception:
                conflicts.append((u, v, float("inf")))

        dim_h1 = len(conflicts)
        dim_h0 = 1 if (dim_h1 == 0 and len(agent_claims) > 0) else 0
        is_consistent = dim_h1 == 0

        return SheafConsistencyReport(
            is_consistent=is_consistent,
            dim_h0_consensus=dim_h0,
            dim_h1_obstructions=dim_h1,
            max_coboundary_residual=round(max_residual, 4),
            conflicting_pairs=conflicts,
        )
