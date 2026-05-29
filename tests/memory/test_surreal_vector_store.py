"""Tests for the SurrealDB mem0 vector provider.

Offline tests mock the HTTP transport (_sql) to assert SurrealQL generation and the
mem0 OutputData contract. A live round-trip test runs only when SurrealDB :8001 is
reachable (skips cleanly otherwise) — proving real cosine ranking.
"""

from __future__ import annotations

import urllib.request
from unittest.mock import patch

import pytest


# surreal_vector_store imports mem0 at module scope (it subclasses VectorStoreBase),
# so this whole module needs the optional `memory` extra. CI installs only `--extra
# dev` yet runs tests/, so without this guard collection ImportErrors and reds CI.
# importorskip must precede the import to turn that hard error into a clean skip.
pytest.importorskip("mem0")

from cohezion.memory.surreal_vector_store import (
    OutputData,
    SurrealVectorStore,
    register_surreal_provider,
)


def _store(**kw):
    """Construct with _sql patched so __init__'s create_col makes no network call."""
    with patch.object(SurrealVectorStore, "_sql", return_value=[]):
        return SurrealVectorStore(collection_name="t", embedding_model_dims=3, **kw)


def test_record_uses_backtick_syntax():
    """Record refs must be `col`:`id` (handles UUID hyphens this SurrealDB rejects in type::thing)."""
    s = _store()
    assert s._record("a-b-c") == "`t`:`a-b-c`"


def test_search_sql_uses_cosine_and_filters():
    s = _store()
    with patch.object(s, "_sql", return_value=[{"result": []}]) as m:
        s.search("", [1.0, 0.0, 0.0], top_k=4, filters={"user_id": "dev"})
    sql = m.call_args[0][0]
    assert "vector::similarity::cosine(vec, [1.0, 0.0, 0.0])" in sql
    assert 'WHERE payload.user_id = "dev"' in sql
    assert "ORDER BY score DESC LIMIT 4" in sql


def test_insert_sql_creates_content():
    s = _store()
    with patch.object(s, "_sql", return_value=[]) as m:
        s.insert(vectors=[[1, 2, 3]], payloads=[{"memory": "x"}], ids=["id1"])
    sql = m.call_args[0][0]
    assert sql.startswith("CREATE `t`:`id1` CONTENT")
    assert '"memory": "x"' in sql and "[1, 2, 3]" in sql


def test_search_parses_output_data():
    s = _store()
    fake = [{"result": [{"id": "a1", "payload": {"memory": "m"}, "score": 0.9}]}]
    with patch.object(s, "_sql", return_value=fake):
        out = s.search("", [1, 0, 0], top_k=1)
    assert isinstance(out[0], OutputData)
    assert out[0].id == "a1" and out[0].score == 0.9 and out[0].payload["memory"] == "m"


def test_register_surreal_provider_hooks_all_three_points():
    import sys

    from mem0.utils.factory import VectorStoreFactory
    from mem0.vector_stores.configs import VectorStoreConfig

    register_surreal_provider()
    provider_map = VectorStoreConfig.__private_attributes__["_provider_configs"].default
    assert provider_map.get("surrealdb") == "SurrealDBConfig"
    assert "surrealdb" in VectorStoreFactory.provider_to_class
    assert "mem0.configs.vector_stores.surrealdb" in sys.modules


def test_registered_config_validates_in_mem0():
    """A surrealdb vector_store config must pass mem0's VectorStoreConfig validator."""
    from mem0.vector_stores.configs import VectorStoreConfig

    register_surreal_provider()
    cfg = VectorStoreConfig(
        provider="surrealdb",
        config={"collection_name": "c", "embedding_model_dims": 768},
    )
    assert cfg.provider == "surrealdb"


def _surreal_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8001/health", timeout=1)
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _surreal_up(), reason="SurrealDB :8001 not reachable")
def test_live_round_trip_cosine_ranking():
    """Live: insert 3 vectors, confirm SurrealDB cosine ranks the aligned one first."""
    s = SurrealVectorStore(collection_name="mem0_pytest_live", embedding_model_dims=3)
    s.reset()
    try:
        s.insert(
            vectors=[[1, 0, 0], [0, 1, 0], [0.9, 0.1, 0.0]],
            payloads=[
                {"user_id": "u", "memory": "x"},
                {"user_id": "u", "memory": "y"},
                {"user_id": "u", "memory": "nearx"},
            ],
            ids=["a", "b", "c"],
        )
        hits = s.search("", [1, 0, 0], top_k=3, filters={"user_id": "u"})
        assert [h.id for h in hits] == ["a", "c", "b"], "cosine ranking must be a > c > b"
        assert s.get("a").payload["memory"] == "x"
        assert s.search("", [1, 0, 0], filters={"user_id": "other"}) == []
    finally:
        s.delete_col()
