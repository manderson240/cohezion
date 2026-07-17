#!/usr/bin/env python3
"""Bounded graph-edge ingest over vault markdown (pathway Move 2 driver).

For each of the N most recent vault decision/report/model-research docs:
UPSERT its vault_memory doc node, then GraphifyService extracts entities +
relations (local resident model via FleetRoster) and persists them into the
existing edge tables. Verify gate: edges non-empty + sampled precision audit
BEFORE any retrieval depends on them.

Run: uv run python scripts/drivers/graphify_vault.py --limit 15
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import urllib.request
from pathlib import Path

from cohezion.api.services.graphify import GraphifyService


VAULT = Path.home() / "vaults" / "cohezion-vault"
DIRS = ("decisions", "reports", "model-research")


def _slug(p: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", p.stem.lower()).strip("_")[:60]


def _sql(stmt: str) -> list:
    req = urllib.request.Request(
        "http://localhost:8001/sql",  # noqa: S310
        data=stmt.encode(),
        headers={
            "surreal-ns": "cohezion", "surreal-db": "main",
            "Content-Type": "text/plain", "Accept": "application/json",
            "Authorization": "Basic cm9vdDpyb290",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return json.load(r)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()

    docs = sorted(
        (p for d in DIRS for p in (VAULT / d).glob("*.md")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[: args.limit]

    svc = GraphifyService()
    total_edges = 0
    for p in docs:
        doc_id = _slug(p)
        _sql(
            f"UPSERT vault_memory:⟨{doc_id}⟩ SET title = {json.dumps(p.stem)}, "
            f"path = {json.dumps(str(p))}, indexed_by = 'graphify_vault';"
        )
        result = await svc.extract_graph(p.read_text(errors="replace"), doc_id)
        ok = await svc.ingest_to_vault(result)
        total_edges += len(result.relations)
        print(f"{doc_id}: {len(result.entities)} entities, {len(result.relations)} relations, {ok} stmts ok")

    counts = _sql(
        "SELECT count() FROM mentions GROUP ALL; SELECT count() FROM informed_by GROUP ALL; "
        "SELECT count() FROM relates_to GROUP ALL; SELECT count() FROM kg_entity GROUP ALL;"
    )
    labels = ("mentions", "informed_by", "relates_to", "kg_entity")
    for label, r in zip(labels, counts):
        res = r.get("result")
        n = res[0].get("count", 0) if isinstance(res, list) and res else 0
        print(f"table {label}: {n}")
    print(f"docs={len(docs)} relation_edges={total_edges}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
