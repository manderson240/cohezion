"""EXP-trust-efficacy — does efficacy-weighting or recency-gating beat frequency for guidance injection?

Surfaced by the WS-DRIVER adversarial review (RETRO-2026-06-02g/h): the compound loop writes a
fault-guard into a GroundTruthHierarchy and re-corroborates it on every recurrence, so trust tracks
fault FREQUENCY, not guard EFFICACY — and the min_trust floor then selects for the most-recurring
(often least-fixable) guards. This experiment tests two independent levers against the status quo:

  WRITE policy:
    * frequency — corroborate the guard on every occurrence (current behaviour).
    * efficacy  — corroborate while the guard is NOT yet active; CONTRADICT when the fault recurs
                  while its guard is already being injected (the guard was supposed to prevent it).
  READ gate:
    * trust      — inject guards with trust >= floor (current behaviour).
    * +recency   — additionally require the fault to have occurred within a recency window
                   (a fixed fault stops recurring, so its guard should age out of the budget).

4 arms = {frequency, efficacy} x {trust, trust+recency}.

Deterministic seeded simulation (no LLM / no network): a population of fault MODES, a fraction
``fixable`` (once their guard is injected, future occurrences are prevented) and the rest unfixable
(recur regardless). We stream T tasks, update trust per the arm's write policy, and at each task
measure VALUE-PRECISION of the injected set:

    value-precision = (# injected guards whose mode is currently ACTIVE-and-UNFIXED) / (# injected)

Rationale: a guard for a CURRENTLY-recurring fault is worth surfacing to the planner (even if the
fault is unfixable — "you keep hitting this"); a guard for an already-FIXED fault is wasted budget.
Higher value-precision = the bounded injection budget is spent on guards that matter now.

Falsifiable: if no arm beats `frequency/trust` (the status quo) by a clear margin across seeds, keep
the status quo (simplicity wins). Run logs a winner to autoresearch.jsonl.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

from cohezion.memory.trust_hierarchy import GroundTruthHierarchy


@dataclass(frozen=True)
class Arm:
    name: str
    efficacy: bool  # write policy: contradict-when-active vs corroborate-always
    recency: bool  # read gate: require recent occurrence to inject


ARMS = [
    Arm("frequency/trust", efficacy=False, recency=False),  # status quo
    Arm("efficacy/trust", efficacy=True, recency=False),
    Arm("frequency/recency", efficacy=False, recency=True),
    Arm("efficacy/recency", efficacy=True, recency=True),
]


@dataclass
class Mode:
    id: int
    fixable: bool
    rate: float  # per-task occurrence probability while active


def _guard(mode_id: int) -> str:
    return f"skill 'tool' guarded against: failure mode {mode_id}"


def simulate(
    arm: Arm,
    *,
    seed: int,
    n_modes: int = 24,
    fixable_frac: float = 0.5,
    tasks: int = 600,
    floor: float = 0.6,
    max_facts: int = 5,
    window: int = 40,
) -> float:
    """Run one arm; return mean value-precision of the injected set across tasks (where any injected)."""
    rng = random.Random(seed)
    modes = [
        Mode(i, rng.random() < fixable_frac, 0.05 + 0.25 * rng.random()) for i in range(n_modes)
    ]
    by_guard = {_guard(m.id): m.id for m in modes}
    h = GroundTruthHierarchy()
    fixed: set[int] = set()
    last_seen: dict[int, int] = {}
    value_prec: list[float] = []  # surface view: injected guards whose fault is active-and-unfixed
    effective_prec: list[
        float
    ] = []  # corrective view: injected guards that are FIXABLE (would help)
    fixable_ids = {m.id for m in modes if m.fixable}

    def active(mode_id: int, t: int) -> bool:
        return mode_id in last_seen and last_seen[mode_id] >= t - window

    def injected_modes(t: int) -> set[int]:
        chosen = [f for f in h.rank() if f.trust >= floor][:max_facts]
        ids = {by_guard[f.content] for f in chosen if f.content in by_guard}
        if arm.recency:
            ids = {m for m in ids if active(m, t)}
        return ids

    for t in range(tasks):
        inj = injected_modes(t)
        if inj:
            valuable = sum(1 for m in inj if active(m, t) and m not in fixed)
            value_prec.append(valuable / len(inj))
            # corrective view: a guard is "effective" if heeding it would actually prevent the fault
            # (the mode is fixable and not already fixed). Frequency-weighting climbs UNFIXABLE guards
            # into the top-k, which this metric penalises — the reviewer's hypothesis.
            effective = sum(1 for m in inj if m in fixable_ids and m not in fixed)
            effective_prec.append(effective / len(inj))
        # occurrence phase
        for m in modes:
            if m.fixable and m.id in fixed:
                continue  # guard worked; mode no longer occurs
            if rng.random() >= m.rate:
                continue
            guard_active = m.id in inj  # was this guard being injected at the start of the task?
            if arm.efficacy and guard_active:
                h.corroborate(
                    _guard(m.id), agree=False
                )  # recurred despite an active guard -> failed
            else:
                h.add(_guard(m.id))  # establish / strengthen the guard
            last_seen[m.id] = t
            # a fixable mode whose guard is active is prevented from recurring HENCEFORTH
            if m.fixable and guard_active:
                fixed.add(m.id)

    return {
        "value_precision": statistics.mean(value_prec) if value_prec else 1.0,
        "effective_precision": statistics.mean(effective_prec) if effective_prec else 1.0,
    }


def run(seeds=(1, 2, 3, 4, 5)) -> dict:
    results = {}
    for arm in ARMS:
        runs = [simulate(arm, seed=s) for s in seeds]
        results[arm.name] = {
            "mean_value_precision": round(statistics.mean(r["value_precision"] for r in runs), 4),
            "mean_effective_precision": round(
                statistics.mean(r["effective_precision"] for r in runs), 4
            ),
            "effective_stdev": round(
                statistics.pstdev([r["effective_precision"] for r in runs]), 4
            ),
        }
    return results


def main() -> int:
    results = run()
    # Rank on EFFECTIVE-precision — the corrective view that tests the reviewer's hypothesis
    # (does the policy stop promoting guards that don't work). value-precision is reported alongside.
    baseline = results["frequency/trust"]["mean_effective_precision"]
    ranked = sorted(results.items(), key=lambda kv: kv[1]["mean_effective_precision"], reverse=True)
    winner, wstats = ranked[0]
    lift = wstats["mean_effective_precision"] - baseline

    print("EXP-trust-efficacy — injected-guidance precision (higher = better)\n")
    print(f"  {'arm':22s} {'effective':>10s} {'value':>8s}")
    for name, st in ranked:
        flag = "  <- status quo" if name == "frequency/trust" else ""
        print(
            f"  {name:22s} {st['mean_effective_precision']:>10.4f} "
            f"{st['mean_value_precision']:>8.4f}{flag}"
        )
    print(f"\nwinner (by effective-precision): {winner}  (+{lift:.4f} vs status quo)")

    # Falsifiable verdict: require a clear margin to unseat the simpler status quo.
    is_winner = winner != "frequency/trust" and lift >= 0.05
    verdict = (
        f"{winner} beats status quo by {lift:.3f} on effective-precision"
        if is_winner
        else "status quo retained (no clear win on effective-precision)"
    )
    print(f"verdict: {verdict}")

    record = {
        "experiment": "exp_trust_efficacy",
        "results": results,
        "winner": winner,
        "lift_vs_status_quo": round(lift, 4),
        "is_winner": is_winner,
        "verdict": verdict,
        "ranked_metric": "effective_precision (injected guards that are fixable/would-help)",
        "also_reported": "value_precision (injected guards active-and-unfixed)",
    }
    log = Path(__file__).resolve().parents[2] / "autoresearch.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    print(f"\nlogged -> {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
