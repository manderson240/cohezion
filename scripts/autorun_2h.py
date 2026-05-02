"""2-hour autonomous EVO research driver.

Integrates four pillars:
  timeit          — timeit.default_timer() microsecond-precision per-experiment timing
  autodata        — rolling JSONL analysis: keep_frac, mean_delta, per-experiment stats
  autoresearch    — AutoresearchEngine inter-cycle opportunity analysis
  autoharness     — CompoundEngineeringAutoHarness token/coherence health checks

Session log: autoresearch_2h_<timestamp>.jsonl
Run:
  uv run python scripts/autorun_2h.py [--hours 2] [--no-llm]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import timeit
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# ── path setup ──────────────────────────────────────────────────────────────
_REPO = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("autorun_2h")

# ── session log ──────────────────────────────────────────────────────────────
_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_LOG = _REPO / f"autoresearch_2h_{_TS}.jsonl"

_STOP = False


def _install_sigint() -> None:
    def _handler(sig: int, frame: Any) -> None:
        global _STOP
        print("\n[autorun_2h] SIGINT — stopping after current experiment.", flush=True)
        _STOP = True

    signal.signal(signal.SIGINT, _handler)


# ── timed experiment wrapper ─────────────────────────────────────────────────


@dataclass
class ExperimentTiming:
    label: str
    duration_s: float
    result: dict
    keep: str  # "keep" | "discard" | "error"
    cycle: int
    wall_ts: str = field(default_factory=lambda: datetime.now().isoformat())


async def run_timed(label: str, fn, cycle: int) -> ExperimentTiming:
    """Run experiment fn(), measure with timeit.default_timer, return ExperimentTiming."""
    t0 = timeit.default_timer()
    keep = "discard"
    result: dict = {}
    try:
        result = await fn() or {}
        # Infer keep from result fields (overnight loop convention)
        if isinstance(result, dict):
            delta = result.get("delta", result.get("gain", result.get("coherence_delta", 0.0)))
            if isinstance(delta, (int, float)) and delta > 0:
                keep = "keep"
    except Exception as exc:
        import traceback

        result = {"error": str(exc)}
        keep = "error"
        traceback.print_exc(file=sys.stderr)

    duration_s = timeit.default_timer() - t0
    timing = ExperimentTiming(
        label=label, duration_s=duration_s, result=result, keep=keep, cycle=cycle
    )
    _log_session(timing)
    return timing


def _log_session(t: ExperimentTiming) -> None:
    """Append timing record to session JSONL (autodata)."""
    record = {
        "label": t.label,
        "cycle": t.cycle,
        "duration_s": round(t.duration_s, 4),
        "keep": t.keep,
        "result": t.result,
        "ts": t.wall_ts,
    }
    with SESSION_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


# ── autodata: rolling JSONL analysis ────────────────────────────────────────


def analyze_session_data(timings: list[ExperimentTiming]) -> dict:
    """Compute per-label keep_frac, mean_duration, mean_delta from timing list (autodata)."""
    by_label: dict[str, list[ExperimentTiming]] = defaultdict(list)
    for t in timings:
        by_label[t.label].append(t)

    stats: dict[str, dict] = {}
    for label, ts in by_label.items():
        keep_frac = sum(1 for t in ts if t.keep == "keep") / len(ts)
        mean_dur = sum(t.duration_s for t in ts) / len(ts)
        deltas = [
            t.result.get("delta", t.result.get("gain", t.result.get("coherence_delta", 0.0)))
            for t in ts
            if isinstance(
                t.result.get("delta", t.result.get("gain", t.result.get("coherence_delta"))),
                (int, float),
            )
        ]
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        stats[label] = {
            "n": len(ts),
            "keep_frac": round(keep_frac, 3),
            "mean_duration_s": round(mean_dur, 2),
            "mean_delta": round(mean_delta, 4),
        }
    return stats


# ── autoresearch: AutoresearchEngine analysis ────────────────────────────────


async def run_autoresearch_analysis(timings: list[ExperimentTiming], cycle: int) -> list[dict]:
    """Feed session data into AutoresearchEngine, surface top improvement opportunities."""
    try:
        from cohezion.compound.autoresearch import AutoresearchEngine

        stats = analyze_session_data(timings)
        total_runs = len(timings)
        kept = sum(1 for t in timings if t.keep == "keep")
        mean_dur = sum(t.duration_s for t in timings) / total_runs if total_runs else 0.0

        metrics = {
            "cache_hit_rate": kept / total_runs if total_runs else 0.0,
            "avg_tokens_per_request": 0,
            "vault_write_latency_ms": 0,
            "avg_coherence": sum(
                float(t.result.get("final_evo_coherence", t.result.get("delta", 0.5)))
                for t in timings
                if isinstance(t.result, dict)
            )
            / total_runs
            if total_runs
            else 0.5,
            "mean_duration_s": mean_dur,
            "per_experiment": stats,
        }

        engine = AutoresearchEngine()
        opportunities = await engine.analyze(metrics)

        top = [
            {
                "category": o.category,
                "priority": o.priority,
                "recommendation": o.recommendation,
                "potential_impact": o.potential_impact,
            }
            for o in opportunities[:3]
        ]

        if top:
            print(f"\n[autoresearch] Cycle {cycle} opportunities:", flush=True)
            for o in top:
                print(
                    f"  [{o['priority']}] {o['category']}: {o['recommendation'][:80]}", flush=True
                )

        return top

    except Exception as exc:
        logger.debug("AutoresearchEngine unavailable: %s", exc)
        return []


# ── autoharness: CompoundEngineeringAutoHarness health ───────────────────────


def run_autoharness_check(timings: list[ExperimentTiming], cycle: int) -> dict:
    """Use CompoundEngineeringAutoHarness to track token budget and generation health."""
    try:
        from cohezion.inference.autoharness_ce import CompoundEngineeringAutoHarness

        harness = CompoundEngineeringAutoHarness(model_id="Gemma-4-E4B-it-GGUF")

        # Track timing improvements across cycles as a token-budget proxy
        # Each kept experiment = one "optimized" compound cycle
        kept = sum(1 for t in timings if t.keep == "keep")
        total = len(timings)
        harness.budget.baseline_tokens = total * 1000  # proxy: 1k tokens per run
        harness.budget.optimized_tokens = (
            total - kept
        ) * 1000 + kept * 600  # kept runs = 40% efficient
        harness.budget.reference_savings = kept * 400

        report = harness.budget.report()
        gen = harness.oroborous.generation

        print(
            f"[autoharness] Cycle {cycle}: "
            f"efficiency={report['efficiency_gain_pct']:.1f}% "
            f"oroborous_gen={gen} "
            f"keep_frac={kept}/{total}",
            flush=True,
        )
        return {
            "efficiency_pct": report["efficiency_gain_pct"],
            "generation": gen,
            "kept": kept,
            "total": total,
        }

    except Exception as exc:
        logger.debug("CompoundEngineeringAutoHarness unavailable: %s", exc)
        return {}


# ── main 2-hour loop ─────────────────────────────────────────────────────────


async def main(hours: float = 2.0, use_llm: bool = True) -> None:
    global _STOP
    _install_sigint()

    # Import experiment functions from the overnight loop
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "overnight_evo_loop", _REPO / "scripts" / "overnight_evo_loop.py"
    )
    assert spec and spec.loader
    evo = importlib.util.module_from_spec(spec)
    sys.modules["overnight_evo_loop"] = evo
    spec.loader.exec_module(evo)  # type: ignore[attr-defined]

    # Wire the persistence stack (mirrors overnight_evo_loop.main())
    from cohezion.core.journey_worker import get_journey_worker
    from cohezion.core.telemetry_bus import get_telemetry_bus

    bus = get_telemetry_bus()
    worker = get_journey_worker()
    await bus.start()
    await worker.start()

    if worker._db.connected:
        await worker._db.ensure_journey(
            journey_id="autorun_2h",
            agent_id="autorun_2h_driver",
            intent="2-hour EVO autoresearch with timeit, autodata, autoresearch, autoharness",
        )

    # LLM probe
    if use_llm:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{evo.LEMONADE_BASE}/models")
                if r.status_code != 200:
                    use_llm = False
        except Exception:
            use_llm = False

    print(f"[autorun_2h] Session log: {SESSION_LOG}", flush=True)
    print(
        f"[autorun_2h] LLM={use_llm}  Deadline: {hours}h  Start: {datetime.now().isoformat()}",
        flush=True,
    )

    # SCHEDULE — mirrors overnight_evo_loop.py SCHEDULE (with timeit wrapping added here)
    SCHEDULE = [
        (
            "E12_persist",
            lambda: evo.experiment_e12_persistent_evo(n_deliberations=100, use_llm=use_llm),
        ),
        (
            "E63_mycelium",
            lambda: evo.experiment_e63_mycelium_closed_loop(
                n_phase=10, use_llm=use_llm, learning_rate=1.0
            ),
        ),
        (
            "E51_quality",
            lambda: evo.experiment_e51_evo_quality_sensitivity(n_ticks=100, use_llm=use_llm),
        ),
        (
            "E12_persist_xl",
            lambda: evo.experiment_e12_persistent_evo(n_deliberations=200, use_llm=use_llm),
        ),
        (
            "E63_mycelium_lr2",
            lambda: evo.experiment_e63_mycelium_closed_loop(
                n_phase=10, use_llm=use_llm, learning_rate=2.0
            ),
        ),
        (
            "E51_quality_xl",
            lambda: evo.experiment_e51_evo_quality_sensitivity(n_ticks=200, use_llm=use_llm),
        ),
        (
            "E46_jepa_train",
            lambda: evo.experiment_e46_jepa_learning(n_train_steps=20, use_llm=use_llm),
        ),
        (
            "E12_persist_xxl",
            lambda: evo.experiment_e12_persistent_evo(n_deliberations=500, use_llm=use_llm),
        ),
        ("E47_voice", lambda: evo.experiment_e47_voice_profiles(use_llm=use_llm)),
    ]

    DEADLINE = timeit.default_timer() + hours * 3600
    EXPERIMENT_TIMEOUT = 3600  # 1h per experiment max
    all_timings: list[ExperimentTiming] = []
    cycle = 0

    while not _STOP and timeit.default_timer() < DEADLINE:
        remaining_s = DEADLINE - timeit.default_timer()
        print(
            f"\n{'=' * 60}\n[autorun_2h] Cycle {cycle} — {remaining_s / 60:.1f} min remaining\n{'=' * 60}",
            flush=True,
        )

        for label, fn in SCHEDULE:
            if _STOP or timeit.default_timer() >= DEADLINE:
                break

            remaining_s = DEADLINE - timeit.default_timer()
            print(f"\n[autorun_2h] → {label} ({remaining_s / 60:.1f} min left)", flush=True)

            try:
                timing = await asyncio.wait_for(
                    run_timed(label, fn, cycle),
                    timeout=min(EXPERIMENT_TIMEOUT, remaining_s - 10),
                )
            except TimeoutError:
                timing = ExperimentTiming(
                    label=label,
                    duration_s=EXPERIMENT_TIMEOUT,
                    result={"error": "timeout"},
                    keep="error",
                    cycle=cycle,
                )
                _log_session(timing)

            all_timings.append(timing)
            print(
                f"  ✓ {label}: {timing.duration_s:.1f}s  keep={timing.keep}",
                flush=True,
            )

        # Between cycles: autodata analysis + autoresearch + autoharness
        if all_timings:
            stats = analyze_session_data(all_timings)
            print(f"\n[autodata] Cycle {cycle} summary:", flush=True)
            for lbl, s in stats.items():
                print(
                    f"  {lbl}: n={s['n']} keep_frac={s['keep_frac']:.0%} "
                    f"mean_dur={s['mean_duration_s']:.0f}s mean_delta={s['mean_delta']:+.4f}",
                    flush=True,
                )

            await run_autoresearch_analysis(all_timings, cycle)
            run_autoharness_check(all_timings, cycle)

        cycle += 1

    # Session summary
    elapsed = timeit.default_timer() - (DEADLINE - hours * 3600)
    total_experiments = len(all_timings)
    kept = sum(1 for t in all_timings if t.keep == "keep")
    print(
        f"\n[autorun_2h] DONE  elapsed={elapsed / 3600:.2f}h  experiments={total_experiments}  kept={kept}",
        flush=True,
    )

    if all_timings:
        final_stats = analyze_session_data(all_timings)
        summary = {
            "session_log": str(SESSION_LOG),
            "elapsed_h": round(elapsed / 3600, 3),
            "total_experiments": total_experiments,
            "kept": kept,
            "keep_frac": round(kept / total_experiments, 3),
            "cycles_completed": cycle,
            "per_experiment": final_stats,
        }
        summary_path = _REPO / f"autoresearch_2h_{_TS}_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        print(f"[autorun_2h] Summary: {summary_path}", flush=True)

        # Final autoharness report
        run_autoharness_check(all_timings, cycle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2-hour autonomous EVO research driver")
    parser.add_argument("--hours", type=float, default=2.0, help="Run duration in hours")
    parser.add_argument("--no-llm", action="store_true", help="Force heuristic mode (no Lemonade)")
    args = parser.parse_args()

    asyncio.run(main(hours=args.hours, use_llm=not args.no_llm))
