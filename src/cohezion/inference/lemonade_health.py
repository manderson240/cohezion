"""Lemonade OmniRouter recipe-aware health probe (stub).

Exports the types and functions consumed by:
  - tests/inference/test_lemonade_health.py
  - tests/inference/test_fleet_recipe_gate.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CtxHazard:
    """A model loaded with ctx_size=0 — a potential OOM crasher."""

    model: str
    recipe: str
    ctx_size: int
    backend_url: str
    pid: int

    def __str__(self) -> str:
        return f"CtxHazard(model={self.model!r}, ctx_size={self.ctx_size}, pid={self.pid})"


@dataclass
class OrphanProcess:
    """A lemonade backend process with no matching loaded model."""

    model: str
    pid: int
    backend_url: str

    def __str__(self) -> str:
        return f"OrphanProcess(model={self.model!r}, pid={self.pid})"


@dataclass
class TypeHeadroom:
    """Slot headroom for a model type (e.g. 'llm', 'image')."""

    type: str
    loaded: int
    max_: int

    @property
    def free(self) -> int:
        return self.max_ - self.loaded

    @property
    def saturated(self) -> bool:
        return self.free <= 0

    def __str__(self) -> str:
        state = "SATURATED" if self.saturated else "ok"
        return f"TypeHeadroom(type={self.type!r}, loaded={self.loaded}/{self.max_}, {state})"


@dataclass
class RecipeProbe:
    """Result of probing a single lemonade recipe endpoint."""

    recipe: str
    ok: bool
    latency_ms: float
    detail: str = ""


@dataclass
class LemonadeHealth:
    """Snapshot of OmniRouter (:13305) health."""

    checked_at: float
    port: int
    version: str
    status: str
    loaded_count: int
    recipe_probes: list[RecipeProbe] = field(default_factory=list)
    headroom: list[TypeHeadroom] = field(default_factory=list)
    ctx_hazards: list[CtxHazard] = field(default_factory=list)
    orphan_processes: list[OrphanProcess] = field(default_factory=list)


def is_lemonade_alive(port: int = 13305, timeout: float = 1.0) -> bool:
    """Return True when the OmniRouter HTTP endpoint is reachable."""
    raise NotImplementedError


def probe_lemonade(port: int = 13305, timeout: float = 5.0) -> LemonadeHealth:
    """Probe the OmniRouter and return a full health snapshot."""
    raise NotImplementedError


def _check_ctx_hazards(models_payload: Any) -> list[CtxHazard]:
    """Extract ctx_size=0 hazards from the /api/v1/models response payload."""
    raise NotImplementedError


def _check_orphans(models_payload: Any) -> list[OrphanProcess]:
    """Detect orphaned backend processes from the /api/v1/models response payload."""
    raise NotImplementedError
