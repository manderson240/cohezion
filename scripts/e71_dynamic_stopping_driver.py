"""E71: Dynamic stopping rule — exploit E67's measured decay constant.

Standalone driver (does not modify overnight_evo_loop.py to avoid file thrash).
Imports the EVO helpers from the overnight loop module by file path.

Background (from E67, run 3, 2026-05-02):
  |delta_cal| sequence: [0.125, 0.063, 0.031, 0.015, 0.008, 0.004, 0.002, 0.001, 0.0, 0.0]
  → halves every cycle (10x faster than E67's 3-cycle hypothesis).

Hypothesis: stopping mycelium feedback when |delta_cal| < epsilon reaches
the same final consensus as E64's fixed 5-cycle baseline, but in fewer
refinement cycles → wall-time savings + lower overfit risk.

Run: uv run python scripts/e71_dynamic_stopping_driver.py
Logs: appends to autoresearch.jsonl (asi.experiment="E71")
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import math
import sys
import time
import timeit
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

# Import overnight_evo_loop helpers without colliding with concurrent edits
_spec = importlib.util.spec_from_file_location(
    "overnight_evo_loop", REPO / "scripts" / "overnight_evo_loop.py"
)
assert _spec and _spec.loader
evo = importlib.util.module_from_spec(_spec)
sys.modules["overnight_evo_loop_e71"] = evo
_spec.loader.exec_module(evo)

JSONL_PATH = REPO / "autoresearch.jsonl"


def _next_run() -> int:
    """Read max run number from JSONL, return next."""
    if not JSONL_PATH.exists():
        return 1
    last = 0
    for line in JSONL_PATH.read_text().splitlines():
        try:
            last = max(last, json.loads(line).get("run", 0))
        except Exception:
            pass
    return last + 1


def log_e71(run: int, metrics: dict, status: str, description: str, **extra) -> None:
    """Append E71 result to autoresearch.jsonl in the existing format."""
    entry = {
        "run": run,
        "metric": metrics.get("final_consensus", 0.0),
        "metrics": metrics,
        "status": status,
        "description": description,
        "timestamp": int(time.time() * 1000),
        "segment": 99,
        "confidence": 1.0,
        "asi": {"experiment": "E71", **extra},
    }
    with JSONL_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  [E71] run={run} {status} — {description}", flush=True)


async def run_dynamic_stop(
    max_cycles: int,
    n_phase: int,
    epsilon: float,
    use_llm: bool,
) -> dict:
    """Run E64-style compounding loop with adaptive early-stop on |delta_cal|."""
    from cohezion.learning.mycelium_registry import MyceliumRegistry
    from cohezion.swarm.quadrature_nexus import VoiceType

    evo._reset_shared_nexus()
    nexus = evo._get_shared_nexus()
    t0 = timeit.default_timer()

    prev_cal: dict = dict.fromkeys(VoiceType, 0.0)
    cycle_means: list[float] = []
    cycle_deltas_cal: list[float] = []
    stopped_at_cycle = -1
    stop_reason = "max_cycles"

    for cycle_idx in range(max_cycles):
        # Phase A
        phase_a: list[float] = []
        event_metas: list[dict] = []
        for i in range(n_phase):
            d = await evo.run_llm_deliberation(
                action=f"e71_eps{epsilon}_c{cycle_idx}_a{i}",
                description="Deploy scheduled system update",
                priority=0.50,
                budget=False,
                use_llm=use_llm,
            )
            phase_a.append(d["consensus"])
            if d.get("event_metadata"):
                event_metas.append(d["event_metadata"])

        skill_applied = False
        if event_metas:
            registry = MyceliumRegistry(min_entries_for_pattern=2)
            if registry.ingest_evo_journeys(event_metas) >= 1:
                registry.run_audit()
                skill = registry.skills.get("EVO_DELIBERATION_SYNTHESIZED")
                if skill:
                    nexus.apply_mycelium_feedback(skill.skill_content, learning_rate=1.0)
                    skill_applied = True

        cur_cal = dict(nexus._mycelium_calibration)
        delta_cal = math.sqrt(sum((cur_cal[v] - prev_cal.get(v, 0.0)) ** 2 for v in VoiceType))
        cycle_deltas_cal.append(delta_cal)
        prev_cal = cur_cal

        # Phase B
        phase_b: list[float] = []
        for i in range(n_phase):
            d = await evo.run_llm_deliberation(
                action=f"e71_eps{epsilon}_c{cycle_idx}_b{i}",
                description="Deploy scheduled system update",
                priority=0.50,
                budget=False,
                use_llm=use_llm,
            )
            phase_b.append(d["consensus"])

        mean_b = sum(phase_b) / len(phase_b) if phase_b else 0.0
        cycle_means.append(mean_b)

        print(
            f"  eps={epsilon} c{cycle_idx + 1}/{max_cycles}: |Δcal|={delta_cal:.5f} "
            f"-> consensus={mean_b:.4f} skill={skill_applied}",
            flush=True,
        )

        # Use <= so a delta exactly equal to epsilon also fires
        if cycle_idx >= 1 and delta_cal <= epsilon:
            stopped_at_cycle = cycle_idx + 1
            stop_reason = f"|Δcal|={delta_cal:.6f} <= epsilon={epsilon}"
            print(f"  >>> EARLY STOP: {stop_reason}", flush=True)
            break

    if stopped_at_cycle == -1:
        stopped_at_cycle = len(cycle_means)

    final_consensus = cycle_means[-1] if cycle_means else 0.0
    wall_time_s = timeit.default_timer() - t0
    cycles_saved = max_cycles - stopped_at_cycle
    pct_savings = cycles_saved / max_cycles * 100.0 if max_cycles else 0.0

    return {
        "epsilon": epsilon,
        "stopped_at_cycle": stopped_at_cycle,
        "stop_reason": stop_reason,
        "max_cycles": max_cycles,
        "cycles_saved": cycles_saved,
        "pct_savings": round(pct_savings, 1),
        "final_consensus": round(final_consensus, 4),
        "cycle_means": [round(c, 4) for c in cycle_means],
        "cycle_deltas_cal": [round(d, 5) for d in cycle_deltas_cal],
        "n_phase": n_phase,
        "used_llm": use_llm,
        "wall_time_s": round(wall_time_s, 3),
    }


async def main() -> None:
    use_llm = False  # heuristic mode for first-pass calibration
    max_cycles = 8
    n_phase = 4
    # Epsilon sweep — find the elbow (minimum saved cycles without consensus loss)
    epsilons = [0.05, 0.01, 0.005, 0.002, 0.001]

    results: list[dict] = []
    print(f"=== E71 epsilon sweep (max_cycles={max_cycles}, n_phase={n_phase}, llm={use_llm}) ===")
    for eps in epsilons:
        r = await run_dynamic_stop(max_cycles, n_phase, eps, use_llm)
        results.append(r)

    # Find the optimal epsilon: largest pct_savings with final_consensus >= 0.84
    # (within 0.5% of full-loop final ≈ 0.8495)
    CONSENSUS_FLOOR = 0.84
    qualifying = [r for r in results if r["final_consensus"] >= CONSENSUS_FLOOR]
    if qualifying:
        optimal = max(qualifying, key=lambda r: r["pct_savings"])
    else:
        optimal = max(results, key=lambda r: r["final_consensus"])

    print("\n=== E71 sweep summary ===")
    print(f"{'epsilon':>10} {'stop@':>6} {'final':>7} {'saved%':>7} {'wall_s':>7}")
    for r in results:
        marker = "  <-- optimal" if r is optimal else ""
        print(
            f"{r['epsilon']:>10.4f} {r['stopped_at_cycle']:>6d} "
            f"{r['final_consensus']:>7.4f} {r['pct_savings']:>6.0f}% "
            f"{r['wall_time_s']:>7.3f}{marker}"
        )

    # Log the sweep result + the optimal as separate JSONL entries
    run = _next_run()
    log_e71(
        run,
        {
            "sweep_results": results,
            "optimal_epsilon": optimal["epsilon"],
            "optimal_stopped_at_cycle": optimal["stopped_at_cycle"],
            "optimal_pct_savings": optimal["pct_savings"],
            "optimal_final_consensus": optimal["final_consensus"],
            "optimal_wall_time_s": optimal["wall_time_s"],
            "consensus_floor": CONSENSUS_FLOOR,
            "max_cycles": max_cycles,
            "n_phase": n_phase,
            "used_llm": use_llm,
            "duration_s": sum(r["wall_time_s"] for r in results),
            "final_consensus": optimal["final_consensus"],
        },
        "keep" if optimal["pct_savings"] > 0 else "discard",
        f"E71 sweep: optimal eps={optimal['epsilon']} stops_at={optimal['stopped_at_cycle']}/{max_cycles} "
        f"saved={optimal['pct_savings']:.0f}% final={optimal['final_consensus']:.4f}",
        optimal_epsilon=optimal["epsilon"],
        optimal_pct_savings=optimal["pct_savings"],
    )

    # Also write a structured summary file
    out = REPO / "scripts" / "e71_summary.json"
    out.write_text(json.dumps({"sweep": results, "optimal": optimal}, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
