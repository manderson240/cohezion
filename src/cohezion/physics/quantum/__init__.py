"""Quantum circuit solvers and SETI metrics computation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cohezion.physics.quantum.peaked_solver import PeakedCircuitSolver

from cohezion.physics.quantum.utils import compute_seti_metrics, reconstruct_site_map

__all__ = [
    "PeakedCircuitSolver",
    "reconstruct_site_map",
    "compute_seti_metrics",
]


def __getattr__(name: str):
    if name == "PeakedCircuitSolver":
        from cohezion.physics.quantum.peaked_solver import PeakedCircuitSolver

        return PeakedCircuitSolver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
