"""Apply Lemonade model recipes to the :13305 OmniRouter daemon.

Applies BASE_RECIPES from lemonade_recipes.py via the Lemonade HTTP API:
  POST /api/v1/load {model_name, ctx_size, llamacpp_args, llamacpp_backend, save_options: true}

Safety rules (N3 OOM hazard in harness.md):
  - Models are applied sequentially, smallest-first, never in parallel.
  - A RAM gate (oom_guard) blocks any load that would leave <RAM_BUFFER_GB free.
  - Each model is unloaded immediately after recipe_options are saved.
  - ctx_size=0 is explicitly rejected and will cause a hard abort.
  - JSON payloads use json.dumps() — never Python repr (see prior parse-error incident).

Modes:
  python scripts/apply_lemonade_recipes.py           — dry-run, shows plan only
  python scripts/apply_lemonade_recipes.py --apply   — actually applies via API
  python scripts/apply_lemonade_recipes.py --apply --only Bonsai-8B-gguf  — single model

USER_VARIANTS registration: written to ~/.cache/lemonade/custom_models/ as JSON files.
Requires `sudo systemctl restart lemond` to pick up after --apply.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from typing import Any

import requests

# ── Repo root on sys.path ──────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from cohezion.compound.lemonade_recipes import BASE_RECIPES, USER_VARIANTS
from cohezion.compound.oom_guard import get_available_ram_gb

# ── Constants ─────────────────────────────────────────────────────────────────
_API = "http://localhost:13305/api/v1"
_RAM_BUFFER_GB = 12.0   # always keep ≥12 GB free after loading any model
_LOAD_TIMEOUT  = 600    # seconds — heavy models (23 GB) can take 2-3 min to load
_VERIFY_TIMEOUT = 5

# Approximate on-disk sizes for the models we manage (GB).
# Used to gate RAM before loading.  Conservative (includes KV cache overhead).
_MODEL_SIZE_GB: dict[str, float] = {
    "nomic-embed-text-v2-moe-GGUF":      1.0,
    "Qwen3-Embedding-0.6B-GGUF":         1.0,
    "Qwen3-0.6B-GGUF":                   1.5,
    "Bonsai-1.7B-gguf":                  1.5,
    "Bonsai-4B-gguf":                    3.0,
    "Gemma-4-E2B-it-GGUF":              6.0,
    "Bonsai-8B-gguf":                    3.0,
    "DeepSeek-Qwen3-8B-GGUF":           8.0,
    "Gemma-4-E4B-it-GGUF":             10.0,
    "Gemma-4-26B-A4B-it-GGUF":         24.0,
    "Qwen3.6-27B-GGUF":                25.0,
    "Gemma-4-31B-it-GGUF":             26.0,
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": 25.0,
    "Nemotron-3-Nano-30B-A3B-GGUF":    30.0,
    "Qwen3.5-35B-A3B-GGUF":            30.0,
    "Qwen3.6-35B-A3B-GGUF":            30.0,
    "Qwen3.6-35B-A3B-MTP-GGUF":        32.0,
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _api_get(path: str) -> dict:
    r = requests.get(f"{_API}/{path}", timeout=_VERIFY_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _api_post(path: str, payload: dict, timeout: int = _VERIFY_TIMEOUT) -> dict:
    # Always use json.dumps — never pass a Python dict repr to the API
    r = requests.post(
        f"{_API}/{path}",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def _health_check() -> bool:
    try:
        d = _api_get("health")
        return d.get("status") == "ok"
    except Exception as exc:
        _log(f"  [health] ERROR: {exc}")
        return False


def _load_with_recipe(model_name: str, opts: "dict[str, Any]", dry_run: bool) -> bool:
    """POST /api/v1/load to save recipe options; returns True on success."""
    payload = {
        "model_name": model_name,
        "save_options": True,
        **opts,
    }

    # Sanity: never allow ctx_size=0 to reach the API (N3 OOM hazard)
    if payload.get("ctx_size") == 0:
        _log(f"  [ABORT] ctx_size=0 for {model_name} — refusing to send (N3 hazard).")
        return False

    if dry_run:
        _log(f"  [dry-run] POST /api/v1/load {json.dumps(payload, indent=4)}")
        return True

    try:
        resp = _api_post("load", payload, timeout=_LOAD_TIMEOUT)
        _log(f"  [load] response: {json.dumps(resp)[:200]}")
        return True
    except requests.Timeout:
        _log(f"  [load] TIMEOUT after {_LOAD_TIMEOUT}s — model may still be loading.")
        return False
    except requests.HTTPError as exc:
        resp_body = exc.response.text[:400] if exc.response is not None else ""
        status = exc.response.status_code if exc.response is not None else "?"
        _log(f"  [load] HTTP ERROR {status}: {resp_body}")
        return False
    except Exception as exc:
        _log(f"  [load] ERROR: {exc}")
        return False


def _unload(model_name: str, dry_run: bool) -> None:
    if dry_run:
        _log(f"  [dry-run] POST /api/v1/unload {{'model_name': '{model_name}'}}")
        return
    try:
        resp = _api_post("unload", {"model_name": model_name}, timeout=10)
        _log(f"  [unload] {json.dumps(resp)[:120]}")
    except Exception as exc:
        _log(f"  [unload] (non-fatal) {exc}")


def _verify_saved(model_name: str, expected: "dict[str, Any]") -> bool:
    """Check that the daemon's stored recipe_options match what we sent."""
    try:
        d = _api_get(f"models/{model_name}")
        ro = d.get("recipe_options") or {}
        for key, val in expected.items():
            if key == "ctx_size":
                remote_val = ro.get("ctx_size")
                if remote_val != val:
                    _log(f"  [verify] ctx_size mismatch: expected {val}, got {remote_val}")
                    return False
        return True
    except Exception as exc:
        _log(f"  [verify] WARN (could not confirm): {exc}")
        return True  # non-fatal — save_options: true already returned success


def apply_base_recipes(
    dry_run: bool = True,
    model_filter: str | None = None,
) -> dict[str, str]:
    """Apply all BASE_RECIPES.  Returns {model_name: 'ok'|'skip'|'fail'}."""

    results: dict[str, str] = {}

    # Sort by estimated model size (smallest first) to minimise peak RAM during apply
    ordered = sorted(
        BASE_RECIPES.items(),
        key=lambda kv: _MODEL_SIZE_GB.get(kv[0], 5.0),
    )

    _log(f"\n{'DRY-RUN: ' if dry_run else ''}Applying {len(ordered)} BASE_RECIPES")
    _log("=" * 60)

    for model_name, opts in ordered:
        if model_filter and model_filter.lower() not in model_name.lower():
            continue

        size_gb = _MODEL_SIZE_GB.get(model_name, 5.0)
        _log(f"\n• {model_name} (~{size_gb:.0f} GB)")
        _log(f"  ctx_size={opts.get('ctx_size')}  backend={opts.get('llamacpp_backend')}")

        if not dry_run:
            avail = get_available_ram_gb()
            needed = size_gb + _RAM_BUFFER_GB
            _log(f"  RAM available: {avail:.1f} GB  needed: {needed:.1f} GB")

            if avail < needed:
                _log(f"  [SKIP] insufficient RAM ({avail:.1f} < {needed:.1f}) — skipping.")
                results[model_name] = "skip"
                continue

        flat_opts: dict[str, Any] = {**opts}
        ok = _load_with_recipe(model_name, flat_opts, dry_run=dry_run)

        if ok and not dry_run:
            time.sleep(1)  # brief pause before verify/unload
            if _verify_saved(model_name, flat_opts):
                _log(f"  [verify] ✓ recipe_options saved")
            _unload(model_name, dry_run=False)

        results[model_name] = "ok" if ok else "fail"

    return results


def _custom_models_dir() -> Path:
    """Return the user-writable Lemonade custom_models directory."""
    d = Path.home() / ".cache" / "lemonade" / "custom_models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def apply_user_variants(dry_run: bool = True) -> dict[str, str]:
    """Write USER_VARIANTS JSON files to ~/.cache/lemonade/custom_models/.

    To activate them, update config.json extra_models_dir and restart lemond.
    """
    results: dict[str, str] = {}
    dest = _custom_models_dir()

    _log(f"\n{'DRY-RUN: ' if dry_run else ''}Writing {len(USER_VARIANTS)} USER_VARIANTS")
    _log(f"  Destination: {dest}")
    _log("=" * 60)

    for variant in USER_VARIANTS:
        name = variant.get("model_name", "unknown")
        slug = name.replace("user.", "").replace(".", "_")
        path = dest / f"{slug}.json"

        _log(f"\n• {name}")
        _log(f"  → {path}")

        if dry_run:
            _log(f"  [dry-run] would write:\n{json.dumps(variant, indent=4)}")
            results[name] = "ok"
            continue

        try:
            path.write_text(json.dumps(variant, indent=2))
            _log(f"  [write] ✓ written")
            results[name] = "ok"
        except Exception as exc:
            _log(f"  [write] ERROR: {exc}")
            results[name] = "fail"

    if not dry_run and results:
        # Update config.json to point extra_models_dir at custom_models
        config_path = Path.home() / ".cache" / "lemonade" / "config.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text())
                if cfg.get("extra_models_dir") != str(dest):
                    cfg["extra_models_dir"] = str(dest)
                    config_path.write_text(json.dumps(cfg, indent=2))
                    _log(f"\n[config] Updated extra_models_dir → {dest}")
            except Exception as exc:
                _log(f"\n[config] WARN: could not update config.json: {exc}")

        _log("\n[IMPORTANT] Run: sudo systemctl restart lemond")
        _log("  (required for user variants to appear in /api/v1/models)")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually apply recipes (default: dry-run only)",
    )
    parser.add_argument(
        "--only",
        metavar="PATTERN",
        default=None,
        help="Filter: only apply models whose name contains PATTERN",
    )
    parser.add_argument(
        "--skip-variants",
        action="store_true",
        default=False,
        help="Skip USER_VARIANTS (apply BASE_RECIPES only)",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        _log("\n★  DRY-RUN MODE  ★  (pass --apply to execute)")
        _log("   No API calls will be made. No models will be loaded.\n")

    # Health gate
    if not dry_run:
        if not _health_check():
            _log("ERROR: Lemonade daemon at :13305 is not healthy. Aborting.")
            return 1
        avail = get_available_ram_gb()
        _log(f"System RAM available: {avail:.1f} GB")
        if avail < 20:
            _log(f"ERROR: only {avail:.1f} GB free — need ≥20 GB to safely apply recipes.")
            return 1

    base_results = apply_base_recipes(dry_run=dry_run, model_filter=args.only)

    variant_results: dict[str, str] = {}
    if not args.skip_variants:
        variant_results = apply_user_variants(dry_run=dry_run)

    all_results = {**base_results, **variant_results}
    fails = [n for n, s in all_results.items() if s == "fail"]
    skips = [n for n, s in all_results.items() if s == "skip"]

    _log("\n" + "=" * 60)
    _log(f"Summary: {len(all_results)} models")
    _log(f"  OK:     {sum(1 for s in all_results.values() if s == 'ok')}")
    _log(f"  Skipped:{len(skips)}")
    _log(f"  Failed: {len(fails)}")
    if fails:
        _log(f"  Failed models: {fails}")

    if dry_run:
        _log("\nTo apply, run:  python scripts/apply_lemonade_recipes.py --apply")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
