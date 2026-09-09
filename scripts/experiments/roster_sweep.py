# ruff: noqa: I001 - import block is deliberately split by the sys.path setup below.
"""Measure the whole lane roster ONE MODEL AT A TIME, ranked by true generation cost.

Why one at a time: with several large models resident the fleet contends and wall-clock stops
measuring the model. Observed 2026-08-16 -- gpt-oss-20b read 3.9s alone and 8.0s with two peers
resident, a 2x swing from residency rather than from the lane. Token counts are unaffected by
contention; latency is not, so latency is only trustworthy under exclusive residency.

Why GEN_TOK: `len(text)` measures what survived the adapter, and for a thinking model outside
gaia_adapter._THINKING_MODEL_MARKERS the reasoning is stripped first. Ranking by characters put
gpt-oss-20b and Nemotron at the top purely because their reasoning was invisible. See
docs/benchmarks/lane_selection.md.

Safety, because this box hard-hung twice on 2026-08-15:
  * unloads everything before each load, so peak residency is one model
  * refuses to load when free memory is under --min-free-gb
  * bounded ctx_size (never 0 -- N3, a ctx_size=0 load mapped ~120GB GTT and required a cold boot)
  * never sets `pinned` (mlock blocks TTM eviction)
  * durable per-rep output on ZFS, so a crash costs one rep rather than the sweep

Usage:
  .venv/bin/python scripts/experiments/roster_sweep.py --reps 3
  .venv/bin/python scripts/experiments/roster_sweep.py --models a,b --reps 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "experiments"))

from durable_swarm_output import DurableRun  # noqa: E402
from lane_termination_benchmark import one_rep  # noqa: E402

ROUTER = "http://localhost:13305/api/v1"

# Ordered small -> large: a systemic failure surfaces on a cheap load rather than after a 22GB
# one, and the sweep degrades gracefully if memory tightens partway through.
# Ids verified against the live /api/v1/models catalog on 2026-08-16. The short names carried in
# prose docs (`SmolLM3-3B`, `Qwen3-Coder-30B`, `lfm2.5-230m`) all 404 on /load -- a load failure
# is recorded as a RESULT here, but it wastes a slot, so keep these exact.
DEFAULT_ROSTER = [
    "lfm2.5-230m-code-exp-GGUF-F16",
    "llama3.2-3b-FLM",
    "qwen3-4b-FLM",
    "SmolLM3-3B-IQ4_XS-GGUF-IQ4_XS",
    "Gemma-4-E2B-it-GGUF",
    "Gemma-4-E4B-it-GGUF",
    "Qwen3-8B-GGUF",
    "deepseek-r1-0528-8b-FLM",
    "gpt-oss-20b",
    "Gemma-4-26B-A4B-it-GGUF",
    "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "Nemotron-3-Nano-30B-A3B-GGUF",
    "Gemma-4-31B-it-GGUF",
    "Qwen3.6-35B-A3B-MTP-GGUF",
]


def _post(path: str, payload: dict, timeout: int = 900) -> dict:
    body = json.dumps(payload).encode()
    # S310: ROUTER is a module-level http:// localhost constant, never caller-supplied.
    req = urllib.request.Request(f"{ROUTER}/{path}", data=body,  # noqa: S310
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _resident() -> list[str]:
    try:
        with urllib.request.urlopen(f"{ROUTER}/health", timeout=10) as r:  # noqa: S310
            d = json.load(r)
        return [m["model_name"] for m in d.get("all_models_loaded", [])]
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError):
        return []


def _free_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 1048576
    return 0.0


def _psi() -> float:
    try:
        first = Path("/proc/pressure/memory").read_text().splitlines()[0]
        return float(first.split("avg10=")[1].split()[0])
    except (OSError, IndexError, ValueError):
        return 0.0


def _drain(keep: str | None = None) -> None:
    """Unload every resident model except `keep`. Embedding models are left alone -- they are
    small, shared with other sessions, and evicting them would be a side effect on peers."""
    for name in _resident():
        if name == keep or "embed" in name.lower():
            continue
        _post("unload", {"model_name": name}, timeout=120)


async def sweep(models: list[str], reps: int, ctx: int, min_free: float) -> list[dict]:
    run = DurableRun("roster-sweep", meta={"models": models, "reps": reps, "ctx_size": ctx})
    rows: list[dict] = []
    print(f"{'model':<34} {'term':>5} {'GEN_TOK':>8} {'rawch':>7} {'drop':>7} {'p50s':>7}  note")
    print("-" * 96)

    for model in models:
        _drain()
        free, psi = _free_gb(), _psi()
        if free < min_free or psi > 10:
            note = f"SKIPPED free={free:.0f}G psi={psi:.1f}"
            print(f"{model:<34} {'-':>5} {'-':>8} {'-':>7} {'-':>7} {'-':>7}  {note}")
            rows.append({"model": model, "skipped": note})
            run.record_lane(rows[-1])
            continue

        t0 = time.time()
        res = _post("load", {"model_name": model, "ctx_size": ctx})
        if res.get("status") != "success":
            note = f"LOAD FAILED {str(res.get('error') or res)[:44]}"
            print(f"{model:<34} {'-':>5} {'-':>8} {'-':>7} {'-':>7} {'-':>7}  {note}")
            rows.append({"model": model, "load_error": note})
            run.record_lane(rows[-1])
            continue
        load_s = time.time() - t0

        # Warm once, unscored. The first call after a load pays graph/KV warmup -- measured 18.1s
        # against 1.2s for the identical call immediately after -- which would otherwise land
        # entirely in rep 1 and skew a 3-rep median.
        await one_rep(model, 256)

        reps_out = [await one_rep(model, 4000) for _ in range(reps)]
        for r in reps_out:
            run.record_lane(r)

        term = sum(1 for r in reps_out if r["terminated"]) / len(reps_out)
        gen = statistics.median(r.get("gen_tokens", 0) for r in reps_out)
        raw = statistics.median(r["raw_chars"] for r in reps_out)
        drop = statistics.median(r.get("dropped_reasoning_chars", 0) for r in reps_out)
        p50 = statistics.median(r["secs"] for r in reps_out)
        whys = {r["why"] for r in reps_out if r["why"]}
        row = {"model": model, "term": term, "gen_tokens": gen, "raw_chars": raw,
               "dropped": drop, "p50": p50, "load_s": round(load_s, 1),
               "why": ",".join(sorted(whys))}
        rows.append(row)
        print(f"{model:<34} {term:>5.2f} {gen:>8.0f} {raw:>7.0f} {drop:>7.0f} {p50:>7.1f}  "
              f"{row['why'] or 'ok'}", flush=True)

    _drain()
    run.finalize({"reps": reps, "ctx_size": ctx})
    return rows


def report(rows: list[dict]) -> None:
    ok = [r for r in rows if r.get("gen_tokens") is not None and "term" in r]
    if not ok:
        print("\nNo lane produced a measurement.")
        return
    print("\n=== ranked by TRUE generation cost (GEN_TOK, ascending) ===")
    usable = [r for r in ok if r["term"] >= 0.8]
    for r in sorted(usable, key=lambda r: r["gen_tokens"]):
        flag = "  <- chars understate this lane" if r["dropped"] > 0 else ""
        print(f"  {r['model']:<34} {r['gen_tokens']:>6.0f} tok  {r['p50']:>6.1f}s{flag}")
    unusable = [r for r in ok if r["term"] < 0.8]
    if unusable:
        print("\nEXCLUDED -- termination below 0.8, unusable for swarm work regardless of cost:")
        for r in unusable:
            print(f"  {r['model']:<34} term={r['term']:.2f}  {r['why']}")
    stripped = [r for r in ok if r["dropped"] > 0]
    if stripped:
        print("\nMeasured post-strip (outside gaia_adapter._THINKING_MODEL_MARKERS) -- their")
        print("rawch is NOT comparable to the others; the GEN_TOK ranking above is:")
        for r in stripped:
            print(f"  {r['model']}: ~{r['dropped']:.0f} chars/call discarded")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--ctx-size", type=int, default=16384)
    ap.add_argument("--min-free-gb", type=float, default=40.0)
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()] or DEFAULT_ROSTER
    rows = await sweep(models, args.reps, args.ctx_size, args.min_free_gb)
    report(rows)


if __name__ == "__main__":
    asyncio.run(main())
