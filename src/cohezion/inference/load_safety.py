"""Freeze-prevention load-safety guard for the local inference fleet.

Why this exists
---------------
On 2026-07-16 the box HARD-FROZE three times because nothing guarded a model
load against RAM/weight over-commit. The specific failure: Mistral-Medium-3.5-128B
IQ4_XS reported catalog ``size = 42.3`` GB but its real on-disk weights were
~69 GB (a 1.63x gap), and the existing pre-load gate approved it purely because
free RAM was above a fixed floor — it never checked whether the *weights* fit.
The sustained mmap page-in storm then drove the box unresponsive.

This module is the additive weight-fit guard that ``oom_guard.pre_load_gate``
lacked. It is deliberately dependency-light and split into pure functions
(``effective_size_gb`` / ``check_load_safe``) that take model metadata + an
available-RAM number as *input* — no network, no /proc — so the decision logic
is unit-testable offline. ``available_ram_gb`` is the one impure helper (reads
/proc/meminfo) and is kept separate from the decision.

Two calibrated constants, both intentionally conservative:

* ``SIZE_SAFETY_FACTOR`` — catalog ``size`` UNDERSTATES real footprint (verified
  1.63x on Mistral-Medium; the factor also absorbs KV-cache / mmproj / GTT
  overhead the catalog omits). Inflate every reported size by this factor.
* ``RAM_FLOOR_GB`` — never plan to consume the last 16 GB (harness N3 discipline).

Decision contract (``check_load_safe``):
  * effective size UNKNOWN (None) => REFUSE — "unknown != fits" was the exact
    bypass that would re-freeze the box; an unverifiable footprint is unsafe.
  * effective size > (available - floor) => REFUSE (weight over-commit).
  * otherwise => proceed.

FLM-recipe (NPU, sub-8B) models carry no catalog ``size`` but are not the
unified-RAM freeze risk that heavy iGPU GGUF loads are; they get a bounded
nominal instead of None so a missing size does not false-refuse a safe NPU load.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


# Never plan to use the last 16 GB of unified memory (harness N3 discipline).
RAM_FLOOR_GB: float = 16.0

# Catalog ``size`` understates real footprint: Mistral-Medium IQ4_XS reported
# 42.3 GB but its weights are ~69 GB on disk (1.63x), and the catalog ignores
# KV-cache/mmproj/GTT overhead. Trusting raw catalog size in the guard would
# have APPROVED the exact model that froze the box. Inflate by this factor.
SIZE_SAFETY_FACTOR: float = 1.7

# FLM/NPU models report no catalog size but are sub-8B by construction (the
# fleet's largest is deepseek-r1-8b ~5 GB). Bound them so a missing size does
# not false-refuse a safe NPU load, while still counting them against the floor.
_FLM_NOMINAL_GB: float = 6.0


def available_ram_gb() -> float:
    """Return MemAvailable from /proc/meminfo in GB (0.0 if unreadable).

    This is the single impure helper — kept out of ``check_load_safe`` so the
    decision logic can be exercised offline with an explicit ``available_gb``.
    """
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        return 0.0
    return 0.0


def _size_of(model_meta: Mapping[str, Any]) -> float | None:
    """Raw reported size in GB from either the catalog (``size``) or a
    ``ModelEntry`` (``size_gb``). A falsy/None value means 'not reported'."""
    raw = model_meta.get("size")
    if raw is None:
        raw = model_meta.get("size_gb")
    try:
        val = float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return None
    return val if val > 0.0 else None


def _recipe_of(model_meta: Mapping[str, Any]) -> str:
    """Recipe/backend string from either the catalog (``recipe``) or a
    ``ModelEntry`` (``runtime_backend``). Lowercased; empty when absent."""
    recipe = model_meta.get("recipe") or model_meta.get("runtime_backend") or ""
    return str(recipe).lower()


def effective_size_gb(model_meta: Mapping[str, Any]) -> float | None:
    """Conservative footprint estimate in GB, or None when genuinely unknown.

    * A reported size is inflated by ``SIZE_SAFETY_FACTOR`` (real footprint
      exceeds catalog size — the freeze root cause).
    * A FLM-recipe model with no reported size gets a bounded nominal
      (``_FLM_NOMINAL_GB`` x factor) — safe NPU loads must not false-refuse.
    * Anything else with no reported size returns None. Callers MUST treat None
      as 'do not load', never as 0 (the freeze bypass).
    """
    size = _size_of(model_meta)
    if size is not None:
        return size * SIZE_SAFETY_FACTOR
    if _recipe_of(model_meta) == "flm":
        return _FLM_NOMINAL_GB * SIZE_SAFETY_FACTOR
    return None


def check_load_safe(
    model_meta: Mapping[str, Any],
    available_gb: float,
    *,
    ram_floor_gb: float = RAM_FLOOR_GB,
) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for loading ``model_meta`` given ``available_gb``.

    Pure function: no network, no /proc — pass ``available_ram_gb()`` in.

    Refuses when the effective (safety-inflated) footprint is unknown, or when
    it exceeds ``available_gb - ram_floor_gb``. Otherwise approves.
    """
    est = effective_size_gb(model_meta)
    if est is None:
        return False, (
            "size unknown/unverifiable — refusing (unknown != fits; "
            "the freeze bypass was treating unknown as 0 GB)"
        )
    budget = max(0.0, available_gb - ram_floor_gb)
    if est > budget:
        return False, (
            f"est footprint {est:.1f}GB (catalog x{SIZE_SAFETY_FACTOR}) > "
            f"{available_gb:.1f}GB avail - {ram_floor_gb:.0f}GB floor = {budget:.1f}GB"
        )
    return True, (
        f"ok: est {est:.1f}GB <= {budget:.1f}GB budget "
        f"({available_gb:.1f}GB avail - {ram_floor_gb:.0f}GB floor)"
    )


def safe_swap(
    target: str,
    *,
    prior_occupant: Callable[[], str | None],
    load_fn: Callable[[str], object],
    verify_fn: Callable[[str], bool],
) -> dict[str, object]:
    """Transactional model swap: load ``target``, restoring the prior occupant if
    the load fails or the model never verifies ready.

    Incident 2026-07-17 (Ternary-Bonsai): lemonade LRU-evicts the current
    occupant BEFORE the load attempt and does NOT restore it on failure, flushing
    the fleet. This makes the swap atomic. Dependency-injected so it is testable
    without a live server and reusable for any backend (NPU slot, iGPU tenant).

    Returns ``{ok, loaded, restored, restore_failed}``. Never raises — a recovery
    primitive must not itself crash the caller.
    """
    prior = prior_occupant()
    try:
        load_fn(target)
        if verify_fn(target):
            return {"ok": True, "loaded": target, "restored": None, "restore_failed": False}
        reason = "verify_false"
    except Exception as exc:
        reason = f"load_error: {exc}"
    # Load failed → restore the evicted occupant if there was one.
    if prior is None:
        return {
            "ok": False,
            "loaded": None,
            "restored": None,
            "restore_failed": False,
            "reason": reason,
        }
    try:
        load_fn(prior)
        return {
            "ok": False,
            "loaded": None,
            "restored": prior,
            "restore_failed": False,
            "reason": reason,
        }
    except Exception as exc:
        return {
            "ok": False,
            "loaded": None,
            "restored": None,
            "restore_failed": True,
            "reason": f"{reason}; restore: {exc}",
        }
