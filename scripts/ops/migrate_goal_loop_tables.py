#!/usr/bin/env python3
"""Migrate the per-session `<domain>_goal` / `<domain>_loop` tables (+ `autonomous_loop`
and the `serves` edge) into the ONE goal/loop graph: canonical `goal` + `loop` nodes
with `domain` as data, and typed edges in `goal_graph`.

Integrate-first (non-destructive-wiring.md): old tables are read, NEVER dropped or
altered. Idempotent: node and edge ids are deterministic, so re-running adds 0 rows.

    python scripts/ops/migrate_goal_loop_tables.py --dry-run                      # default
    python scripts/ops/migrate_goal_loop_tables.py --execute --target-db tgl_test  # scratch
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


sys.path.insert(0, "src")

from cohezion.flume.goal_graph import apply_plan, discover_domains, plan_migration
from cohezion.flume.loop_goal_refactor_engine import DurableSurrealGoalPersistence
from cohezion.flume.trace_goal_sources import sql


def _read_factory(source_db: str):
    def read(table: str) -> list[dict[str, Any]]:
        try:
            return sql(f"SELECT * FROM {table};", source_db)
        except RuntimeError as exc:
            if "does not exist" in str(exc):
                return []
            raise

    return read


def _tables(source_db: str) -> list[str]:
    info = sql("INFO FOR DB;", source_db)
    return list(info[0]["tables"]) if info else []


def _target_counts(target_db: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for label in ("goal", "loop"):
        for r in sql(
            f"SELECT domain, count() AS n FROM {label} WHERE source_table != NONE GROUP BY domain;",
            target_db,
        ):
            out.setdefault(str(r["domain"]), {"goal": 0, "loop": 0})[label] = r["n"]
    edges = sql("SELECT kind, count() AS n FROM goal_graph GROUP BY kind;", target_db)
    out["_edges"] = {str(r["kind"]): r["n"] for r in edges}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-db", default="main", help="db holding the old per-domain tables")
    ap.add_argument("--target-db", default="main", help="db to write the canonical graph into")
    ap.add_argument("--execute", action="store_true", help="write (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = ap.parse_args()

    read = _read_factory(args.source_db)
    domains = discover_domains(lambda: _tables(args.source_db))
    plan = plan_migration(domains, read)
    counts = plan.counts()

    print(f"source db={args.source_db} target db={args.target_db}")
    print(f"{'domain':<18}{'goals':>7}{'loops':>7}")
    for d in sorted(counts):
        print(f"{d:<18}{counts[d]['goal']:>7}{counts[d]['loop']:>7}")
    n_edge: dict[str, int] = {}
    for kind, *_ in plan.edges:
        n_edge[kind] = n_edge.get(kind, 0) + 1
    print(f"TOTAL goals={len(plan.goals)} loops={len(plan.loops)} edges={n_edge}")
    if not args.execute:
        print("(dry-run: nothing written. Re-run with --execute.)")
        return 0

    persistence = DurableSurrealGoalPersistence(database=args.target_db, timeout=30.0)
    apply_plan(plan, persistence)
    got = _target_counts(args.target_db)
    bad = [
        d
        for d in counts
        if got.get(d, {}).get("goal") != counts[d]["goal"]
        or got.get(d, {}).get("loop") != counts[d]["loop"]
    ]
    print(f"written; target counts per domain: { {k: v for k, v in got.items() if k != '_edges'} }")
    print(f"target edges by kind: {got['_edges']}")
    if bad:
        print(f"FAIL: per-domain counts differ from source for {bad}")
        return 1
    print("OK: per-domain counts equal the old tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
