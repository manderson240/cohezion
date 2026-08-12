"""Core contracts for AutoHarness zero-cost verifiers and 12D Manifold states.

Enforces deterministic action validation, static verification result schemas,
and 12D Poincaré hyper-space vector invariants.

RESTORED 2026-08-12 from commit 66f5186d5, byte-identical.

WHY: this module is absent from this branch while THIRTEEN modules import
``PoincarePoint`` from it — including ``physics/j_space_manifold.py``,
``physics/poincare_manifold.py``, ``physics/tensor_calculus.py``,
``physics/fiber_connection.py`` and ``physics/ctac_engine.py``. Every one of them was
UNIMPORTABLE here: ``ModuleNotFoundError: No module named 'cohezion.contracts'``.

That is not a dormancy finding — the implementations are present and substantial. It is a
missing dependency that silently disabled the entire J-space / Poincaré-manifold surface on
this branch. Nothing reported it because nothing imported those modules in the test paths
that run here, so the failure was invisible until something tried to use them.

Stdlib-only (math, abc, dataclasses, typing), 76 lines, no further dependencies — so
restoring it is additive and cannot regress anything that currently passes.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Immutable outcome of a zero-cost action verification."""

    valid: bool
    score: float  # 0.0 to 1.0
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    @classmethod
    def success(
        cls,
        score: float = 1.0,
        metadata: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
    ) -> VerificationResult:
        return cls(valid=True, score=score, metadata=metadata or {}, duration_ms=duration_ms)

    @classmethod
    def failure(
        cls,
        errors: list[str] | tuple[str, ...],
        score: float = 0.0,
        duration_ms: float = 0.0,
    ) -> VerificationResult:
        return cls(valid=False, score=score, errors=tuple(errors), duration_ms=duration_ms)


class CodeAsAction(ABC):
    """Abstract base class for all code-as-action components."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the action."""
        ...

    @abstractmethod
    def verify(self) -> VerificationResult:
        """Deterministically verify action safety without side effects."""
        ...


@runtime_checkable
class Verifier(Protocol):
    """Protocol for static and runtime verifiers."""

    def verify_code(self, source_code: str) -> VerificationResult: ...


@dataclass(frozen=True, slots=True)
class PoincarePoint:
    """N-Dimensional Poincaré-ball point coordinates (12D, 16D, 26D, 32D, 256D, 2048D)."""

    coords: tuple[float, ...]
    dim: int = 12

    def __post_init__(self) -> None:
        actual_dim = len(self.coords)
        if self.dim != actual_dim:
            object.__setattr__(self, "dim", actual_dim)

        norm_sq = sum(c * c for c in self.coords)
        if norm_sq >= 1.0:
            raise ValueError(
                f"PoincarePoint ({self.dim}D) must lie strictly inside the unit ball "
                f"(norm^2={norm_sq:.4f} >= 1.0)"
            )

    @property
    def norm(self) -> float:
        return math.sqrt(sum(c * c for c in self.coords))
