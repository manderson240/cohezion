"""Device-aware residency census for the Lemonade OmniRouter (:13305).

`lemonade_health.probe_lemonade()` is the fleet-level oracle (FT1): it answers
"is the router up, are recipes alive, are there ctx hazards". It is deliberately
*device-blind* -- it counts models by TYPE (llm/embedding/tts) via `max_models`.

This module answers the orthogonal question the 24/7 multi-silicon goal needs:
**which silicon is each model actually occupying, and which ones are safe to move?**

Lemonade 11.8.1 reports per-model `device`, `pinned`, `is_busy`, `is_streaming`,
`slot_pool`, `residency_class` and `watchdog_reset`. None of those fields were
parsed anywhere in the codebase before this module, which meant every "NPU tier"
/ "iGPU tier" routing decision named a tier without ever verifying the model
landed on that silicon.

Safety posture is fail-closed: a model is evictable only when we can positively
prove it is idle, unpinned and healthy. Anything unknown is treated as pinned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


__all__ = [
    "DeviceOccupancy",
    "ResidentModel",
    "SiliconCensus",
    "normalize_device",
    "parse_census",
]

# Lemonade reports raw device strings; Strix Halo exposes XDNA2 as "npu",
# the RDNA3.5 integrated GPU as "gpu", and AVX-512 cores as "cpu".
# We normalise "gpu" -> "igpu" ONLY as a display label; `raw_device` is
# always preserved so a future dGPU is never silently mislabelled.
_DEVICE_ALIASES: dict[str, str] = {
    "npu": "npu",
    "gpu": "igpu",
    "igpu": "igpu",
    "cpu": "cpu",
}

# ctx_size sentinels meaning "no explicit cap was set". These are NOT the same
# hazard, and conflating them (as an earlier revision did) overstates one and
# understates the other:
#
#   0   The documented Strix Halo hard-hang crasher (harness N3): a 35B model at
#       ctx_size=0 mapped ~120 GB of GTT aperture and required a cold boot.
#
#  -1   Lemonade's "auto" sentinel. MEASURED 2026-08-29: loading gemma3-1b-FLM
#       with no explicit ctx_size under a global default of -1 produced
#       `--ctx-len 32768`, exactly the model's own `max_context_window`. So -1
#       means "use the model maximum", NOT an unbounded mapping.
#
# -1 is therefore a *policy* risk rather than a crash: the KV cache is sized by
# whatever window the model advertises. Harmless on a 1B/32K model; serious on a
# 27B model advertising a 262144-token window, where nobody chose that number.
_CTX_CRASHER: frozenset[int] = frozenset({0})
_CTX_UNCAPPED: frozenset[int] = frozenset({-1})

# `backend_health` is an open vocabulary -- observed live: "ready", "busy".
# We deliberately use an asymmetric pair of sets rather than one predicate:
#
#   * ALERTING is conservative about FALSE POSITIVES. Only states we know are
#     bad raise `unhealthy`; an unrecognised state does NOT page anyone. A
#     health check that cries wolf trains operators to ignore it.
#   * EVICTION is conservative about FALSE NEGATIVES. Only states we know are
#     safe permit eviction; an unrecognised state is treated as in-use.
#
# Both directions are "be careful", but they resolve unknown states oppositely,
# which is why one boolean cannot serve both.
_HEALTH_KNOWN_BAD: frozenset[str] = frozenset(
    {"error", "failed", "dead", "crashed", "unhealthy", "stopped"}
)
_HEALTH_SAFE_TO_EVICT: frozenset[str] = frozenset({"ready"})


def normalize_device(raw: str | None) -> str:
    """Map a lemonade `device` string to a canonical silicon label.

    Unknown or missing devices return "unknown" rather than guessing -- a
    wrong device label would silently corrupt every routing decision built
    on top of this census.
    """
    if not raw:
        return "unknown"
    return _DEVICE_ALIASES.get(raw.strip().lower(), "unknown")


@dataclass(frozen=True)
class ResidentModel:
    """One model currently resident on a specific piece of silicon."""

    name: str
    raw_device: str
    device: str
    type: str = "llm"
    recipe: str = ""
    ctx_size: int | None = None
    pinned: bool = False
    is_busy: bool = False
    is_streaming: bool = False
    last_use: float = 0.0
    slot_pool: str = ""
    residency_class: str = ""
    watchdog_reset: bool = False
    backend_alive: bool = True
    backend_health: str = ""
    pid: int = 0
    size_gb: float = 0.0

    @property
    def ctx_crasher(self) -> bool:
        """ctx_size=0 -- the documented Strix Halo hard-hang (harness N3)."""
        return self.ctx_size in _CTX_CRASHER

    @property
    def ctx_uncapped(self) -> bool:
        """No explicit ctx cap: the KV cache is sized by the model's own window."""
        return self.ctx_size is None or self.ctx_size in _CTX_UNCAPPED

    @property
    def ctx_hazard(self) -> bool:
        """Either failure mode: an outright crasher, or an unchosen KV size."""
        return self.ctx_crasher or self.ctx_uncapped

    @property
    def ctx_risk(self) -> str:
        """'crasher' | 'uncapped' | 'ok' -- lets callers rank by severity."""
        if self.ctx_crasher:
            return "crasher"
        if self.ctx_uncapped:
            return "uncapped"
        return "ok"

    @property
    def in_flight(self) -> bool:
        """True when the model is actively serving a request."""
        return self.is_busy or self.is_streaming

    @property
    def evictable(self) -> bool:
        """True only when eviction is provably safe.

        Fail-closed: requires positive evidence of idleness AND health.
        A pinned, busy, streaming or unhealthy backend is never evictable.
        """
        if self.pinned or self.in_flight:
            return False
        # Normalised the same way as `unhealthy`. An earlier revision compared
        # the RAW string here while `unhealthy` used .strip().lower(), so on an
        # open vocabulary a server returning "Ready" made every model
        # permanently non-evictable and `evictable_gb` reported 0.00 GB on a
        # fully idle fleet.
        health = self.backend_health.strip().lower()
        return self.backend_alive and health in _HEALTH_SAFE_TO_EVICT

    @property
    def unhealthy(self) -> bool:
        """True only for states we positively know are bad.

        `backend_health == "busy"` means the model is serving a request -- a
        healthy, expected state. Flagging it (as an earlier revision did) emits
        a CRITICAL alert on every poll during normal operation.
        """
        if not self.backend_alive:
            return True
        return self.backend_health.strip().lower() in _HEALTH_KNOWN_BAD


@dataclass(frozen=True)
class DeviceOccupancy:
    """What a single piece of silicon is currently carrying."""

    device: str
    models: tuple[ResidentModel, ...] = ()

    @property
    def count(self) -> int:
        return len(self.models)

    @property
    def resident_gb(self) -> float:
        return round(sum(m.size_gb for m in self.models), 3)

    @property
    def busy(self) -> bool:
        return any(m.in_flight for m in self.models)

    @property
    def idle(self) -> bool:
        """True when silicon holds models but none are serving -- spare capacity."""
        return self.count > 0 and not self.busy

    @property
    def evictable_gb(self) -> float:
        return round(sum(m.size_gb for m in self.models if m.evictable), 3)


@dataclass(frozen=True)
class SiliconCensus:
    """Device-resolved snapshot of everything resident on the OmniRouter."""

    checked_at: float
    residents: tuple[ResidentModel, ...] = ()
    by_device: dict[str, DeviceOccupancy] = field(default_factory=dict)

    @property
    def devices_engaged(self) -> set[str]:
        """Silicon that is actively serving right now (not merely loaded)."""
        return {d for d, occ in self.by_device.items() if occ.busy}

    @property
    def devices_loaded(self) -> set[str]:
        """Silicon carrying at least one resident model."""
        return {d for d, occ in self.by_device.items() if occ.count > 0}

    @property
    def ctx_hazards(self) -> tuple[ResidentModel, ...]:
        return tuple(m for m in self.residents if m.ctx_hazard)

    @property
    def watchdog_resets(self) -> tuple[ResidentModel, ...]:
        """Models the server itself had to restart -- a 24/7 instability signal."""
        return tuple(m for m in self.residents if m.watchdog_reset)

    @property
    def unhealthy(self) -> tuple[ResidentModel, ...]:
        return tuple(m for m in self.residents if m.unhealthy)

    @property
    def total_resident_gb(self) -> float:
        return round(sum(m.size_gb for m in self.residents), 3)

    def occupancy(self, device: str) -> DeviceOccupancy:
        """Occupancy for a device, empty (not KeyError) when nothing is resident."""
        return self.by_device.get(device, DeviceOccupancy(device=device))

    @property
    def summary(self) -> str:
        parts = [
            f"{d}:{occ.count}({occ.resident_gb:g}GB{'*' if occ.busy else ''})"
            for d, occ in sorted(self.by_device.items())
        ]
        return (
            f"silicon[{' '.join(parts) or 'empty'}] "
            f"total={self.total_resident_gb:g}GB "
            f"hazards={len(self.ctx_hazards)} "
            f"watchdog={len(self.watchdog_resets)}"
        )


def _size_index(catalog: list[dict[str, Any]] | None) -> dict[str, float]:
    """Build model_id -> size_gb from a `/api/v1/models` catalog payload.

    The health endpoint does not report model size, so byte-budget planning
    requires joining against the catalog. Missing sizes stay 0.0 rather than
    being estimated -- a fabricated size would corrupt the budget silently.
    """
    index: dict[str, float] = {}
    for entry in catalog or []:
        model_id = entry.get("id")
        size = entry.get("size")
        if isinstance(model_id, str) and isinstance(size, (int, float)):
            index[model_id] = float(size)
    return index


def parse_census(
    health_payload: dict[str, Any],
    catalog: list[dict[str, Any]] | None = None,
    checked_at: float = 0.0,
) -> SiliconCensus:
    """Build a device-resolved census from a `/api/v1/health` payload.

    `catalog` is the `data` list from `/api/v1/models`; supplying it enables
    byte-budget fields. Without it sizes are 0.0 and counts still work.
    """
    sizes = _size_index(catalog)
    residents: list[ResidentModel] = []

    for entry in health_payload.get("all_models_loaded", []) or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("model_name", "?"))
        raw_device = str(entry.get("device", "") or "")
        opts = entry.get("recipe_options") or {}
        ctx = opts.get("ctx_size") if isinstance(opts, dict) else None

        residents.append(
            ResidentModel(
                name=name,
                raw_device=raw_device,
                device=normalize_device(raw_device),
                type=str(entry.get("type", "llm")),
                recipe=str(entry.get("recipe", "")),
                ctx_size=ctx if isinstance(ctx, int) else None,
                pinned=bool(entry.get("pinned", False)),
                is_busy=bool(entry.get("is_busy", False)),
                is_streaming=bool(entry.get("is_streaming", False)),
                last_use=float(entry.get("last_use", 0) or 0),
                slot_pool=str(entry.get("slot_pool", "")),
                residency_class=str(entry.get("residency_class", "")),
                watchdog_reset=bool(entry.get("watchdog_reset", False)),
                backend_alive=bool(entry.get("backend_alive", True)),
                backend_health=str(entry.get("backend_health", "")),
                pid=int(entry.get("pid", 0) or 0),
                size_gb=sizes.get(name, 0.0),
            )
        )

    grouped: dict[str, list[ResidentModel]] = {}
    for model in residents:
        grouped.setdefault(model.device, []).append(model)

    by_device = {
        device: DeviceOccupancy(device=device, models=tuple(models))
        for device, models in grouped.items()
    }
    return SiliconCensus(
        checked_at=checked_at,
        residents=tuple(residents),
        by_device=by_device,
    )
