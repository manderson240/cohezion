"""SurrealDB v3.3.0 Declarative Migration Runner.

Applies tri-temporal schemas, HNSW vector indexes, and composite performance
indexes using SurrealDB 3.3.0 and official surreal skills.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SurrealDBMigrator")

SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
SURREAL_USER = os.environ.get("SURREAL_USER", "root")
SURREAL_PASS = os.environ.get("SURREAL_PASS", "root")


def execute_surql(surql: str) -> list[dict[str, Any]]:
    """Execute raw SurrealQL statements against SurrealDB endpoint."""
    auth_bytes = f"{SURREAL_USER}:{SURREAL_PASS}".encode("ascii")
    auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

    req = urllib.request.Request(  # noqa: S310
        SURREAL_URL,
        data=surql.encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth_b64}",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Accept": "application/json",
            "Content-Type": "text/plain",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:  # noqa: S310
            if resp.status != 200:
                raise RuntimeError(f"SurrealDB HTTP {resp.status}: {resp.read().decode('utf-8')}")
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_msg = exc.read().decode("utf-8")
        logger.error(f"SurrealDB HTTP Error {exc.code}: {err_msg}")
        raise RuntimeError(f"SurrealDB query failed ({exc.code}): {err_msg}") from exc


def run_migration(migration_file: Path | None = None) -> bool:
    """Run SurrealDB v3.3.0 migration and verify database state."""
    if migration_file is None:
        migration_file = (
            Path(__file__).resolve().parents[3]
            / "scripts"
            / "dba"
            / "migrations"
            / "2026-10-15-v3_3_refactor.surql"
        )

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    logger.info(f"Applying migration: {migration_file.name}")
    surql_content = migration_file.read_text(encoding="utf-8")

    t0 = time.perf_counter()
    results = execute_surql(surql_content)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    errors = [r for r in results if r.get("status") != "OK"]
    if errors:
        logger.error(f"Migration encountered {len(errors)} error(s):")
        for err in errors:
            logger.error(f"  {err}")
        return False

    logger.info(
        f"Migration applied successfully in {elapsed_ms:.1f}ms ({len(results)} statement blocks executed)."
    )

    # Verification Step
    logger.info("Running post-migration verification checks...")
    verification_queries = """
    INFO FOR TABLE learning;
    INFO FOR TABLE kanban_item;
    INFO FOR TABLE experiment_run;
    INFO FOR TABLE automerge_log;
    INFO FOR TABLE vault_neuron;
    INFO FOR TABLE gaia_kaggle_daemon;
    INFO FOR TABLE submission_record;
    """
    verify_results = execute_surql(verification_queries)

    tables = [
        "learning",
        "kanban_item",
        "experiment_run",
        "automerge_log",
        "vault_neuron",
        "gaia_kaggle_daemon",
        "submission_record",
    ]
    all_ok = True
    for i, tbl in enumerate(tables):
        res = verify_results[i].get("result", {})
        fields = res.get("fields", {})
        indexes = res.get("indexes", {})
        logger.info(f"  Table '{tbl}': {len(fields)} fields, {len(indexes)} indexes defined.")
        if len(fields) == 0 or len(indexes) == 0:
            logger.warning(f"  WARNING: Table '{tbl}' has 0 fields or 0 indexes!")
            all_ok = False

    # Verify HNSW KNN Vector Query on learning
    logger.info("Testing HNSW KNN vector query on 'learning' table...")
    test_vec_query = """
    SELECT id, title, vector::distance::knn() AS dist
    FROM learning
    WHERE vector_12d <|1, 40|> [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
    """
    knn_res = execute_surql(test_vec_query)
    if knn_res and knn_res[0].get("status") == "OK":
        knn_hits = knn_res[0].get("result", [])
        logger.info(
            f"  HNSW 12D KNN search successful! Found nearest hit: {knn_hits[0].get('id') if knn_hits else 'None'}"
        )
    else:
        logger.warning(f"  HNSW 12D KNN search warning: {knn_res}")

    return all_ok


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
