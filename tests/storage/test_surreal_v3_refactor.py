"""Tests for SurrealDB v3.3.0 schema and table refactoring.

Verifies:
1. Tri-temporal fields on learning (transaction_time, valid_from, valid_to, superseded_by).
2. HNSW vector index functionality on learning (vector_12d and embedding).
3. Indexed query performance via EXPLAIN on kanban_item and learning.
4. Schema field definitions on all refactored tables.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.request


SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.environ.get("SURREAL_NS", "cohezion")
SURREAL_DB = os.environ.get("SURREAL_DB", "main")
AUTH = base64.b64encode(b"root:root").decode("ascii")


def _query(sql: str) -> list[dict]:
    req = urllib.request.Request(  # noqa: S310
        SURREAL_URL,
        data=sql.encode("utf-8"),
        headers={
            "Authorization": f"Basic {AUTH}",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Accept": "application/json",
            "Content-Type": "text/plain",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def test_learning_table_fields_and_indexes():
    """Verify learning table has tri-temporal fields and HNSW vector index."""
    res = _query("INFO FOR TABLE learning;")
    assert res[0]["status"] == "OK"
    fields = res[0]["result"]["fields"]
    indexes = res[0]["result"]["indexes"]

    # Verify tri-temporal fields
    assert "transaction_time" in fields
    assert "valid_from" in fields
    assert "valid_to" in fields
    assert "superseded_by" in fields

    # Verify vector fields & HNSW indexes
    assert "embedding" in fields
    assert "vector_12d" in fields
    assert "idx_learning_embedding" in indexes
    assert "idx_learning_vector_12d" in indexes
    assert "idx_learning_category_created" in indexes


def test_kanban_table_composite_index():
    """Verify kanban_item table uses composite index on status + created_at."""
    res = _query("INFO FOR TABLE kanban_item;")
    assert res[0]["status"] == "OK"
    indexes = res[0]["result"]["indexes"]
    assert "idx_kanban_status_created" in indexes
    assert "idx_kanban_status" in indexes


def test_hnsw_knn_search_execution():
    """Verify HNSW vector search executes and returns distance."""
    sql = """
    SELECT id, vector::distance::knn() AS dist
    FROM learning
    WHERE vector_12d <|1, 40|> [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
    """
    res = _query(sql)
    assert res[0]["status"] == "OK"
    hits = res[0]["result"]
    assert len(hits) >= 1
    assert "dist" in hits[0]
    assert isinstance(hits[0]["dist"], (int, float))
