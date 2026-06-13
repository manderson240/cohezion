"""Tests for SurrealMemoryGraph — the mem0 provenance graph.

Offline tests mock the HTTP transport (_sql) to assert the RELATE SQL shape
(deterministic edge id, provenance SET fields, edge-table read) and the
best-effort / graceful-degradation contract. A live round-trip test runs only when
SurrealDB :8001 is reachable (skips cleanly otherwise) — proving idempotency and
that an UPDATE preserves the superseded ``prior_memory`` the vector store would lose.

No mem0 dependency: the graph is stdlib-only, so this module collects without the
optional `memory` extra (unlike test_surreal_vector_store.py).
"""

from __future__ import annotations

import urllib.request
from unittest.mock import patch

import pytest

from cohezion.memory.surreal_graph import SurrealMemoryGraph


def test_link_sql_uses_deterministic_edge_id_and_provenance_fields():
    g = SurrealMemoryGraph()
    with patch.object(g, "_sql", return_value=[]) as m:
        ok = g.link("dev", "f1", memory="prefers worktrees", event="ADD")
    assert ok is True
    sql = m.call_args[0][0]
    # deterministic edge id is `<agent>__<fact>` so replay is idempotent
    assert "`mem_remembers`:`dev__f1`" in sql
    assert "`mem_agent`:`dev` ->" in sql and "-> `mem_fact`:`f1`" in sql
    assert 'event = "ADD"' in sql
    assert 'memory = "prefers worktrees"' in sql
    assert "prior_memory = NONE" in sql
    assert "updated_at = time::now()" in sql


def test_link_update_serializes_prior_memory():
    g = SurrealMemoryGraph()
    with patch.object(g, "_sql", return_value=[]) as m:
        g.link("dev", "f1", memory="new", event="UPDATE", prior_memory="old text")
    sql = m.call_args[0][0]
    assert 'event = "UPDATE"' in sql
    assert 'prior_memory = "old text"' in sql  # superseded text preserved on the edge


def test_record_facts_skips_idless_and_counts_written():
    g = SurrealMemoryGraph()
    facts = [
        {"id": "f1", "memory": "a", "event": "ADD"},
        {"memory": "no id — skipped", "event": "ADD"},
        {"id": "f2", "memory": "b", "event": "UPDATE", "previous_memory": "b0"},
    ]
    with patch.object(g, "_sql", return_value=[]):
        written = g.record_facts("dev", facts)
    assert written == 2  # the id-less entry is skipped


def test_facts_for_agent_reads_via_edge_table():
    g = SurrealMemoryGraph()
    fake = [{"result": [{"memory": "m", "event": "ADD", "prior_memory": None, "fact_id": "f1"}]}]
    with patch.object(g, "_sql", return_value=fake) as m:
        rows = g.facts_for_agent("dev", limit=10)
    sql = m.call_args[0][0]
    assert "FROM mem_remembers WHERE in = `mem_agent`:`dev`" in sql
    assert "LIMIT 10" in sql
    assert rows[0]["fact_id"] == "f1"


def test_link_degrades_to_false_on_backend_error():
    """A transport failure must return False, never raise."""
    g = SurrealMemoryGraph()
    with patch.object(g, "_sql", side_effect=RuntimeError("surreal down")):
        assert g.link("dev", "f1") is False


def test_facts_for_agent_degrades_to_empty_on_backend_error():
    g = SurrealMemoryGraph()
    with patch.object(g, "_sql", side_effect=RuntimeError("surreal down")):
        assert g.facts_for_agent("dev") == []


def test_record_facts_partial_failure_counts_only_successes():
    """If one edge write fails, record_facts still counts the successful ones."""
    g = SurrealMemoryGraph()
    with patch.object(g, "_sql", side_effect=[[], RuntimeError("boom")]):
        written = g.record_facts("dev", [{"id": "f1", "memory": "a"}, {"id": "f2", "memory": "b"}])
    assert written == 1


def _surreal_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8001/health", timeout=1)
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _surreal_up(), reason="SurrealDB :8001 not reachable")
def test_live_provenance_idempotent_and_preserves_prior_memory():
    """Live: ADD then UPDATE the same fact; edge dedups and keeps the superseded text."""
    g = SurrealMemoryGraph(
        agent_table="mem_agent_pytest",
        fact_table="mem_fact_pytest",
        edge_table="mem_remembers_pytest",
    )
    g.reset()
    try:
        assert g.link("dev", "f1", memory="prefers worktree commits", event="ADD")
        # Replay the SAME (agent, fact) as an UPDATE carrying the prior text.
        assert g.link(
            "dev",
            "f1",
            memory="prefers squashed worktree commits",
            event="UPDATE",
            prior_memory="prefers worktree commits",
        )
        rows = g.facts_for_agent("dev")
        # deterministic edge id => exactly one edge despite two RELATEs
        assert len(rows) == 1, f"expected 1 deduped edge, got {len(rows)}"
        row = rows[0]
        assert row["fact_id"] == "f1"
        assert row["event"] == "UPDATE"
        assert row["memory"] == "prefers squashed worktree commits"
        # the value-add: the superseded text survives (flat vector store would lose it)
        assert row["prior_memory"] == "prefers worktree commits"
    finally:
        g.reset()
