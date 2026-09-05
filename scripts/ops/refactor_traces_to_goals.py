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
            f"WHERE type IN ['SECURITY_VIOLATION', 'SYSTEM_HEALTH', 'AGENT_COMPLETE', 'JOURNEY_STEP'] "
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


def synthesize_from_database(
    limit: int, database: str, seen_titles: set[str]
) -> list[GoalSpecification]:
    """Scan one database's traces and return newly-synthesized goals.

    `seen_titles` is shared across callers (mutated in place) so a
    --both-databases run dedupes across BOTH databases, not just within one --
    main (git-post-commit stream) and vault (session-published findings) are
    genuinely different trace sources, but nothing prevents the same finding
    surfacing in both.
    """
    traces = fetch_recent_traces(limit, database=database)
    print(
        f"Scanned {len(traces)} recent actionable-type traces from event_log "
        f"(ns=cohezion db={database})"
    )
    goals: list[GoalSpecification] = []
    for trace in traces:
        goal = TraceToLoopTransformer.synthesize_goal_from_real_trace([trace])
        if goal is None or goal.title in seen_titles:
            continue
        seen_titles.add(goal.title)
        goals.append(goal)
    return goals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=30, help="how many recent traces to scan (per database)"
    )
    parser.add_argument(
        "--database",
        default="main",
        help="SurrealDB database to read traces from: main (git-post-commit stream) "
        "or vault (session-published findings via the event bridge). Ignored if "
        "--both-databases is set.",
    )
    parser.add_argument(
        "--both-databases",
        action="store_true",
        help="scan main AND vault in one run, deduped across both (equivalent to "
        "running --database main then --database vault and merging by title)",
    )
    parser.add_argument("--execute", action="store_true", help="persist goals (default: dry-run)")
    parser.add_argument(
        "--dry-run", action="store_true", help="print synthesized goals, write nothing (default)"
    )
    args = parser.parse_args()

    databases = ["main", "vault"] if args.both_databases else [args.database]

    seen_titles: set[str] = set()
    goals: list[GoalSpecification] = []
    for db in databases:
        try:
            goals.extend(synthesize_from_database(args.limit, db, seen_titles))
        except Exception as exc:
            print(f"FAIL: could not read event_log (db={db}): {exc}")
            return 1

    if not goals:
        print("No actionable signals found — no goals synthesized.")
        return 0

    print(f"Synthesized {len(goals)} goal(s) total:")
    for goal in goals:
        print(f"  - [{goal.target_metric} >= {goal.target_threshold}] {goal.title}")

    if not args.execute:
        print("\n(dry-run: no writes. Re-run with --execute to persist.)")
        return 0

    persistence = DurableSurrealGoalPersistence()
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
