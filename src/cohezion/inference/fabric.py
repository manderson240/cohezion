"""Unified-fabric memory accounting for the Strix Halo Lemonade fleet.

The box exposes ONE 122 GiB unified DDR pool and three accelerators that draw
on it through physically different channels:

* **NPU (XDNA2, FLM runtime)** — model weights land in dedicated SRAM beside
  the compute tiles, NOT in the UMA pool; the FLM SRAM allocator caps out at
  ~15.6 GiB, so the NPU budget line is 16.0 GiB / 5 resident models.
* **iGPU (RDNA3.5, llamacpp-vulkan)** — loads pin pages into the GTT
  aperture. This is THE OOM CHANNEL: on 2026-09-14 a concurrent-load race
  pinned 61-62 GiB of GTT and the box OOM'd into a cold-boot recovery. The
  iGPU budget line is therefore the tightest byte gate: 48.0 GiB / 2 resident.
* **CPU (llamacpp-cpu)** — plain anonymous pages in the pool: 24.0 GiB / 3
  resident. CLOUD models load nothing locally and have no budget line.

The per-backend budgets are ACCOUNTING LINES over the one shared pool, not
separate pools — every load ultimately consumes the same physical RAM. So in
addition to the per-backend gates, admission enforces one system-wide floor:
``/proc/meminfo`` ``MemAvailable`` must stay above 16 GiB after the load
(mirroring ``hotswap.RAM_FLOOR_GB``).

Safety posture is fail-closed everywhere, mirroring ``inference/hotswap``:

* unknown candidate size   -> refuse the blind cold load,
* ``/api/v1/health`` down/degraded/malformed -> residency unverifiable -> refuse,
* ``/proc/meminfo`` unreadable -> free RAM unverifiable -> refuse,
* ctx_size <= 0            -> refuse (unbounded/auto KV is the documented
  2026-06-09 hard-freeze vector).

Every refusal is a ``(False, human-readable reason)`` tuple; the module never
raises. All HTTP goes through the module-level :func:`_get` helper (urllib,
short timeouts) so tests can stub the seam with
``monkeypatch.setattr(fabric, "_get", ...)``.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cohezion.inference.hotswap import implausible_size_gb, params_b_from_name


logger = logging.getLogger(__name__)

LEMONADE_BASE = "http://localhost:13305"
DEFAULT_TIMEOUT_S = 3.0  # short: admission runs on the load path, not the hot path
RAM_FLOOR_GB = 16.0  # mirrors hotswap.RAM_FLOOR_GB — never consume the last 16 GB
MAX_CTX = 16384  # mirrors hotswap.MAX_CTX; callers may request less, never more
MIN_KV_FRACTION = 0.25  # floor on the prorated KV overhead at small ctx_size
_BYTES_SIZE_THRESHOLD = 100_000.0  # catalog "size" above this is bytes, not GB

__all__ = [
    "BACKEND_BUDGETS",
    "LEMONADE_BASE",
    "RAM_FLOOR_GB",
    "Backend",
    "BackendBudget",
    "admission_ok",
    "backend_for_model",
    "resident_by_backend",
]


class Backend(StrEnum):
    """The three local silicon lanes plus cloud, as Lemonade runtime names."""

    NPU = "flm"
    IGPU = "llamacpp-vulkan"
    CPU = "llamacpp-cpu"
    CLOUD = "cloud"


@dataclass
class BackendBudget:
    """One accounting line over the unified pool: count cap + byte budget."""

    backend: Backend
    max_resident: int
    budget_gb: float


# Per-backend budgets over the one 122G pool. CLOUD is deliberately absent:
# cloud models never load locally, so there is nothing to account for.
#   NPU  5 / 16.0G — FLM NPU SRAM allocator caps at ~15.6G per load.
#   IGPU 2 / 48.0G — the GTT gate: 61-62G pinned GTT caused the 2026-09-14 OOM.
#   CPU  3 / 24.0G — plain pages, but a count cap still keeps the pool honest.
BACKEND_BUDGETS: dict[Backend, BackendBudget] = {
    Backend.NPU: BackendBudget(Backend.NPU, 5, 16.0),
    Backend.IGPU: BackendBudget(Backend.IGPU, 2, 48.0),
    Backend.CPU: BackendBudget(Backend.CPU, 3, 24.0),
}


def backend_for_model(model_name: str) -> Backend:
    """Classify a model name onto its backend lane.

    Rules, in precedence order:

    1. an ``FLM`` tag anywhere in the name (``-FLM`` suffix is the convention;
       MTP/sibling variants carry ``-FLM-``) -> NPU,
    2. a ``:cloud`` / ``-cloud`` suffix -> CLOUD,
    3. ``-CPU`` in the name (e.g. ``Phi-4-mini-3.8B-CPU-32T``) -> CPU,
    4. everything else — the GGUF/llamacpp convention — -> IGPU.
    """
    lowered = (model_name or "").lower()
    if "flm" in lowered:
        return Backend.NPU
    if lowered.endswith(":cloud") or lowered.endswith("-cloud"):
        return Backend.CLOUD
    if "-cpu" in lowered:
        return Backend.CPU
    return Backend.IGPU


def _get(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict[str, Any] | None:
    """GET ``url`` and return the parsed JSON object, or ``None`` on ANY failure.

    This is the module's single HTTP seam: short timeout, loopback Lemonade
    base, and every failure (unreachable, non-JSON, non-object payload)
    collapses to ``None`` so callers can fail closed instead of raising.
    Tests stub it with ``monkeypatch.setattr(fabric, "_get", ...)``.
    """
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode(errors="ignore"))
    except Exception as exc:
        logger.debug("fabric: GET %s failed: %s", url, exc)
        return None
    return payload if isinstance(payload, dict) else None


def _resident_map(lemonade_base: str) -> dict[Backend, list[str]] | None:
    """Resident model names grouped by backend, or ``None`` when health is degraded.

    ``None`` (unreachable, degraded, or malformed health answer) is distinct
    from ``{}`` (server answered, fleet empty) — admission must refuse on the
    former and proceed on the latter. An entry counts as resident when it
    carries a non-empty ``model_name`` and has not explicitly reported
    ``loaded: false``.
    """
    state = _resident_state(lemonade_base)
    return None if state is None else state


def _resident_state(lemonade_base: str) -> dict[Backend, list[str]] | None:
    """Residency view that DISTINGUISHES degraded from answered-and-empty.

    Returns ``None`` when the health endpoint is unreachable, answers with a
    non-object payload, or answers with a malformed body (missing/non-list
    ``all_models_loaded``) — residency is then unverifiable, so admission must
    fail closed. Returns the (possibly empty) per-backend grouping only when
    health answered with a well-formed body. Tests stub ``fabric._get``; this
    seam keeps that contract.
    """
    health = _get(f"{lemonade_base.rstrip('/')}/api/v1/health")
    if health is None:
        return None
    entries = health.get("all_models_loaded")
    if not isinstance(entries, list):
        logger.warning(
            "fabric: /api/v1/health answered but 'all_models_loaded' is malformed "
            "(%s) — residency unverifiable, failing closed",
            type(entries).__name__,
        )
        return None
    out: dict[Backend, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("loaded") is False:
            continue
        name = entry.get("model_name")
        if not isinstance(name, str) or not name:
            continue
        out.setdefault(backend_for_model(name), []).append(name)
    return out


def resident_by_backend(lemonade_base: str = LEMONADE_BASE) -> dict[Backend, list[str]]:
    """Resident model names grouped by backend, from ``GET /api/v1/health``.

    Degraded (health unreachable or malformed) -> ``{}``; never raises. Models
    are classified by :func:`backend_for_model`, not by Lemonade's ``device``
    field, so the census and the admission gate always agree on lanes. Census
    consumers that need to DISTINGUISH degraded from a truly empty fleet
    should call :func:`_resident_state` (``None`` = degraded) instead.
    """
    return _resident_state(lemonade_base) or {}


def _kv_overhead_gb(weights_gb: float, ctx_size: int) -> float:
    """KV-cache overhead estimate, prorated from hotswap's flat rule.

    ``hotswap._kv_overhead_gb`` charges 3.0 GB (weights > 10 GB) or 1.0 GB at
    its MAX_CTX of 16384. This module knows the caller's ``ctx_size``, so the
    same flat overhead is scaled by ``ctx_size / 16384``, floored at
    :data:`MIN_KV_FRACTION` (even a tiny context maps scheduling buffers).
    """
    base = 3.0 if weights_gb > 10.0 else 1.0
    fraction = min(1.0, max(MIN_KV_FRACTION, ctx_size / MAX_CTX))
    return round(base * fraction, 2)


def _mem_available_gb() -> float | None:
    """``MemAvailable`` in GiB from /proc/meminfo, or ``None`` when unreadable.

    Mirrors ``hotswap.free_gb_or_none`` (kiB -> GiB). The admission path must
    distinguish "0 GB free" from "cannot read" only insofar as BOTH refuse —
    there is no abstain polarity here because nothing evicts from this module.
    """
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1048576
    except Exception:
        pass
    return None


def _catalog_sizes(lemonade_base: str) -> dict[str, float]:
    """Model sizes in GB from ``GET /api/v1/models``, empty when unavailable.

    Sizes are treated as GB (hotswap's convention). A value above
    ``_BYTES_SIZE_THRESHOLD`` cannot be a real GB weight figure and is
    converted from bytes, so either server convention lands in GB.
    """
    payload = _get(f"{lemonade_base.rstrip('/')}/api/v1/models")
    if payload is None:
        return {}
    data = payload.get("data") or []
    if not isinstance(data, list):
        return {}
    out: dict[str, float] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        size = entry.get("size")
        if (
            not isinstance(model_id, str)
            or not model_id
            or isinstance(size, bool)
            or not isinstance(size, (int, float))
        ):
            continue
        gb = float(size)
        if gb > _BYTES_SIZE_THRESHOLD:
            gb /= 1e9
        out[model_id] = gb
    return out


def admission_ok(
    model_name: str,
    ctx_size: int,
    lemonade_base: str = LEMONADE_BASE,
) -> tuple[bool, str]:
    """Unified admission gate for one model load over the unified pool.

    Checks, in order:

    1. the target backend's ``max_resident`` is not exceeded AFTER adding this
       model (per-backend count cap over one pool),
    2. the backend's ``budget_gb`` has room for weights + prorated KV
       (size from ``/api/v1/models`` when available; unknown size = fail
       CLOSED, mirroring ``hotswap``'s refusal of blind cold loads),
    3. system free RAM (``/proc/meminfo`` ``MemAvailable``) stays above the
       16 GB floor after the load.

    CLOUD models load nothing locally and are admitted without any HTTP.
    A model that is already resident is a no-op admission (mirrors HS1).

    Returns ``(ok, reason)`` with a human-readable reason; never raises —
    every internal failure is folded into a fail-closed refusal.
    """
    try:
        return _admission_check(model_name, ctx_size, lemonade_base)
    except Exception as exc:  # pragma: no cover - the gate must never raise
        logger.warning("fabric: admission check raised unexpectedly: %s", exc)
        return False, f"admission gate internal error: {exc}"


def _admission_check(
    model_name: str,
    ctx_size: int,
    lemonade_base: str,
) -> tuple[bool, str]:
    if not isinstance(model_name, str) or not model_name.strip():
        return False, "refusing load: model name is empty"

    if isinstance(ctx_size, bool) or not isinstance(ctx_size, (int, float)) or ctx_size <= 0:
        return False, (
            f"refusing load of {model_name}: invalid ctx_size {ctx_size!r} — unbounded/auto KV "
            "is the documented hard-freeze vector; pass a bounded ctx_size"
        )
    ctx = min(int(ctx_size), MAX_CTX)

    backend = backend_for_model(model_name)
    if backend is Backend.CLOUD:
        return True, f"{model_name} is a cloud model — nothing loads locally, admission granted"

    residents = _resident_state(lemonade_base)
    if residents is None:
        return False, (
            f"refusing load of {model_name}: Lemonade /api/v1/health is degraded — "
            "unreachable or malformed answer means residency cannot be verified "
            "(fail closed)"
        )
    names_now = {name for names in residents.values() for name in names}
    if model_name in names_now:
        return True, f"{model_name} is already resident — admission is a no-op"

    budget = BACKEND_BUDGETS[backend]
    current = residents.get(backend, [])
    if len(current) + 1 > budget.max_resident:
        return False, (
            f"refusing load of {model_name}: {backend.name} residency cap reached — "
            f"{len(current)}/{budget.max_resident} already resident "
            f"({', '.join(current) or 'none'}); unload one first"
        )

    sizes = _catalog_sizes(lemonade_base)
    weights = sizes.get(model_name)
    if weights is None:
        return False, (
            f"refusing load of {model_name}: unknown model size — the catalog reports no size "
            "metadata for it and a blind cold load cannot be gated (fail closed, mirrors hotswap)"
        )
    if implausible_size_gb(model_name, weights):
        params = params_b_from_name(model_name)
        param_label = f"{params:g}B" if params is not None else "unknown-param"
        return False, (
            f"refusing load of {model_name}: implausible catalog size {weights:.2f}GB for a "
            f"{param_label} model — bad metadata defeats the budget gate (fail closed)"
        )
    kv = _kv_overhead_gb(weights, ctx)
    needed = round(weights + kv, 2)

    resident_sizes = [sizes.get(name) for name in current]
    used = round(sum(s for s in resident_sizes if s is not None), 2)
    unknown = sum(1 for s in resident_sizes if s is None)
    room = round(budget.budget_gb - used, 2)
    if needed > room:
        unknown_note = (
            f"; {unknown} resident size(s) unknown, counted as 0 — the system RAM floor still applies"
            if unknown
            else ""
        )
        return False, (
            f"refusing load of {model_name}: {backend.name} budget exceeded — need {needed:.2f}GB "
            f"(weights {weights:.2f}GB + KV {kv:.2f}GB at ctx {ctx}), only {room:.2f}GB of "
            f"{budget.budget_gb:.1f}GB free ({len(current)} resident using {used:.2f}GB"
            f"{unknown_note})"
        )

    available = _mem_available_gb()
    if available is None:
        return False, (
            f"refusing load of {model_name}: /proc/meminfo MemAvailable is unreadable — "
            "free RAM cannot be verified (fail closed)"
        )
    projected = round(available - needed, 2)
    if projected < RAM_FLOOR_GB:
        return False, (
            f"refusing load of {model_name}: system RAM floor — MemAvailable {available:.2f}GB "
            f"- {needed:.2f}GB = {projected:.2f}GB would fall below the {RAM_FLOOR_GB:.0f}GB floor"
        )
    return True, (
        f"admitted {model_name} on {backend.name}: residency {len(current) + 1}/"
        f"{budget.max_resident}, {needed:.2f}GB against {room:.2f}GB budget headroom, "
        f"projected free RAM {projected:.2f}GB stays above the {RAM_FLOOR_GB:.0f}GB floor"
    )
