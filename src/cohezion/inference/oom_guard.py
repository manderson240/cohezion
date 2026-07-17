"""OOM guardrail for Lemonade router on AMD Strix Halo (128 GiB unified memory).

Single entry point: `scan_and_harden()`.  Call it at session start and before
any heavy-model inference sprint.  No sudo required — uses the Lemonade HTTP API
exclusively.

N3 root cause (harness.md §N3):
  - Any model with recipe_options.ctx_size=0 on the router auto-loads with
    an unbounded KV cache when a request names it.  On Strix Halo this hangs
    the kernel and forces a hard reboot.
  - Direct file edit of recipe_options.json is volatile (lemond restart can
    reload from backup/download metadata).  The only durable fix is
    POST /api/v1/load with {save_options: true} — this patches the API
    persistence path rather than the on-disk JSON.

Protection layers implemented here:
  1. scan_and_harden() — discovers every heavy model with ctx_size=0 and pins
     it via the API before any inference request can auto-load it.
  2. check_ram()       — reads psutil.virtual_memory().available; caller should
     abort the load when free RAM < min_free_gb.
  3. verify_all_bounded() — pure read-only check suitable for CI/harness tests;
     never modifies state.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from cohezion.config.defaults import LEMONADE_BASE_URL


logger = logging.getLogger(__name__)

# KV-cache ceiling for all heavy models (≥5 GB).  Chosen to fit within the
# 128 GiB Strix Halo unified pool with comfortable headroom for OS + apps.
SAFE_CTX_SIZE: int = 16384

# Models below this size threshold (GB) are left unbounded — their full-context
# KV cache cannot exhaust unified memory even on a partially-used system.
HEAVY_MODEL_GB_THRESHOLD: float = 5.0


def check_ram(min_free_gb: float = 20.0) -> tuple[bool, float]:
    """Return (safe, free_gb).  safe=True when free RAM >= min_free_gb.

    Falls back to (True, inf) if psutil is not installed — the caller should
    NOT crash; it just cannot enforce the guard without psutil.
    """
    try:
        import psutil

        free_gb: float = psutil.virtual_memory().available / 1_000_000_000
        return free_gb >= min_free_gb, free_gb
    except ImportError:
        logger.debug("psutil not installed — RAM guard skipped")
        return True, float("inf")


def _get_catalog(base_url: str, timeout: float = 5.0) -> list[dict[str, Any]]:
    """Fetch /api/v1/models — returns list of model dicts (name, size, recipe_options).

    Falls back to /v1/models (OpenAI-compat) when /api/v1/models is unavailable;
    that endpoint returns only id/created fields so recipe_options will be absent.
    """
    for path in ("/api/v1/models", "/v1/models"):
        try:
            req = urllib.request.Request(  # noqa: S310
                base_url.rstrip("/") + path, method="GET"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = json.loads(resp.read())
                # Both endpoints return either a list or {"data": [...]} / {"models": [...]}
                if isinstance(raw, list):
                    return raw
                return raw.get("models", raw.get("data", []))
        except Exception as exc:
            logger.debug("Catalog fetch from %s%s failed: %s", base_url, path, exc)
    return []


def _get_recipe_options(base_url: str, model_name: str, timeout: float = 5.0) -> dict[str, Any]:
    """Fetch /api/v1/models/<name> and return recipe_options dict (may be empty)."""
    try:
        url = f"{base_url.rstrip('/')}/api/v1/models/{model_name}"
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
            return data.get("recipe_options") or {}
    except Exception as exc:
        logger.debug("recipe_options fetch for %s failed: %s", model_name, exc)
        return {}


def _harden_model(
    base_url: str,
    model_name: str,
    ctx_size: int = SAFE_CTX_SIZE,
    timeout: float = 15.0,
) -> bool:
    """POST /api/v1/load with save_options=true to permanently cap ctx_size.

    This is the only durable fix (direct file edit is overwritten on restart).
    Does NOT load the model into GPU memory — it only writes the recipe_options.
    Returns True on HTTP 200 or 201.
    """
    payload = json.dumps(
        {"model_name": model_name, "ctx_size": ctx_size, "save_options": True}
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{base_url.rstrip('/')}/api/v1/load",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            ok = resp.status in (200, 201)
            if ok:
                logger.info(
                    "OOMGuard: pinned %s ctx_size=%d (save_options=true)", model_name, ctx_size
                )
            else:
                logger.warning("OOMGuard: unexpected status %d for %s", resp.status, model_name)
            return ok
    except urllib.error.HTTPError as exc:
        logger.warning("OOMGuard: HTTP %d hardening %s: %s", exc.code, model_name, exc.read()[:100])
        return False
    except Exception as exc:
        logger.warning("OOMGuard: failed to harden %s: %s", model_name, exc)
        return False


def _is_heavy(model: dict[str, Any]) -> bool:
    """True when the model's size field indicates ≥ HEAVY_MODEL_GB_THRESHOLD GB.

    Size field may be absent, None, or a float (GB).  When absent we assume
    heavy=True for unknown models to err on the side of caution.
    """
    size = model.get("size")
    if size is None:
        return True  # unknown size → treat as heavy
    try:
        return float(size) >= HEAVY_MODEL_GB_THRESHOLD
    except (TypeError, ValueError):
        return True


def _ctx_is_unsafe(recipe_options: dict[str, Any]) -> bool:
    """True when ctx_size is explicitly 0 (unbounded KV cache crash vector)."""
    ctx = recipe_options.get("ctx_size")
    return ctx is not None and ctx == 0


def scan_and_harden(
    base_url: str = LEMONADE_BASE_URL,
    safe_ctx: int = SAFE_CTX_SIZE,
) -> dict[str, Any]:
    """Scan all router models; harden any heavy model with ctx_size=0.

    Returns a report dict:
    {
        "hardened":  [model_names successfully pinned this call],
        "already_safe": [model_names that were already bounded],
        "skipped":   [small models left untouched],
        "failed":    [model_names where hardening failed],
        "router_offline": bool,
        "free_ram_gb": float,
    }

    This is designed to be called:
    1. From the lemonade-warmup.sh hook (python3 -c "from cohezion.inference.oom_guard import scan_and_harden; scan_and_harden()")
    2. From omni_recipes.LemonadeLoopRecipes.register_all() after known-recipe registration
    3. From LoopCoordinator._pre_sprint_health_check()
    """
    _, free_gb = check_ram(min_free_gb=0.0)  # just measure, don't gate here

    catalog = _get_catalog(base_url)
    if not catalog:
        logger.warning("OOMGuard: router offline or empty catalog at %s", base_url)
        return {
            "hardened": [],
            "already_safe": [],
            "skipped": [],
            "failed": [],
            "router_offline": True,
            "free_ram_gb": free_gb,
        }

    hardened: list[str] = []
    already_safe: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for model in catalog:
        name: str = model.get("model_name") or model.get("id") or ""
        if not name:
            continue

        if not _is_heavy(model):
            skipped.append(name)
            continue

        # recipe_options may already be present in the catalog response (full endpoint)
        # or may require a separate per-model fetch (OpenAI-compat fallback).
        recipe_options = model.get("recipe_options") or _get_recipe_options(base_url, name)

        if _ctx_is_unsafe(recipe_options):
            ok = _harden_model(base_url, name, ctx_size=safe_ctx)
            (hardened if ok else failed).append(name)
        else:
            already_safe.append(name)

    report = {
        "hardened": hardened,
        "already_safe": already_safe,
        "skipped": skipped,
        "failed": failed,
        "router_offline": False,
        "free_ram_gb": free_gb,
    }

    if hardened:
        logger.warning(
            "OOMGuard: hardened %d model(s) that had ctx_size=0 — %s",
            len(hardened),
            hardened,
        )
    if failed:
        logger.error(
            "OOMGuard: FAILED to harden %d model(s) — manual intervention needed: %s",
            len(failed),
            failed,
        )

    total = len(hardened) + len(already_safe) + len(skipped) + len(failed)
    logger.info(
        "OOMGuard: scanned %d models — %d hardened, %d already safe, %d skipped (small), %d failed | RAM %.1f GB free",
        total,
        len(hardened),
        len(already_safe),
        len(skipped),
        len(failed),
        free_gb,
    )
    return report


def pre_load_gate(
    model_name: str,
    ctx_size: int,
    min_free_gb: float = 20.0,
    base_url: str = LEMONADE_BASE_URL,
) -> tuple[bool, str]:
    """Combined pre-load safety gate for dynamic model hot-swapping.

    Call this BEFORE sending POST /api/v1/load to the OmniRouter.
    Returns (allowed, reason). When allowed=False, abort the load request.

    Checks (in order):
    1. ctx_size=0 on a heavy model → always blocked (N3 crash vector)
    2. Free RAM < min_free_gb → blocked
    3. Both safe → allowed, with reason including RAM headroom

    Args:
        model_name: Model name for size heuristic (heuristic from catalog size
                    field; falls back to name-based estimate).
        ctx_size: Requested context window (0 = unbounded = dangerous).
        min_free_gb: Minimum free RAM required in GiB (default 20 GiB).
        base_url: OmniRouter URL for catalog lookup.
    """
    # 1. ctx_size=0 gate — non-negotiable for heavy models
    catalog = _get_catalog(base_url)
    entry = next(
        (m for m in catalog if (m.get("model_name") or m.get("id") or "") == model_name),
        None,
    )
    is_heavy = _is_heavy(entry) if entry is not None else _name_looks_heavy(model_name)

    if is_heavy and ctx_size == 0:
        return False, (
            f"ctx_size=0 on heavy model {model_name!r} is the N3 OOM crash vector — "
            f"use ctx_size≤{SAFE_CTX_SIZE} instead"
        )

    # 2. RAM gate
    ok, free_gb = check_ram(min_free_gb)
    if not ok:
        return False, (
            f"insufficient RAM: {free_gb:.1f} GiB free < {min_free_gb:.0f} GiB floor "
            f"(required before loading {model_name!r})"
        )

    # 3. Weight-fit gate (freeze-prevention, 2026-07-16). The RAM gate above only
    # guarantees a fixed reserve — it does NOT verify the model's WEIGHTS fit.
    # Mistral-Medium-128B (catalog size 42.3 GB, ~69 GB real weights) passed the
    # floor with 42 GB free and hard-froze the box. When the catalog knows this
    # model, refuse if its safety-inflated footprint over-commits available RAM
    # minus the same reserve. Pure decision in load_safety; catalog entry as input.
    if entry is not None:
        from cohezion.inference.load_safety import check_load_safe

        fit_ok, fit_reason = check_load_safe(entry, free_gb, ram_floor_gb=min_free_gb)
        if not fit_ok:
            return False, f"weight over-commit for {model_name!r}: {fit_reason}"

    return True, f"ok: {free_gb:.1f} GiB free, ctx_size={ctx_size}, heavy={is_heavy}"


def _name_looks_heavy(model_name: str) -> bool:
    """Heuristic: does model name suggest ≥ HEAVY_MODEL_GB_THRESHOLD GB?"""
    import re

    m = re.search(r"(\d+(?:\.\d+)?)B", model_name, re.IGNORECASE)
    if m:
        params_b = float(m.group(1))
        return params_b * 0.5 >= HEAVY_MODEL_GB_THRESHOLD  # Q4 ~0.5 GB/B
    return False


def verify_all_bounded(base_url: str = LEMONADE_BASE_URL) -> tuple[bool, list[str]]:
    """Read-only check: return (all_safe, violations).

    violations is a list of model names with ctx_size=0 on heavy models.
    Use in harness tests or CI to assert N3 invariant without modifying state.
    """
    catalog = _get_catalog(base_url)
    if not catalog:
        return True, []  # router offline — no violation to report

    violations: list[str] = []
    for model in catalog:
        name: str = model.get("model_name") or model.get("id") or ""
        if not name or not _is_heavy(model):
            continue
        recipe_options = model.get("recipe_options") or _get_recipe_options(base_url, name)
        if _ctx_is_unsafe(recipe_options):
            violations.append(name)

    return len(violations) == 0, violations
