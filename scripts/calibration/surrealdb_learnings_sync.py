#!/usr/bin/env python3
"""SurrealDB Learnings Sync Script.

Synchronizes Learning 390, Learning 391, and the retrospective file
to SurrealDB on port 8001 (namespace cohezion, database vault, table neurons).
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request


# SurrealDB connection details
SURREALDB_URL = os.environ.get("SURREALDB_URL", "http://localhost:8001/sql")
SURREALDB_USER = os.environ.get("SURREALDB_USER", "root")
SURREALDB_PASS = os.environ.get("SURREALDB_PASS", "root")
NS = "cohezion"
DB = "vault"


def _sql_str(v: str) -> str:
    """Escape and wrap string for SQL."""
    return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"


def sync_learning(learning_id: str, title: str, path: str, tags: list[str], content: str) -> None:
    """Upsert a learning node (neuron) into SurrealDB.

    Parameters
    ----------
    learning_id : str
        The record ID suffix (e.g. 'L390')
    title : str
        Title of the learning
    path : str
        File path reference
    tags : list[str]
        List of tag strings
    content : str
        Full text content of the learning
    """
    db_id = f"neurons:{learning_id}"
    tags_json = json.dumps(tags)

    upsert_sql = (
        f"UPSERT {db_id} SET "
        f"title = {_sql_str(title)}, "
        f"path = {_sql_str(path)}, "
        f"tags = {tags_json}, "
        f"content = {_sql_str(content)}, "
        f"stage = 'active', "
        f"updated_at = time::now();"
    )

    print(f"Upserting {db_id} into SurrealDB ({NS}/{DB})...")
    try:
        auth = base64.b64encode(f"{SURREALDB_USER}:{SURREALDB_PASS}".encode()).decode()
        req = urllib.request.Request(  # noqa: S310
            SURREALDB_URL,
            data=upsert_sql.encode("utf-8"),
            method="POST",
            headers={
                "surreal-ns": NS,
                "surreal-db": DB,
                "Authorization": f"Basic {auth}",
                "Content-Type": "text/plain",
            },
        )
        response_bytes = urllib.request.urlopen(req, timeout=5).read()  # noqa: S310
        response_json = json.loads(response_bytes)

        if isinstance(response_json, list) and response_json:
            first = response_json[0]
            if isinstance(first, dict) and first.get("status") == "ERR":
                print(
                    f"❌ SurrealDB error for {db_id}: {first.get('result')}",
                    file=sys.stderr,
                )
                return
        print(f"✅ Successfully wrote {db_id} to SurrealDB.")
    except Exception as e:
        print(
            f"⚠️ SurrealDB write failed for {db_id}: {e}",
            file=sys.stderr,
        )


def main() -> None:
    # Learning 390
    sync_learning(
        learning_id="L390",
        title="AutoHarness Synthesis and Local Verifier Generation",
        path="/home/mike-anderson/vaults/cohezion-vault/learnings/L390-autoharness-synthesis-local-verifier.md",
        tags=["autoharness", "verifier", "synthesis", "local-model"],
        content=(
            "Implemented dynamic verifier synthesis via local model phi4 on Ollama. "
            "The synthesis engine automatically generates deterministic verification "
            "scripts (Code-as-action-verifier) based on action intent (e.g. creating files, "
            "making API calls). Caches verifiers in harness.py for zero-cost and zero-latency local run."
        ),
    )

    # Learning 391
    sync_learning(
        learning_id="L391",
        title="Semantic Rules Overlap Audit & Context Cache Optimization",
        path="/home/mike-anderson/vaults/cohezion-vault/learnings/L391-semantic-rules-overlap-audit.md",
        tags=["rules", "semantic-overlap", "embeddings", "optimization"],
        content=(
            "Developed an automated semantic overlap script using nomic-embed-text:v1.5 embeddings "
            "and cosine similarity to map and prune redundant rules between MEMORY.md, "
            "coding-standards.md, and CLAUDE.md. Yields a projected savings of ~3.2k tokens per agent turn "
            "(approx 45% prompt cache savings)."
        ),
    )

    # Retrospective
    sync_learning(
        learning_id="RETRO_2026_06_04",
        title="Retrospective: AutoHarness Foundation & Semantic Rules Audit Sprint",
        path="/home/mike-anderson/vaults/cohezion-vault/learnings/RETRO-2026-06-04-sprint-completion.md",
        tags=[
            "retrospective",
            "autoharness",
            "routing",
            "benchmarks",
            "prompt-cache",
            "semantic-overlap",
        ],
        content=(
            "Retrospective for the sprint completing AutoHarness verifier synthesis, "
            "real-world prompt routing benchmarks (100% success on 50 traces), HIHO gate code "
            "expansion by 20 domain-specific snippets, and rules redundancy semantic audit "
            "concerning coding-standards.md and MEMORY.md against CLAUDE.md."
        ),
    )


if __name__ == "__main__":
    main()
