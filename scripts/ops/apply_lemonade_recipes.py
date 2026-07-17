# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Apply scripts/ops/lemonade-recipes.md to the :13305 lemonade router.

Dry-run by default: prints the diff plan and exits. Pass --apply to execute.

Safety rails (N3 / K1):
- RAM gate: skips any model whose load would leave < 16 GiB available.
- Skips currently-loaded models unless --force-reload (their recipe applies
  at the next natural reload instead).
- Persists via POST /v1/load {..., save_options: true} (the /api/v1 prefix
  404s on lemonade 10.6.0), then re-reads the catalog entry to VERIFY the
  options actually persisted before reporting success.
- Unloads the model after stamping unless --keep-loaded.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

MANIFEST = Path(__file__).with_name("lemonade-recipes.md")
RAM_FLOOR_GIB = 16.0
KV_ALLOWANCE_GIB = 8.0


def http_json(url: str, payload: dict | None = None, timeout: float = 300.0):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def load_manifest() -> tuple[str, list[dict]]:
    text = MANIFEST.read_text()
    if not text.startswith("---"):
        sys.exit(f"manifest {MANIFEST} has no YAML frontmatter")
    front = text.split("---", 2)[1]
    meta = yaml.safe_load(front)
    return meta["router"], meta["recipes"]


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    return 0.0


def desired_options(entry: dict) -> dict:
    opts: dict = {"ctx_size": entry["ctx_size"]}
    if entry.get("llamacpp_backend"):
        opts["llamacpp_backend"] = entry["llamacpp_backend"]
    if entry.get("llamacpp_args"):
        opts["llamacpp_args"] = entry["llamacpp_args"]
    return opts


def diff(current: dict, desired: dict) -> dict:
    return {k: v for k, v in desired.items() if current.get(k) != v}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="execute (default: dry-run)")
    ap.add_argument("--force-reload", action="store_true", help="also stamp currently-loaded models")
    ap.add_argument("--keep-loaded", action="store_true", help="do not unload after stamping")
    ap.add_argument("--only", help="restrict to a single model id")
    args = ap.parse_args()

    router, recipes = load_manifest()
    health = http_json(f"{router}/api/v1/health")
    loaded = {m["model_name"] for m in health.get("all_models_loaded", [])}

    applied, skipped, failed = [], [], []
    for entry in recipes:
        mid = entry["model"]
        if args.only and mid != args.only:
            continue
        try:
            cur = http_json(f"{router}/api/v1/models/{mid}")
        except urllib.error.HTTPError as e:
            skipped.append((mid, f"not in catalog ({e.code})"))
            continue
        want = desired_options(entry)
        delta = diff(cur.get("recipe_options") or {}, want)
        if not delta:
            skipped.append((mid, "already matches"))
            continue
        if mid in loaded and not args.force_reload:
            skipped.append((mid, f"currently loaded — will pick up on next reload; delta={delta}"))
            continue
        # Single source of truth for the freeze-prevention gate (ultrareview
        # bug_014): the ad-hoc 1.2x formula here diverged from load_safety's
        # calibrated 1.7x (Mistral-Medium 2026-07-16 freeze). KV allowance is
        # kept as an explicit extra on top of the SoT budget.
        from cohezion.inference.load_safety import check_load_safe

        avail = mem_available_gib()
        ok, why = check_load_safe(cur, avail - KV_ALLOWANCE_GIB, ram_floor_gb=RAM_FLOOR_GIB)
        if not ok:
            skipped.append((mid, f"RAM gate (load_safety): {why}; delta={delta}"))
            continue
        if not args.apply:
            print(f"PLAN  {mid}: {delta}")
            continue
        try:
            http_json(f"{router}/v1/load", {"model_name": mid, **want, "save_options": True})
            after = http_json(f"{router}/api/v1/models/{mid}").get("recipe_options") or {}
            residual = diff(after, want)
            if residual:
                failed.append((mid, f"load OK but options did not persist: {residual}"))
            else:
                applied.append(mid)
            if not args.keep_loaded:
                try:
                    http_json(f"{router}/v1/unload", {"model_name": mid}, timeout=60)
                except urllib.error.HTTPError:
                    http_json(f"{router}/api/v1/unload", {"model_name": mid}, timeout=60)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            failed.append((mid, str(e)))

    for mid, why in skipped:
        print(f"SKIP  {mid}: {why}")
    for mid in applied:
        print(f"OK    {mid}: persisted + verified")
    for mid, why in failed:
        print(f"FAIL  {mid}: {why}")
    if not args.apply:
        print("\ndry-run only — re-run with --apply to execute")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
