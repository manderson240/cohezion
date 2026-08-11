#!/usr/bin/env python3
"""Graph-layer audit: are declared relation tables actually POPULATED?

WHY (2026-07-25): the knowledge graph holds ~54 edges across 1,146 documents. Eight of nine
DECLARED relation tables are empty, and `journey_knowledge` — the bridge between 278,741 execution
rows and 1,146 knowledge docs — has ZERO rows. None of the ~30 existing CI gates could notice this,
because they all check code, not data cardinality. The tables sat empty for months.

This is deliberately the same INSTRUMENT CLASS as `systemd_unit_audit.py`: an existence/cardinality
check over declarations. Harness asks "does this ExecStart resolve?"; graph asks "does this declared
edge type have any edges?" Both are O(1), deterministic, no LLM. The insight (Fable, 2026-07-25) is
that harness and graph share an instrument class, while loop-layer failures need causal instruments.

A DECLARED-BUT-EMPTY relation table is the graph-layer form of the recurring disease: a declaration
with no live referent.

Report-only by default so it can land without failing CI on the current (known-empty) state; use
--fail-on-empty once tables are populated or retired, to prevent RE-emptying.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

SURREAL = "http://localhost:8001/sql"
NS, DB = "cohezion", "main"

# Tables whose emptiness is a FINDING, with why they matter.
EXPECTED_POPULATED = {
    "vault_document": "curated research notes — the corpus itself",
    "journey_point": "agent execution trajectories",
    "journey_knowledge": "THE BRIDGE between execution and knowledge (0 rows = substrates unconnected)",
    "concept": "extracted concepts over OUR corpus",
    "mentions": "document -> entity edges",
    "relates_to": "concept -> concept edges",
}


def sql(q: str) -> list:
    out = subprocess.run(  # noqa: S603
        ["curl", "-s", "--max-time", "20", SURREAL,
         "-H", f"surreal-ns: {NS}", "-H", f"surreal-db: {DB}",
         "-H", "Content-Type: text/plain", "-u", "root:root", "--data", q],
        capture_output=True, text=True, check=False,
    ).stdout
    try:
        return json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return []


def count(table: str) -> int | None:
    """None = could not determine (do NOT report unknown as empty — that was today's whole lesson)."""
    r = sql(f"SELECT count() FROM {table} GROUP ALL;")
    if not r or not isinstance(r, list) or not r[0].get("result"):
        return 0 if r and r[0].get("status") == "OK" else None
    try:
        return int(r[0]["result"][0]["count"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def relation_tables() -> list[str]:
    r = sql("INFO FOR DB;")
    try:
        tables = r[0]["result"]["tables"]
    except (KeyError, IndexError, TypeError):
        return []
    return [k for k, v in tables.items() if "TYPE RELATION" in str(v)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail-on-empty", action="store_true",
                    help="exit 1 when a declared relation table is empty (use once populated)")
    a = ap.parse_args()

    rels = relation_tables()
    if not rels and count("vault_document") is None:
        print("SurrealDB unreachable — skipping (UNKNOWN is not a finding)")
        return 0

    print(f"graph cardinality audit — ns={NS} db={DB}")

    empty_rels: list[str] = []
    print(f"\n  declared relation tables ({len(rels)}):")
    for t in sorted(rels):
        n = count(t)
        mark = "?" if n is None else ("✗" if n == 0 else "✓")
        print(f"    {mark} {t:24} {'unknown' if n is None else n:>8}")
        if n == 0:
            empty_rels.append(t)

    print("\n  expected-populated tables:")
    starved: list[str] = []
    for t, why in EXPECTED_POPULATED.items():
        n = count(t)
        mark = "?" if n is None else ("✗" if n == 0 else "✓")
        print(f"    {mark} {t:24} {'unknown' if n is None else n:>8}  {why}")
        if n == 0:
            starved.append(t)

    # The ratio is the real signal: nodes without edges is a graph in name only.
    docs, edges = count("vault_document") or 0, 0
    for t in rels + ["mentions", "relates_to"]:
        edges += count(t) or 0
    if docs:
        print(f"\n  edges per document: {edges}/{docs} = {edges / docs:.3f}")
        if edges / docs < 0.5:
            print("    ⚠️  a graph in name only — retrieval's graph-ancestry half has nothing to traverse")

    if empty_rels:
        print(f"\n  {len(empty_rels)} DECLARED-BUT-EMPTY relation table(s): {', '.join(empty_rels)}")
        print("    Each is a declaration with no live referent — populate it or retire the declaration.")

    return 1 if (empty_rels and a.fail_on_empty) else 0


if __name__ == "__main__":
    sys.exit(main())
