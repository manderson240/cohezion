#!/usr/bin/env python3
"""Refactor event_log traces into actionable goals and closed loops.

Reads recent trace rows from SurrealDB, synthesizes GoalSpecifications from
actionable signals, executes ONE measured loop iteration per invocation, and
persists goal + loop_trace durably (ERR-checked -- never the silent-loss trap).

The loop is closed ACROSS runs, not within one: re-measuring an unchanged
system five times in a single process yields five identical readings. Each
invocation contributes one iteration; convergence flips the goal's status so
`fetch_open_goals` stops returning it.

A goal is only EXECUTED when this runner has a real measurement source for its
target metric (see MEASUREMENTS). Goals whose metric has no measurement source
are persisted as synthesized-only and reported as such -- the runner never
invents a metric value, because a fabricated reading would be written to
durable storage as a convergence verdict.

Usage:
    python scripts/ops/refactor_traces_to_goals.py --dry-run   # default: print, no writes
    python scripts/ops/refactor_traces_to_goals.py --limit 50 --execute
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.request
from typing import Any


sys.path.insert(0, "src")

from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    GoalSpecification,
    TraceGoalRefactorPipeline,
    TraceToLoopTransformer,
    payload_looks_like_failure,
)


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
    "Content-Type": "text/plain",
}

# event_log.source values are agent/tool identifiers. Anything outside this
# shape is refused rather than interpolated into SurrealQL.
_SAFE_SOURCE_RE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")

# How many recent rows for a source define its measured error rate.
_ERROR_RATE_WINDOW = 200

# How many fixed_in-bearing rows to scan when deciding if a finding is resolved.
_FIXED_SCAN_LIMIT = 500


def _sql(statement: str, database: str = "vault") -> list:
    """Run SurrealQL; raise on embedded ERR (the HTTP-200-with-ERR trap)."""
    headers = {**SURREAL_HEADERS, "surreal-db": database}
    req = urllib.request.Request(
        SURREAL_URL, data=statement.encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 — fixed literal localhost url
        body = json.loads(r.read())
    rows: list = []
    for stmt in body:
        if stmt.get("status") == "ERR":
            raise RuntimeError(f"SurrealDB error: {stmt.get('result')}")
        rows.extend(stmt.get("result") or [])
    return rows


def fetch_recent_traces(limit: int, database: str = "vault") -> list[dict]:
    """Pull the newest event_log rows across the trace-bearing types.

    NB: db=vault carries the CrossSessionEventBridge's event_log, where
    session-published findings land. db=main holds the git-post-commit
    lifecycle stream (session_end / heartbeat), which carries no actionable
    findings -- scanning it yields zero goals, which reads identically to a
    broken query. SurrealQL also requires ORDER BY fields to appear in the
    SELECT projection.
    """
    return _sql(
        "SELECT id, type, source, session_id, payload, timestamp FROM event_log "
        "WHERE type IN ['SECURITY_VIOLATION', 'SYSTEM_HEALTH', 'AGENT_COMPLETE'] "
        f"ORDER BY timestamp DESC LIMIT {int(limit)};",
        database=database,
    )


def measure_error_rate(source: str, database: str) -> float | None:
    """Fraction of a source's most recent events that look like failures.

    Scored with the ENGINE's catch-all predicate, not a local copy: the
    measurement must drive down the same quantity that opened the goal.

    Returns None when the source is unmeasurable (bad shape, or no rows) --
    None means UNKNOWN and stops execution; it is never coerced to 0.0.
    """
    if not _SAFE_SOURCE_RE.match(source):
        return None
    # ORDER BY is what makes the window "recent"; without it the LIMIT returns
    # whatever order the store happens to yield. SurrealQL requires the
    # ordering field to appear in the projection.
    rows = _sql(
        f"SELECT payload, timestamp FROM event_log WHERE source = '{source}' "
        f"ORDER BY timestamp DESC LIMIT {_ERROR_RATE_WINDOW};",
        database=database,
    )
    if not rows:
        return None
    return sum(1 for r in rows if payload_looks_like_failure(r.get("payload"))) / len(rows)


def measure_finding_open(finding: str, database: str) -> float | None:
    """1.0 while a finding is open, 0.0 once some event reports it fixed.

    Derived from the same event_log that raised the finding: a row carrying
    both this finding text and a `fixed_in` commit is the repo's own record
    that it was resolved. Rows are compared in Python rather than matched in
    SurrealQL, because finding text is free-form (quotes, colons) and
    interpolating it into a statement would be an injection seam.
    """
    if not finding:
        return None
    rows = _sql(
        f"SELECT payload FROM event_log WHERE payload.fixed_in != NONE LIMIT {_FIXED_SCAN_LIMIT};",
        database=database,
    )
    for row in rows:
        payload = row.get("payload") or {}
        if str(payload.get("finding") or "") == finding:
            return 0.0
    # A saturated page is UNKNOWN, not "open". event_log grows without bound, so
    # once fixed_in-bearing rows exceed the page size a resolved finding's fix
    # record can fall outside it -- and reporting that as 1.0 would pin a closed
    # goal open forever, re-introducing the already-fixed defect through the
    # measurement path instead of the synthesis path.
    if len(rows) >= _FIXED_SCAN_LIMIT:
        return None
    return 1.0


def _finding_of(trace: dict[str, Any]) -> str:
    payload = trace.get("payload") or {}
    return str(payload.get("finding") or payload.get("title") or "")


# metric name -> callable(trace, database) -> measured value or None.
# A metric absent from this table has no measurement source, so its goals are
# synthesized but NOT executed -- the runner never invents a reading.
MEASUREMENTS = {
    "error_rate": lambda trace, db: measure_error_rate(str(trace.get("source") or ""), db),
    "finding_open": lambda trace, db: measure_finding_open(_finding_of(trace), db),
}


def _make_step_fn(metric: str, trace: dict[str, Any], database: str):
    """Bind a real measurement into the loop's (iteration, state) -> step contract."""

    def step_fn(iteration: int, state: Any) -> tuple[Any, float, str]:
        value = MEASUREMENTS[metric](trace, database)
        if value is None:
            raise RuntimeError(f"measurement for {metric} returned UNKNOWN; refusing to fabricate")
        source = trace.get("source")
        return (
            {"source": source, "measured": value},
            float(value),
            f"measured {metric}={value:.4f} over last {_ERROR_RATE_WINDOW} events of {source}",
        )

    return step_fn


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="how many recent traces to scan")
    parser.add_argument(
        "--database",
        default="vault",
        help="SurrealDB database to read traces from: vault (session-published "
        "findings via the event bridge, the actionable stream) or main "
        "(git-post-commit lifecycle telemetry)",
    )
    parser.add_argument(
        "--execute", action="store_true", help="execute + persist loops (default: dry-run)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print synthesized goals, write nothing (default)"
    )
    args = parser.parse_args()

    try:
        traces = fetch_recent_traces(args.limit, database=args.database)
    except Exception as exc:
        print(f"FAIL: could not read event_log: {exc}")
        return 1

    print(
        f"Scanned {len(traces)} recent actionable-type traces from event_log "
        f"(ns=cohezion db={args.database})"
    )

    # Pair each goal with the trace that produced it: the measurement needs the
    # trace's source, which the GoalSpecification does not carry.
    pairs: list[tuple[GoalSpecification, dict[str, Any]]] = []
    seen_titles: set[str] = set()
    for trace in traces:
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace([trace])
        if goal is None or goal.title in seen_titles:
            continue
        seen_titles.add(goal.title)
        pairs.append((goal, trace))

    if not pairs:
        print("No actionable signals found — no goals synthesized.")
        return 0

    executable = [(g, t) for g, t in pairs if g.target_metric in MEASUREMENTS]
    unmeasurable = [(g, t) for g, t in pairs if g.target_metric not in MEASUREMENTS]

    print(f"Synthesized {len(pairs)} goals ({len(executable)} executable):")
    for goal, _ in pairs:
        op = "<=" if goal.direction == "at_most" else ">="
        mark = "loop" if goal.target_metric in MEASUREMENTS else "no measurement source"
        print(f"  - [{goal.target_metric} {op} {goal.target_threshold}] {goal.title}  ({mark})")

    if unmeasurable:
        print(
            f"\n{len(unmeasurable)} goal(s) have no measurement source in this runner and will "
            "be recorded without an executed loop. Add an entry to MEASUREMENTS to close them."
        )

    if not args.execute:
        print("\n(dry-run: no writes. Re-run with --execute to persist.)")
        return 0

    persistence = DurableSurrealGoalPersistence(database=args.database)
    pipeline = TraceGoalRefactorPipeline(persistence=persistence)
    failures = 0

    for goal, trace in executable:
        try:
            # max_iterations=1: this invocation contributes exactly one
            # iteration; the loop closes across runs.
            _, result = pipeline.refactor(
                [trace],
                trace_ids=[str(trace.get("id"))],
                step_fn=_make_step_fn(goal.target_metric, trace, args.database),
                max_iterations=1,
            )
            if result is None:
                continue
            verdict = "CONVERGED" if result.converged else "open"
            print(
                f"  {verdict}: {goal.title} — {goal.target_metric}={result.final_metric:.4f} "
                f"({result.iterations_run} iteration, {result.total_time_ms} ms)"
            )
        except Exception as exc:
            failures += 1
            print(f"  FAIL executing {goal.goal_id}: {exc}")

    for goal, trace in unmeasurable:
        try:
            persistence.persist_goal(goal, origin_trace_ids=[str(trace.get("id"))])
            print(f"  recorded (no loop): {goal.title}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL persisting {goal.goal_id}: {exc}")

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
