#!/usr/bin/env python3
"""Refactor traces into actionable goals and closed loops.

One scan reads BOTH event_log databases (``vault``: session-published findings via
the event bridge; ``main``: git-post-commit JOURNEY_STEP + health telemetry) plus
open kanban cards, tags every row with the database it came from, synthesizes
GoalSpecifications, executes ONE measured loop iteration per invocation, and
persists goal + loop_trace durably (ERR-checked -- never the silent-loss trap).
Goals are written to db=main regardless of where their traces were read.

The loop is closed ACROSS runs, not within one: re-measuring an unchanged system
five times in a single process yields five identical readings. Convergence flips
the goal's status so ``fetch_open_goals`` stops returning it.

A goal is only EXECUTED when a real measurement source exists for its metric (see
``trace_goal_sources.MEASUREMENTS``). Others are persisted as synthesized-only and
reported as such -- the runner never invents a metric value.

Usage:
    python scripts/ops/refactor_traces_to_goals.py --dry-run     # default: print, no writes
    python scripts/ops/refactor_traces_to_goals.py --limit 50 --execute
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


sys.path.insert(0, "src")

from cohezion.flume.goal_graph import format_status, graph_status
from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    TraceGoalRefactorPipeline,
)
from cohezion.flume.trace_goal_sources import (
    ERROR_RATE_WINDOW,
    MEASUREMENTS,
    GoalDraft,
    fetch_event_traces,
    scan_traces,
    sql,
    synthesize_scan,
)


GOAL_DB = "main"
DEFAULT_SESSION = "trace-goal-loop"


def fetch_recent_traces(limit: int, database: str = "main") -> list[dict]:
    """Newest finding-type event_log rows from ONE database.

    Kept for its live importers (``cohezion ops refactor-traces`` in cli/main.py and
    ``UnifiedPerpetualLoopDaemon.run_trace_refactor_phase``). New code uses
    ``trace_goal_sources.scan_traces`` (vault + main + kanban, tagged).
    """
    return fetch_event_traces(
        limit, database, ("SECURITY_VIOLATION", "SYSTEM_HEALTH", "AGENT_COMPLETE")
    )


def _make_step_fn(draft: GoalDraft):
    """Bind a real measurement into the loop's (iteration, state) -> step contract."""
    metric = draft.goal.target_metric
    trace = draft.trace
    database = str(trace.get("_source_db") or GOAL_DB)

    def step_fn(iteration: int, state: Any) -> tuple[Any, float, str]:
        value = MEASUREMENTS[metric](trace, database)
        if value is None:
            raise RuntimeError(f"measurement for {metric} returned UNKNOWN; refusing to fabricate")
        source = trace.get("source")
        return (
            {"source": source, "measured": value},
            float(value),
            f"measured {metric}={value:.4f} (db={database}, window {ERROR_RATE_WINDOW}, {source})",
        )

    return step_fn


def _origin_ids(draft: GoalDraft) -> list[str]:
    return [f"{r['source_db']}:{r['source_id']}" for r in draft.derived_from]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="rows to scan PER source")
    parser.add_argument(
        "--database",
        default=None,
        choices=["main", "vault"],
        help="restrict the scan to ONE event_log database (default: the tagged vault+main "
        "event scan plus open kanban cards)",
    )
    parser.add_argument(
        "--goal-db", default=GOAL_DB, help="database goals/loops/edges are written to"
    )
    parser.add_argument(
        "--session", default=DEFAULT_SESSION, help="session tag written on every row this run adds"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="print the goal/loop graph (per-domain counts, unlinked goals/loops, rungs, "
        "newest mirrors) read from goal_graph + canonical nodes; writes nothing",
    )
    parser.add_argument(
        "--execute",
        "--persist",
        dest="execute",
        action="store_true",
        help="execute + persist loops (default: dry-run)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print synthesized goals, write nothing (default)"
    )
    args = parser.parse_args()

    if args.status:
        try:
            print(format_status(graph_status(lambda stmt: sql(stmt, args.goal_db))))
        except Exception as exc:
            print(f"FAIL: could not read the goal graph in db={args.goal_db}: {exc}")
            return 1
        return 0

    try:
        traces = scan_traces(args.limit, database=args.database)
    except Exception as exc:
        print(f"FAIL: could not read traces: {exc}")
        return 1

    by_origin: dict[tuple[str, str], int] = {}
    for t in traces:
        key = (str(t["_source_db"]), str(t["_source_table"]))
        by_origin[key] = by_origin.get(key, 0) + 1
    print(
        "Scanned "
        + ", ".join(f"{n} {tbl}@{db}" for (db, tbl), n in sorted(by_origin.items()))
        + " (ns=cohezion)"
    )

    drafts = synthesize_scan(traces)
    if not drafts:
        print("No actionable signals found — no goals synthesized.")
        return 0

    executable = [d for d in drafts if d.goal.target_metric in MEASUREMENTS]
    unmeasurable = [d for d in drafts if d.goal.target_metric not in MEASUREMENTS]

    print(f"Synthesized {len(drafts)} goals ({len(executable)} executable):")
    for d in drafts:
        g = d.goal
        op = "<=" if g.direction == "at_most" else ">="
        mark = "loop" if g.target_metric in MEASUREMENTS else "no measurement source"
        dbs = sorted({r["source_db"] for r in d.derived_from})
        print(
            f"  - [{g.target_metric} {op} {g.target_threshold}] {g.title}"
            f"  ({mark}; derived_from source_db={','.join(dbs)})"
        )

    if unmeasurable:
        print(
            f"\n{len(unmeasurable)} goal(s) have no measurement source and will be recorded "
            "without an executed loop. Add an entry to MEASUREMENTS to close them."
        )

    if not args.execute:
        print("\n(dry-run: no writes. Re-run with --execute to persist.)")
        return 0

    persistence = DurableSurrealGoalPersistence(database=args.goal_db)
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    failures = 0

    for d in executable:
        try:
            # max_iterations=1: one iteration per invocation; the loop closes across runs.
            _, result = pipeline.refactor(
                [d.trace],
                trace_ids=_origin_ids(d),
                step_fn=_make_step_fn(d),
                max_iterations=1,
                goal=d.goal,
                derived_from=d.derived_from,
                domain="trace",
                session=args.session,
            )
            if result is None:
                continue
            verdict = "CONVERGED" if result.converged else "open"
            print(
                f"  {verdict}: {d.goal.title} — {d.goal.target_metric}={result.final_metric:.4f} "
                f"({result.iterations_run} iteration, {result.total_time_ms} ms)"
            )
        except Exception as exc:
            failures += 1
            print(f"  FAIL executing {d.goal.goal_id}: {exc}")

    for d in unmeasurable:
        try:
            persistence.persist_goal(
                d.goal,
                origin_trace_ids=_origin_ids(d),
                domain="trace",
                session=args.session,
                derived_from=d.derived_from,
            )
            print(f"  recorded (no loop): {d.goal.title}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL persisting {d.goal.goal_id}: {exc}")

    try:
        open_goals = persistence.fetch_open_goals()
        print(f"\nOpen goals still active after this run: {len(open_goals)}")
        for row in open_goals:
            print(f"  - {row.get('title')} [{row.get('target_metric')}]")
    except Exception as exc:
        print(f"  WARN: could not read back open goals: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
