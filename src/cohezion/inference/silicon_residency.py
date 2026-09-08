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
    "ModelStorage",
    "ResidentModel",
    "SiliconCensus",
    "normalize_device",
    "parse_census",
    "parse_storage",
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


# ---------------------------------------------------------------------------
# Model-store capacity
# ---------------------------------------------------------------------------
#
# The census above answers "what is in MEMORY". This section answers the
# orthogonal 24/7 question memory occupancy cannot see: **is there still room on
# DISK to pull or re-pull a model?**
#
# Measured 2026-08-30 on the live router: the store at
# /var/lib/lemonade/.cache/huggingface/hub reported 764 GiB used of 769 GiB,
# leaving 5.57 GiB -- less than a single mid-size GGUF. Nothing in the fleet
# stack noticed, because every existing probe reads memory residency, and the
# store is mode 0750 under `User=lemonade` so an unprivileged `du` silently
# skips it. A store that cannot accept a write does not fail loudly; it fails as
# a mid-download error much later, on whatever job happens to need a model.
#
# WHY ABSOLUTE FREE BYTES, NOT THE FRACTION, IS THE PRIMARY ALERT
# -----------------------------------------------------------------
# The obvious guard is used/total. It is the wrong primary signal on ZFS, and
# the reason is structural rather than a matter of threshold tuning:
#
#   * `total` here is not a fixed capacity. ZFS reports statvfs as
#     used + available, and `available` is pool-wide free space minus the ~3.2%
#     "slop space" ZFS withholds so metadata ops and `zfs destroy` can never
#     themselves hit ENOSPC. So the DENOMINATOR SHRINKS as the pool fills.
#   * `available` is pool-wide, so a dataset's fraction climbs when some OTHER
#     dataset grows. The fraction conflates "this store is large" with "the
#     pool is full" -- two different operational situations.
#   * Snapshots, refreservation and copies= all charge space that the fraction
#     does not attribute to anything you can see or reclaim here.
#
# Absolute free bytes has none of those problems and is the number that decides
# the only question the caller actually has: will the next model fit?
#
# This ordering came out of a three-lane review where the two lanes recommending
# a fractional threshold had, one paragraph earlier, argued the fraction was
# unsound -- and the dissenting lane was the only one whose recommendation
# followed from its own analysis. Recorded because the majority was the weaker
# answer.
#
# The fraction is kept, demoted to a secondary/observability signal, because a
# store at 40% and one at 99% with the same free bytes are genuinely different
# situations to a human reading a dashboard.

# PRIMARY: absolute free space, in GB.
# Critical floor of 10 leaves room for the smallest catalog GGUF (~0.36 GB) plus
# partial-download temp files and metadata; the warning band gives an operator
# roughly one mid-size model (5+ GB) of notice before that.
_STORE_FREE_CRITICAL_GB = 10.0
_STORE_FREE_WARN_GB = 20.0

# SECONDARY (observability): fraction of the store consumed. ZFS allocation
# degrades from first-fit to best-fit past ~90%, so these still mean something
# for write latency -- they are simply not what gates a download.
_STORE_PRESSURE_WARN = 0.90
_STORE_PRESSURE_CRITICAL = 0.97

_BYTES_PER_GB = 1024.0**3


@dataclass(frozen=True)
class ModelStorage:
    """Capacity of the on-disk model store backing the router.

    Sourced from `/api/v1/system-info` -> `model_storage`. Every field defaults
    to 0 so a server that omits the block yields an *unmeasured* store rather
    than a spuriously empty one. `measured` is the guard, and every verdict
    below returns False when it is unset: an unmeasured store is `unknown`,
    never `healthy` and never `critical`. Reporting "0 bytes used, all clear"
    for a store we failed to read is the exact false negative this exists to
    prevent -- the same conflation of "no answer" with "zero" that the byte
    budget in silicon_policy guards against for catalog sizes.
    """

    path: str = ""
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0

    @property
    def measured(self) -> bool:
        """True only when the server actually reported a sized store."""
        return self.total_bytes > 0

    @property
    def free_gb(self) -> float:
        return round(self.free_bytes / _BYTES_PER_GB, 2)

    @property
    def total_gb(self) -> float:
        return round(self.total_bytes / _BYTES_PER_GB, 2)

    @property
    def used_fraction(self) -> float:
        """Occupied fraction in [0, 1]; 0.0 when unmeasured.

        SECONDARY signal only -- see the module note above. On the live payload
        used + free == total exactly, so this is equivalent to 1 - free/total;
        the two forms are not meaningfully different here and no claim is made
        that they diverge. What *does* make the number soft is the denominator:
        `total` is used + pool-wide available, so it moves for reasons that have
        nothing to do with this store. Read it as a dashboard number, and gate
        on `critical` / `warning` instead.
        """
        if not self.measured:
            return 0.0
        return round(self.used_bytes / self.total_bytes, 4)

    # --- PRIMARY verdicts: absolute free space ---

    @property
    def critical(self) -> bool:
        """Too little absolute space left to pull even a small model."""
        return self.measured and self.free_gb < _STORE_FREE_CRITICAL_GB

    @property
    def warning(self) -> bool:
        """Running low: roughly one mid-size model of notice remains.

        Deliberately exclusive of `critical` so the two never fire together --
        a supervisor that emits both for one observation double-alerts, and an
        operator learns to ignore whichever one is noisier.
        """
        if not self.measured:
            return False
        return _STORE_FREE_CRITICAL_GB <= self.free_gb < _STORE_FREE_WARN_GB

    # --- SECONDARY verdicts: fractional pressure (observability only) ---

    @property
    def pressure_warning(self) -> bool:
        if not self.measured:
            return False
        return _STORE_PRESSURE_WARN <= self.used_fraction < _STORE_PRESSURE_CRITICAL

    @property
    def pressure_critical(self) -> bool:
        return self.measured and self.used_fraction >= _STORE_PRESSURE_CRITICAL

    def headroom_for_gb(self, size_gb: float) -> bool | None:
        """Can a model of `size_gb` be pulled? None when the store is unmeasured.

        Tri-state on purpose. `False` means "provably will not fit"; `None`
        means "unknown". A caller that reads unmeasured as `False` blocks
        legitimate work; one that reads it as `True` walks into a mid-download
        ENOSPC. Neither is safe to guess, so the caller must choose explicitly.
        """
        if not self.measured:
            return None
        return self.free_gb >= max(size_gb, 0.0)

    @property
    def summary(self) -> str:
        if not self.measured:
            return "store[unmeasured]"
        return (
            f"store[{self.free_gb:g}GB free / {self.total_gb:g}GB, "
            f"{self.used_fraction * 100:.1f}% used] {self.path or '?'}"
        )


def parse_storage(system_info: dict[str, Any] | None) -> ModelStorage:
    """Extract `model_storage` from a `/api/v1/system-info` payload.

    Tolerant by construction: a missing block, a non-dict block, or non-numeric
    fields all yield an unmeasured `ModelStorage` rather than raising. The
    supervisor polls this every cycle for the life of the process, so a server
    whose payload shape changes across an upgrade must degrade to "unknown"
    rather than crash the daemon that exists to watch it.
    """
    block = (system_info or {}).get("model_storage")
    if not isinstance(block, dict):
        return ModelStorage()

    def _int(key: str) -> int:
        value = block.get(key)
        # bool is an int subclass; accepting it would turn True into 1 byte.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 0
        return int(value) if value >= 0 else 0

    path = block.get("path")
    return ModelStorage(
        path=path if isinstance(path, str) else "",
        total_bytes=_int("total_bytes"),
        used_bytes=_int("used_bytes"),
        free_bytes=_int("free_bytes"),
    )
