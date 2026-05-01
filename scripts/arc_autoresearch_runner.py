#!/usr/bin/env python3
"""Overnight ARC Autoresearch Runner — Thermal-protected, K-Search backed.

Runs until TARGET_DEADLINE (7:00 AM local). Saves checkpoint every 10 tasks.
Metrics: solve_rate on training subset, logged to K-Search tree.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cohezion.arc.solver import evaluate_on_subset, update_ksearch


TARGET_DEADLINE = datetime.fromisoformat(os.environ.get("ARDeadline", datetime.now().replace(hour=7, minute=0, second=0).isoformat()))
CHECKPOINT_PATH = Path.home() / ".cohezion-research/arc_overnight.json"
REPORT_PATH = Path.home() / ".cohezion-research/arc_overnight_report.md"


def _seconds_remaining() -> float:
    return (TARGET_DEADLINE - datetime.now()).total_seconds()


def _load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {"tasks_done": 0, "total_solved": 0, "best_solve_rate": 0.0, "history": []}


def _save_checkpoint(state: dict) -> None:
    CHECKPOINT_PATH.write_text(json.dumps(state, indent=2, default=str))


def _thermal_check() -> bool:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = int(f.read().strip()) / 1000.0
        return temp < 85.0
    except Exception:
        return True


def main():
    print(f"[{datetime.now().isoformat()}] ARC Overnight Autoresearch START")
    print(f"Deadline: {TARGET_DEADLINE.isoformat()}")
    state = _load_checkpoint()

    # Progressive search config: fast -> deep
    configs = [
        {"limit": 20, "time_per_task": 5.0,  "beam_width": 4,  "max_depth": 2},
        {"limit": 40, "time_per_task": 10.0, "beam_width": 8,  "max_depth": 3},
        {"limit": 80, "time_per_task": 15.0, "beam_width": 12, "max_depth": 3},
        {"limit": None, "time_per_task": 20.0, "beam_width": 16, "max_depth": 4},
    ]

    for cfg in configs:
        if _seconds_remaining() < 60:
            break
        if not _thermal_check():
            print(f"[{datetime.now().isoformat()}] THERMAL PAUSE (temp >85C)")
            time.sleep(60)
            continue

        print(f"\nConfig: {cfg}")
        metrics = evaluate_on_subset("training", limit=cfg["limit"], time_per_task=cfg["time_per_task"])
        solve_rate = metrics["solve_rate"]
        state["tasks_done"] += metrics["total"]
        state["total_solved"] += metrics["solved"]
        state["history"].append({
            "timestamp": datetime.now().isoformat(),
            "config": cfg,
            "solve_rate": solve_rate,
            "solved": metrics["solved"],
            "total": metrics["total"],
        })
        if solve_rate > state["best_solve_rate"]:
            state["best_solve_rate"] = solve_rate
        _save_checkpoint(state)

        # Update K-Search with winning chains
        for d in metrics["details"]:
            if d["match"]:
                update_ksearch(d.get("chain", []), 1.0)

        print(f"  solve_rate={solve_rate:.2%} | best={state['best_solve_rate']:.2%} | remaining={_seconds_remaining()/3600:.1f}h")

    # Final report
    report = f"""# ARC Overnight Autoresearch Report
Generated: {datetime.now().isoformat()}
Deadline : {TARGET_DEADLINE.isoformat()}
Tasks evaluated: {state["tasks_done"]}
Total solved   : {state["total_solved"]}
Best solve rate: {state["best_solve_rate"]:.2%}

## History
| Time | Config | Solve Rate |
|------|--------|------------|
"""
    for h in state["history"]:
        report += f"| {h['timestamp'][:19]} | {h['config']} | {h['solve_rate']:.2%} |\n"

    REPORT_PATH.write_text(report)
    print(f"\n[{datetime.now().isoformat()}] DONE. Report: {REPORT_PATH}")
    print(f"Best solve rate achieved: {state['best_solve_rate']:.2%}")


if __name__ == "__main__":
    main()
