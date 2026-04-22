"""Sync Lemonade's per-model recipe_options to match the fleet registry's kv_quant.

Closes the loop between the declarative kv8 pivot (commit 7626af3c0, which set
runtime_flag['llama.cpp'] = 'q8_0' on the iGPU Gemma models) and Lemonade's
actual runtime config — without it, the registry declares q8_0 but llama-server
still serves with bf16 KV, exactly the silent-no-op failure mode the Phase 0
gate was designed to prevent.

For each iGPU model in the registry with a non-'none' kv_quant scheme and a
'llama.cpp' runtime flag:
  1. Query Lemonade's /v1/models for the current recipe_options.llamacpp_args.
  2. If it already contains --cache-type-k/--cache-type-v matching the flag, skip.
  3. Otherwise, either print the command (--dry-run, default) or invoke
     `lemonade load --llamacpp-args "..." --save-options <model_id>` to persist.

Safe to run repeatedly. Idempotent: skips models already in sync. Dry-run default
so the operator can review the plan before applying.

Usage:
    uv run python scripts/sync_lemonade_kv_quant.py                    # dry-run
    uv run python scripts/sync_lemonade_kv_quant.py --apply            # execute
    uv run python scripts/sync_lemonade_kv_quant.py --model <id>       # one model
    uv run python scripts/sync_lemonade_kv_quant.py --apply --verbose  # show diff
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

from cohezion.inference.registry import FleetRegistry, Lane, ModelEntry


LEMONADE_BASE_DEFAULT = "http://localhost:13307"
IGPU_LANES = {Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED}


def expected_llamacpp_args(flag: str) -> str:
    """Compose llama-server --cache-type-k/-v args from a runtime_flag value."""
    return f"--cache-type-k {flag} --cache-type-v {flag}"


def fetch_recipe_options(model_id: str, lemonade_base: str) -> dict | None:
    """Return recipe_options for a model from /v1/models, or None if model absent."""
    try:
        with urllib.request.urlopen(  # noqa: S310 — localhost operator tool, trusted input
            f"{lemonade_base}/v1/models", timeout=5
        ) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"  ERROR: cannot reach {lemonade_base}: {exc}", file=sys.stderr)
        return None
    for entry in payload.get("data", []):
        if entry.get("id") == model_id:
            return entry.get("recipe_options") or {}
    return None


def already_in_sync(current_options: dict | None, expected_args: str) -> bool:
    """True iff current recipe_options.llamacpp_args already contains the expected flags.

    Lemonade stores the flags as a single space-separated string; we check substring
    presence of each `--cache-type-k X` / `--cache-type-v X` rather than exact-match
    so an operator can add other flags without this script clobbering them.
    """
    if not current_options:
        return False
    current = current_options.get("llamacpp_args") or ""
    return all(part.strip() in current for part in expected_args.split("--") if part.strip())


def apply_sync(model_id: str, expected_args: str) -> int:
    """Invoke `lemonade load --save-options ...` for a model. Returns exit code."""
    cmd = [
        "lemonade",
        "load",
        "--llamacpp-args",
        expected_args,
        "--save-options",
        model_id,
    ]
    print(f"  $ {' '.join(cmd)}")
    # `cmd` is a static list built from registry data + the `lemonade` CLI.
    # No shell expansion, no user-controlled strings — safe by construction.
    result = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, timeout=120, check=False
    )
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode}): {result.stderr.strip()[:200]}")
    return result.returncode


def plan_and_apply(
    registry: FleetRegistry,
    lemonade_base: str,
    *,
    dry_run: bool,
    target_model_id: str | None = None,
    verbose: bool = False,
) -> tuple[int, int, int]:
    """Iterate registry, plan syncs, optionally apply. Returns (in_sync, planned, applied)."""
    in_sync = planned = applied = 0
    for model in registry.models.values():
        if target_model_id and model.model_id != target_model_id:
            continue
        if not _is_llamacpp_kv_quant_candidate(model):
            continue
        flag = model.kv_quant.runtime_flag.get("llama.cpp")
        if flag is None:  # _is_candidate already filters this, belt-and-suspenders
            continue
        expected = expected_llamacpp_args(flag)
        options = fetch_recipe_options(model.model_id, lemonade_base)
        if already_in_sync(options, expected):
            print(f"[in-sync]  {model.model_id} — already has {expected!r}")
            in_sync += 1
            continue
        if options is None:
            current = "<model not registered with Lemonade>"
        elif not options:
            current = "<no recipe_options persisted yet>"
        else:
            current = options.get("llamacpp_args", "<no llamacpp_args key>")
        print(f"[needs-sync] {model.model_id}")
        if verbose:
            print(f"             current:  {current}")
            print(f"             expected: {expected}")
        planned += 1
        if not dry_run:
            rc = apply_sync(model.model_id, expected)
            if rc == 0:
                applied += 1
                post = fetch_recipe_options(model.model_id, lemonade_base)
                verified = already_in_sync(post, expected)
                print(f"  verified: {verified}")
    return in_sync, planned, applied


def _is_llamacpp_kv_quant_candidate(model: ModelEntry) -> bool:
    """True iff this model is an iGPU llamacpp model with a non-default kv_quant."""
    if model.lane not in IGPU_LANES:
        return False
    if model.kv_quant.scheme == "none":
        return False
    return model.kv_quant.runtime_flag.get("llama.cpp") is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually invoke lemonade load. Default is dry-run.",
    )
    parser.add_argument("--model", help="Sync only this model_id, not the full registry.")
    parser.add_argument(
        "--lemonade-base",
        default=LEMONADE_BASE_DEFAULT,
        help=f"Lemonade server base URL (default: {LEMONADE_BASE_DEFAULT})",
    )
    parser.add_argument("--verbose", action="store_true", help="Show current vs expected args.")
    args = parser.parse_args(argv)

    registry = FleetRegistry()
    print(
        f"Scanning registry for iGPU llamacpp models with non-default kv_quant...  "
        f"(mode: {'apply' if args.apply else 'DRY-RUN'})"
    )
    in_sync, planned, applied = plan_and_apply(
        registry,
        args.lemonade_base,
        dry_run=not args.apply,
        target_model_id=args.model,
        verbose=args.verbose,
    )
    print()
    print(f"Summary: in-sync={in_sync}  needs-sync={planned}  applied={applied}")
    if planned and not args.apply:
        print("Re-run with --apply to execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
