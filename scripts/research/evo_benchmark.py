"""Benchmark script for the optimal EVO experiment schedule.

Measures delta, keep_rate, and throughput (experiments/minute) using
timeit.default_timer. Results are logged to autoresearch_bench.jsonl.

Includes an autoharness health check to verify overnight_evo_loop imports.

Usage:
  # Quick smoke test (1 iteration, no LLM — ~seconds):
  uv run python scripts/research/evo_benchmark.py --quick

  # Full benchmark (10 iterations, no LLM — minutes):
  uv run python scripts/research/evo_benchmark.py --iterations 10

  # With live LLM (long-running):
  uv run python scripts/research/evo_benchmark.py --iterations 3 --llm
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
import timeit
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

BENCH_LOG = _REPO / "autoresearch_bench.jsonl"


# ── autoharness health check ──────────────────────────────────────────────────


def autoharness_health_check() -> dict:
    """Verify overnight_evo_loop imports are healthy (no ImportError)."""
    result: dict = {"status": "unknown"}
    try:
        spec = importlib.util.spec_from_file_location(
            "overnight_evo_loop", _REPO / "scripts" / "overnight_evo_loop.py"
        )
        assert spec and spec.loader
        evo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evo)  # type: ignore[attr-defined]

        # Verify the key functions exist
        required = [
            "experiment_e63_mycelium_closed_loop",
            "experiment_e50_db_informed_proposals",
            "experiment_e51_evo_quality_sensitivity",
        ]
        missing = [fn for fn in required if not hasattr(evo, fn)]
        if missing:
            result = {"status": "error", "missing_functions": missing}
        else:
            result = {"status": "ok", "verified_functions": required}
    except (ImportError, AttributeError, AssertionError) as exc:
        result = {"status": "error", "error": str(exc)}
    return result


# ── single schedule run (no-LLM heuristic mode for speed) ────────────────────


async def run_schedule_once(evo: object, use_llm: bool) -> dict:
    """Run the 4-experiment optimal schedule once, return per-experiment results."""

    # Serial composition helper (mirrors autorun_2h.py)
    async def run_e63_then_e50_serial() -> dict:
        r1 = await evo.experiment_e63_mycelium_closed_loop(  # type: ignore[attr-defined]
            n_phase=3, use_llm=use_llm, learning_rate=3.0
        )
        r2 = await evo.experiment_e50_db_informed_proposals(use_llm=use_llm)  # type: ignore[attr-defined]
        d1 = float(r1.get("coherence_delta", r1.get("delta", 0.0)))
        d2 = float(r2.get("gain", r2.get("coherence_delta", r2.get("delta", 0.0))))
        return {"coherence_delta": d1 + d2, "r1_delta": d1, "r2_delta": d2}

    schedule = [
        (
            "E63_n3_lr3",
            lambda: evo.experiment_e63_mycelium_closed_loop(  # type: ignore[attr-defined]
                n_phase=3, use_llm=use_llm, learning_rate=3.0
            ),
        ),
        ("E50_db", lambda: evo.experiment_e50_db_informed_proposals(use_llm=use_llm)),  # type: ignore[attr-defined]
        (
            "E51_quality",
            lambda: evo.experiment_e51_evo_quality_sensitivity(n_ticks=100, use_llm=use_llm),  # type: ignore[attr-defined]
        ),
        ("E63_then_E50", run_e63_then_e50_serial),
    ]

    results: dict[str, dict] = {}
    for label, fn in schedule:
        t0 = timeit.default_timer()
        try:
            r = await fn() or {}
            duration_s = timeit.default_timer() - t0
            delta = float(r.get("delta", r.get("gain", r.get("coherence_delta", 0.0))))
            keep = delta > 0 or r.get("quality_sensitive") is True or r.get("sensitive") is True
            results[label] = {
                "delta": delta,
                "keep": keep,
                "duration_s": round(duration_s, 3),
                "raw": r,
            }
        except Exception as exc:
            duration_s = timeit.default_timer() - t0
            results[label] = {
                "delta": 0.0,
                "keep": False,
                "duration_s": round(duration_s, 3),
                "error": str(exc),
            }
    return results


# ── benchmark loop ────────────────────────────────────────────────────────────


async def run_benchmark(iterations: int, use_llm: bool) -> None:
    print("[evo_benchmark] Autoharness health check...", flush=True)
    health = autoharness_health_check()
    print(f"  overnight_evo_loop: {health['status']}", flush=True)
    if health["status"] != "ok":
        print(f"  FAIL: {health}", flush=True, file=sys.stderr)
        sys.exit(1)

    # Load evo module once for the whole benchmark
    spec = importlib.util.spec_from_file_location(
        "overnight_evo_loop", _REPO / "scripts" / "overnight_evo_loop.py"
    )
    assert spec and spec.loader
    evo = importlib.util.module_from_spec(spec)
    sys.modules["overnight_evo_loop"] = evo
    spec.loader.exec_module(evo)  # type: ignore[attr-defined]

    print(
        f"[evo_benchmark] Starting {iterations} iteration(s), use_llm={use_llm}",
        flush=True,
    )
    print(f"[evo_benchmark] Log: {BENCH_LOG}", flush=True)

    all_deltas: list[float] = []
    all_keeps: list[bool] = []
    bench_start = timeit.default_timer()

    for i in range(iterations):
        iter_start = timeit.default_timer()
        print(f"\n[evo_benchmark] Iteration {i + 1}/{iterations}", flush=True)
        results = await run_schedule_once(evo, use_llm)
        iter_duration = timeit.default_timer() - iter_start

        for label, r in results.items():
            all_deltas.append(r["delta"])
            all_keeps.append(r["keep"])
            status = "KEEP" if r["keep"] else ("ERR" if "error" in r else "DISC")
            print(
                f"  {label}: delta={r['delta']:+.4f} {status} {r['duration_s']:.1f}s",
                flush=True,
            )

        # Log to bench JSONL
        record = {
            "ts": datetime.now().isoformat(),
            "iteration": i,
            "duration_s": round(iter_duration, 3),
            "use_llm": use_llm,
            "results": {
                k: {kk: vv for kk, vv in v.items() if kk != "raw"} for k, v in results.items()
            },
        }
        with BENCH_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")

    total_elapsed = timeit.default_timer() - bench_start
    n_exps = len(all_deltas)
    keep_rate = sum(all_keeps) / n_exps if n_exps else 0.0
    mean_delta = sum(all_deltas) / n_exps if n_exps else 0.0
    throughput = n_exps / (total_elapsed / 60) if total_elapsed > 0 else 0.0

    print(f"\n{'=' * 60}", flush=True)
    print("[evo_benchmark] DONE", flush=True)
    print(f"  iterations       : {iterations}", flush=True)
    print(f"  total_experiments: {n_exps}", flush=True)
    print(f"  keep_rate        : {keep_rate:.1%}", flush=True)
    print(f"  mean_delta       : {mean_delta:+.4f}", flush=True)
    print(f"  throughput       : {throughput:.1f} experiments/min", flush=True)
    print(f"  elapsed          : {total_elapsed:.1f}s", flush=True)
    print(f"  log              : {BENCH_LOG}", flush=True)


# ── entry point ───────────────────────────────────────────────────────────────


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark the optimal EVO experiment schedule")
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=10,
        help="Number of full-schedule passes (default: 10)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick smoke test: 1 iteration, no LLM",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable LLM (Lemonade) calls (default: heuristic/no-LLM)",
    )
    args = parser.parse_args()

    iterations = 1 if args.quick else args.iterations
    use_llm = args.llm and not args.quick

    asyncio.run(run_benchmark(iterations=iterations, use_llm=use_llm))
