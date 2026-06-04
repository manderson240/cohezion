#!/usr/bin/env python3
"""Storage layer for autoresearch — SurrealDB (structured + graph) + Obsidian vault (notes).

Replaces stray JSONL as the *canonical* store. Per the research-defaults pattern, every
experiment becomes BOTH a SurrealDB record (queryable) AND an Obsidian note (human-readable),
and is wired into the datamesh graph via RELATE edges.

Design constraints:
- Pure stdlib (urllib). The runner is the bare `python3` interpreter, NOT the venv, so we
  must NOT import the `cohezion` package (coding-standards L367 — ModuleNotFoundError).
  We talk to SurrealDB over its HTTP /sql endpoint, exactly like the other tooling does.
- Datamesh graph: we write to the existing edge tables (`references` for lineage, `OPTIMIZES`
  for the objective) — using the architecture's graph is the deliverable, not importing its
  Python objects. (`derived_from`/`led_to`/`informed_by` are type-locked to journey tables.)
- Headless-safe: Obsidian via direct .md writes (NOT the interactive-auth MCP, which is
  absent in headless/cron runs). SurrealDB-down is a logged warning + JSONL buffer fallback,
  never a silent failure (CLAUDE.md: sentinel-is-a-bug).
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


log = logging.getLogger("autoresearch_store")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="  [store] %(levelname)s: %(message)s")

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "main"
SURREAL_USER, SURREAL_PASS = "root", "root"
SURREAL_TIMEOUT = 5

TABLE = "experiment_runs"
OBJECTIVE_NODE = "concept:skill_context_density"  # OPTIMIZES target node

VAULT_EXPERIMENTS = Path.home() / "vaults" / "cohezion-vault" / "experiments"
JSONL_BUFFER = Path(__file__).parent / "autoresearch.jsonl"  # OFFLINE BUFFER ONLY


# ─── SurrealDB HTTP ─────────────────────────────────────────────────────────────
def _surreal(sql: str) -> list:
    """POST a SurrealQL statement to the HTTP /sql endpoint. Raises on transport error."""
    token = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
    req = urllib.request.Request(SURREAL_URL, data=sql.encode(), method="POST")  # noqa: S310 - fixed localhost URL
    req.add_header("surreal-ns", SURREAL_NS)
    req.add_header("surreal-db", SURREAL_DB)
    req.add_header("Content-Type", "text/plain")
    req.add_header("Accept", "application/json")
    req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=SURREAL_TIMEOUT) as resp:  # noqa: S310 - fixed localhost URL
        return json.loads(resp.read().decode())


def surreal_available() -> bool:
    try:
        _surreal("RETURN 1;")
        return True
    except Exception as exc:
        log.warning("SurrealDB unavailable (%s) — falling back to JSONL buffer", exc)
        return False


_schema_ensured = False


def _ensure_schema() -> None:
    """Ensure experiment_runs accepts arbitrary fields (it ships SCHEMAFULL/empty → unusable).

    Idempotent: DEFINE TABLE OVERWRITE only redefines the schema, never drops rows. Runs once
    per process. Matches the SCHEMALESS convention of the `learnings`/`fleet_research` tables.
    """
    global _schema_ensured
    if _schema_ensured:
        return
    _surreal(
        f"DEFINE TABLE OVERWRITE {TABLE} TYPE ANY SCHEMALESS PERMISSIONS NONE;"
        # Index the fields the SessionStart digest hook filters/sorts on (record-id lookups
        # and ->edge-> traversals are already auto-indexed; these cover winner/ts scans).
        f"DEFINE INDEX OVERWRITE er_winner ON {TABLE} FIELDS winner;"
        f"DEFINE INDEX OVERWRITE er_ts ON {TABLE} FIELDS ts;"
    )
    _schema_ensured = True


_ID_ALLOWED = re.compile(r"^[A-Za-z0-9_.:-]+$")  # matches the EXPERIMENTS-key convention


def _rid(experiment_id: str) -> str:
    """Deterministic record id so re-runs UPSERT in place (preserves dedup).

    Validates the id at this single chokepoint (all SQL call sites flow through here) so a
    stray backtick can never close the quoted identifier and inject SurrealQL.
    """
    if not _ID_ALLOWED.match(experiment_id):
        raise ValueError(f"unsafe experiment_id for record id: {experiment_id!r}")
    return f"{TABLE}:`{experiment_id}`"


def already_logged_winner(experiment_id: str) -> bool:
    """True if this experiment is already recorded as a winner (SurrealDB-first, jsonl fallback)."""
    try:
        res = _surreal(f"SELECT winner FROM {_rid(experiment_id)};")
        rows = res[0].get("result") or []
        return bool(rows) and bool(rows[0].get("winner"))
    except Exception as exc:
        log.warning("winner-check query failed (%s) — checking JSONL buffer", exc)
        if JSONL_BUFFER.exists():
            for line in JSONL_BUFFER.read_text().splitlines():
                if not line.strip():
                    continue
                e = json.loads(line)
                if e.get("experiment_id") == experiment_id and e.get("winner"):
                    return True
        return False


# ─── Obsidian note ──────────────────────────────────────────────────────────────
def _write_vault_note(entry: dict) -> Path:
    VAULT_EXPERIMENTS.mkdir(parents=True, exist_ok=True)
    exp_id = entry["experiment_id"]
    date = entry["ts"][:10]
    metrics = entry.get("metrics", {})
    path = VAULT_EXPERIMENTS / f"{date}-autoresearch-{exp_id}.md"
    metric_lines = "\n".join(f"- **{k}**: {v}" for k, v in metrics.items())
    body = f"""---
type: experiment
experiment_id: {exp_id}
surreal_id: {TABLE}:{exp_id}
winner: {str(entry.get("winner", False)).lower()}
tokens_saved: {metrics.get("tokens_saved_new", 0)}
date: {date}
tags: [autoresearch, skill-density]
---
# {exp_id}

{entry.get("notes", "")}

## Metrics
{metric_lines}

## Lineage
[[skill-context-density]] · [[Autoresearch]]
"""
    path.write_text(body)
    return path


# ─── Public API ─────────────────────────────────────────────────────────────────
def log_result(
    experiment_id: str,
    config: dict,
    metrics: dict,
    winner: bool,
    notes: str,
    *,
    derived_from: str | None = None,
) -> None:
    """Persist one experiment result to SurrealDB + vault + graph. Idempotent (UPSERT by id).

    The `derived_from` PARAMETER names the prior run's experiment_id; the lineage is recorded
    via the `references` graph edge (the param name intentionally differs from the edge table).
    Falls back to the local JSONL buffer (with a logged warning) when SurrealDB is down.
    """
    if config.get("dry_run"):
        return
    if already_logged_winner(experiment_id):
        return

    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "experiment_id": experiment_id,
        "config": config,
        "metrics": metrics,
        "winner": winner,
        "notes": notes,
    }

    # 1) Canonical structured record (UPSERT by deterministic id).
    surreal_ok = False
    try:
        _ensure_schema()
        res = _surreal(f"UPSERT {_rid(experiment_id)} CONTENT {json.dumps(entry)};")
        if res and res[0].get("status") == "OK":
            surreal_ok = True
        else:
            log.warning("SurrealDB UPSERT returned non-OK: %s", res)
    except Exception as exc:
        log.warning("SurrealDB record write failed (%s) — buffering to JSONL", exc)

    # 2) Datamesh graph edges — idempotent (DELETE prior same-type edge, then RELATE), in a
    #    SEPARATE try so an edge failure is reported honestly and never masquerades as buffering
    #    (the canonical record is already saved at this point).
    if surreal_ok:
        try:
            rid = _rid(experiment_id)
            _surreal(f"UPSERT {OBJECTIVE_NODE} SET kind = 'objective';")
            _surreal(f"DELETE OPTIMIZES WHERE in = {rid} AND out = {OBJECTIVE_NODE};")
            _surreal(
                f"RELATE {rid}->OPTIMIZES->{OBJECTIVE_NODE} SET winner = {str(winner).lower()};"
            )
            if derived_from:
                # `references` is the ANY-typed lineage edge (derived_from/led_to/informed_by
                # are type-locked to journey/universe tables). Chains the loop's experiments.
                tgt = _rid(derived_from)
                _surreal(
                    f"DELETE references WHERE in = {rid} AND out = {tgt} AND kind = 'lineage';"
                )
                _surreal(f"RELATE {rid}->references->{tgt} SET kind = 'lineage', at = time::now();")
        except Exception as exc:
            log.warning("SurrealDB graph-edge write failed (%s) — record saved, edge dropped", exc)

    # 3) Human-readable Obsidian note (always, headless-safe direct write).
    try:
        note = _write_vault_note(entry)
        log.info("vault note → %s", note.name)
    except Exception as exc:
        log.warning("vault note write failed (%s)", exc)

    # 4) Offline buffer ONLY when SurrealDB unavailable (syncs next run).
    if not surreal_ok:
        with open(JSONL_BUFFER, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log.warning("buffered %s to local JSONL (SurrealDB was unavailable)", experiment_id)

    dest = "SurrealDB+vault" if surreal_ok else "vault+JSONL-buffer"
    print(
        f"  Logged: {experiment_id} | winner={winner} "
        f"| saved={metrics.get('tokens_saved_new', 0):,}t → {dest}"
    )


def sync_buffer() -> int:
    """Flush any buffered JSONL rows into SurrealDB once it is reachable. Returns count synced."""
    if not JSONL_BUFFER.exists() or not surreal_available():
        return 0
    rows = [json.loads(l) for l in JSONL_BUFFER.read_text().splitlines() if l.strip()]
    synced = 0
    _ensure_schema()
    for e in rows:
        try:
            _surreal(f"UPSERT {_rid(e['experiment_id'])} CONTENT {json.dumps(e)};")
            _write_vault_note(e)
            synced += 1
        except Exception as exc:
            log.warning("sync of %s failed (%s)", e.get("experiment_id"), exc)
    if synced == len(rows):
        JSONL_BUFFER.unlink()  # buffer drained; canonical store now holds everything
        log.info("buffer fully synced (%d rows) and removed", synced)
    return synced
