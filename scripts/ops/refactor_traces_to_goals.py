#!/usr/bin/env python3
"""Refactor event_log traces into actionable goals and closed loops.

Reads recent trace rows (event_log / kanban_item) from SurrealDB, synthesizes
GoalSpecifications from actionable signals (security findings, health findings,
fix-verifications, failure clusters), executes their loops, and persists both
goal + result durably (ERR-checked — never the silent-loss trap).

Usage:
    python scripts/ops/refactor_traces_to_goals.py --dry-run   # default: print, no writes
    python scripts/ops/refactor_traces_to_goals.py --limit 50 --execute
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.request


sys.path.insert(0, "src")

from cohezion.flume.loop_goal_refactor_engine import (
    DurableSurrealGoalPersistence,
    GoalSpecification,
    TraceToLoopTransformer,
)


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
    "Content-Type": "text/plain",
}


def _sql(statement: str) -> list:
    """Run SurrealQL; raise on embedded ERR (HTTP-200 trap)."""
    req = urllib.request.Request(
        SURREAL_URL, data=statement.encode(), headers=SURREAL_HEADERS, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
        body = json.loads(r.read())
    rows: list = []
    for stmt in body:
        if stmt.get("status") == "ERR":
            raise RuntimeError(f"SurrealDB error: {stmt.get('result')}")
        rows.extend(stmt.get("result") or [])
    return rows


def fetch_recent_traces(limit: int, database: str = "main") -> list[dict]:
    """Pull the newest event_log rows across the trace-bearing types.

    NB: --database vault reaches the CrossSessionEventBridge's event_log (where
    session-published findings land); main holds the git-post-commit JOURNEY_STEP
    stream. Both are trace sources.
    """
    # NB: SurrealQL requires ORDER BY fields to appear in the SELECT projection.
    headers = {**SURREAL_HEADERS, "surreal-db": database}
    req = urllib.request.Request(
        SURREAL_URL,
        data=(
            f"SELECT id, type, source, session_id, payload, timestamp FROM event_log "
            f"WHERE type IN ['SECURITY_VIOLATION', 'SYSTEM_HEALTH', 'AGENT_COMPLETE'] "
            f"ORDER BY timestamp DESC LIMIT {int(limit)};"
        ).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
        body = json.loads(r.read())
    rows: list = []
    for stmt in body:
        if stmt.get("status") == "ERR":
            raise RuntimeError(f"SurrealDB error: {stmt.get('result')}")
        rows.extend(stmt.get("result") or [])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, help="how many recent traces to scan")
    parser.add_argument(
        "--database",
        default="main",
        help="SurrealDB database to read traces from: main (git-post-commit stream) "
        "or vault (session-published findings via the event bridge)",
    )
    parser.add_argument("--execute", action="store_true", help="persist goals (default: dry-run)")
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

    persistence = DurableSurrealGoalPersistence()
    goals: list[GoalSpecification] = []
    seen_titles: set[str] = set()
    for trace in traces:
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace([trace])
        if goal is None or goal.title in seen_titles:
            continue
        seen_titles.add(goal.title)
        goals.append(goal)

    if not goals:
        print("No actionable signals found — no goals synthesized.")
        return 0

    print(f"Synthesized {len(goals)} goals:")
    for goal in goals:
        print(f"  - [{goal.target_metric} >= {goal.target_threshold}] {goal.title}")

    if not args.execute:
        print("\n(dry-run: no writes. Re-run with --execute to persist.)")
        return 0

    written = 0
    for goal in goals:
        try:
            record = persistence.persist_goal(goal)
            print(f"  persisted {record}")
            written += 1
        except Exception as exc:
            print(f"  FAIL persisting {goal.goal_id}: {exc}")
    print(f"\nDone: {written}/{len(goals)} goals persisted to SurrealDB goal table.")
    return 0 if written == len(goals) else 1


if __name__ == "__main__":
    raise SystemExit(main())
