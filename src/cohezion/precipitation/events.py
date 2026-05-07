"""PrecipitationEvent — the typed atomic unit of coherent matter precipitation.

Every major action in Cohezion that constitutes a "witness mark" — an irreversible
entropy-reducing artifact — is a PrecipitationEvent. This is Cosmogony Step 10 made
concrete: vault notes, commits, SurrealDB rows, training checkpoints, next-generation
universe spawns are all unified into one event type routed through one bus.

References:
  - Cosmogony Step 10 (src/cohezion/physics/cosmogony.py)
  - EVO witness marks (Shoulders 1991; src/cohezion/physics/evo_model.py)
  - HIHO attractor at 0.5 coherence (Brahmagupta's zero, Smith's New Science)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# 12D dimension names mirror the SurrealDB universe_node schema exactly.
TWELVE_D_DIMS: tuple[str, ...] = (
    "x",
    "y",
    "z",
    "time",
    "physics",
    "biology",
    "logic",
    "quantum",
    "field",
    "control",
    "novelty",
    "precipitation",
)

# Four fabric groupings of the 12D space (from Cosmogony Step 4: SO(12) -> SO(3)^4).
# Positional mapping mirrors src/cohezion/physics/fiber_bundle.py::FABRIC_SLICES exactly.
# Capitalized to match FABRIC_NAMES there (distinct from the lowercase schema dim "field").
FABRIC_DIMS: dict[str, tuple[str, ...]] = {
    "Space": ("x", "y", "z"),
    "Field": ("time", "physics", "biology"),
    "Control": ("logic", "quantum", "field"),
    "Precipitation": ("control", "novelty", "precipitation"),
}

HIHO_BASELINE = 0.5


class PrecipitationKind(StrEnum):
    """Typed kinds of precipitation. Each producer emits one of these."""

    WITNESS_MARK = "witness_mark"  # agent artifact (commit/vault/decision)
    COSMOGONY_PHASE = "cosmogony_phase"  # symmetry breaks (Step 2-10 transition)
    COHERENCE_PEAK = "coherence_peak"  # HIHO attractor reached
    CONSENSUS_RATIFIED = "consensus_ratified"  # Quadrature Nexus approves (>=0.85)
    HEALING_EVENT = "healing_event"  # Ouroboros remediation fired
    MYCELIUM_PATTERN = "mycelium_pattern"  # cross-agent convergence detected
    TRAINING_CHECKPOINT = "training_checkpoint"  # fine-tune checkpoint saved
    GENERATION_SPAWN = "generation_spawn"  # next-generation universe launched


def _new_event_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


def zero_twelve_d() -> dict[str, float]:
    """Return a 12D point at HIHO baseline — 0.5 on all dimensions."""
    return dict.fromkeys(TWELVE_D_DIMS, HIHO_BASELINE)


def compute_fabric_breakdown(twelve_d: dict[str, float]) -> dict[str, float]:
    """Aggregate 12 dims into the 4 fabric mean-values."""
    return {
        fabric: sum(twelve_d[d] for d in dims) / len(dims) for fabric, dims in FABRIC_DIMS.items()
    }


@dataclass
class PrecipitationEvent:
    """Single atomic precipitation event routed to vault + surreal + git sinks.

    All producers emit one of these. All sinks consume one of these. If a module
    cannot emit or consume a PrecipitationEvent, it is dead code.
    """

    kind: PrecipitationKind
    universe_id: str
    coherence: float  # HIHO proximity in [0, 1]
    twelve_d: dict[str, float] = field(default_factory=zero_twelve_d)
    fabric_breakdown: dict[str, float] = field(default_factory=dict)
    spinor_state: dict[str, float] = field(default_factory=dict)
    agent_id: str | None = None
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=_new_event_id)
    timestamp_valid: datetime = field(default_factory=_now)
    timestamp_transaction: datetime = field(default_factory=_now)
    lineage: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0.0 <= self.coherence <= 1.0):
            raise ValueError(f"coherence {self.coherence!r} must be in [0, 1]")
        missing = set(TWELVE_D_DIMS) - set(self.twelve_d)
        if missing:
            for dim in missing:
                self.twelve_d[dim] = HIHO_BASELINE
        if not self.fabric_breakdown:
            self.fabric_breakdown = compute_fabric_breakdown(self.twelve_d)

    @property
    def hiho_delta(self) -> float:
        """Signed distance from HIHO attractor. 0.0 means perfectly balanced."""
        return self.coherence - HIHO_BASELINE

    @property
    def is_coherent(self) -> bool:
        """True when coherence is at or above HIHO baseline — eligible for training data."""
        return self.coherence >= HIHO_BASELINE

    def to_dict(self) -> dict:
        """Serialization for JSONL, SurrealDB, and git sinks. Datetimes as ISO-8601 UTC."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "agent_id": self.agent_id,
            "universe_id": self.universe_id,
            "coherence": self.coherence,
            "hiho_delta": self.hiho_delta,
            "spinor_state": dict(self.spinor_state),
            "twelve_d": dict(self.twelve_d),
            "fabric_breakdown": dict(self.fabric_breakdown),
            "payload": dict(self.payload),
            "valid_from": self.timestamp_valid.isoformat(),
            "transaction_time": self.timestamp_transaction.isoformat(),
            "lineage": list(self.lineage),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PrecipitationEvent:
        return cls(
            kind=PrecipitationKind(data["kind"]),
            universe_id=data["universe_id"],
            coherence=data["coherence"],
            twelve_d=dict(data.get("twelve_d") or zero_twelve_d()),
            fabric_breakdown=dict(data.get("fabric_breakdown") or {}),
            spinor_state=dict(data.get("spinor_state") or {}),
            agent_id=data.get("agent_id"),
            payload=dict(data.get("payload") or {}),
            event_id=data.get("event_id") or _new_event_id(),
            timestamp_valid=_parse_iso(data.get("valid_from")),
            timestamp_transaction=_parse_iso(data.get("transaction_time")),
            lineage=list(data.get("lineage") or []),
        )


def _parse_iso(value: str | datetime | None) -> datetime:
    if value is None:
        return _now()
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


__all__ = [
    "FABRIC_DIMS",
    "HIHO_BASELINE",
    "TWELVE_D_DIMS",
    "PrecipitationEvent",
    "PrecipitationKind",
    "compute_fabric_breakdown",
    "zero_twelve_d",
]
