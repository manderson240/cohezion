"""Unit tests for MemoryStore — JSONL-backed observation log.

Tests run against a tmp-dir JSONL file; no vault path required.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from mcp_server.memory_store import MemoryStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(jsonl_path=tmp_path / "observations.jsonl")


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


def test_save_returns_auto_incremented_id(tmp_path):
    store = make_store(tmp_path)
    id1 = store.save(text="first observation", title="First")
    id2 = store.save(text="second observation", title="Second")
    assert id1 == 1
    assert id2 == 2


def test_save_creates_jsonl_file(tmp_path):
    store = make_store(tmp_path)
    store.save(text="hello world")
    assert store._path.exists()
    lines = store._path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["text"] == "hello world"
    assert entry["id"] == 1


def test_save_validates_type(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError, match="type"):
        store.save(text="bad type", type="invalid_type")


def test_save_all_valid_types(tmp_path):
    store = make_store(tmp_path)
    for t in ("bugfix", "feature", "refactor", "discovery", "decision", "change"):
        store.save(text=f"obs for {t}", type=t)
    assert store._path.read_text().count("\n") == 6


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_returns_matching_entries(tmp_path):
    store = make_store(tmp_path)
    store.save(text="asyncio event loop fix", title="Loop Fix")
    store.save(text="ruff lint improvements", title="Linting")
    results = store.search("asyncio")
    assert len(results) == 1
    assert results[0]["title"] == "Loop Fix"


def test_search_matches_title(tmp_path):
    store = make_store(tmp_path)
    store.save(text="some content", title="Critical Bug")
    results = store.search("Critical")
    assert len(results) == 1


def test_search_case_insensitive(tmp_path):
    store = make_store(tmp_path)
    store.save(text="SurrealDB connection fix")
    results = store.search("surrealdb")
    assert len(results) == 1


def test_search_returns_snippet_not_full_text(tmp_path):
    store = make_store(tmp_path)
    long_text = "x" * 500
    store.save(text=long_text)
    results = store.search("xxx")
    assert len(results[0]["snippet"]) <= 200


def test_search_empty_store(tmp_path):
    store = make_store(tmp_path)
    assert store.search("anything") == []


def test_search_filter_by_type(tmp_path):
    store = make_store(tmp_path)
    store.save(text="bug fix observation", type="bugfix")
    store.save(text="new feature observation", type="feature")
    results = store.search("observation", type="bugfix")
    assert len(results) == 1
    assert results[0]["type"] == "bugfix"


def test_search_filter_by_project(tmp_path):
    store = make_store(tmp_path)
    store.save(text="cohezion work", project="cohezion")
    store.save(text="other work", project="other-project")
    results = store.search("work", project="cohezion")
    assert len(results) == 1


def test_search_limit(tmp_path):
    store = make_store(tmp_path)
    for i in range(10):
        store.save(text=f"observation number {i}")
    results = store.search("observation", limit=3)
    assert len(results) == 3


def test_search_date_filter(tmp_path):
    store = make_store(tmp_path)
    store.save(text="old observation")
    # Manually patch the timestamp of the first entry to be old
    lines = store._path.read_text().splitlines()
    old_entry = json.loads(lines[0])
    old_entry["timestamp"] = "2020-01-01T00:00:00Z"
    store._path.write_text(json.dumps(old_entry) + "\n")

    store.save(text="new observation")
    results = store.search("observation", dateStart="2024-01-01T00:00:00Z")
    assert len(results) == 1
    assert results[0]["id"] == 2


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_get_returns_full_entries(tmp_path):
    store = make_store(tmp_path)
    id1 = store.save(text="full text here", title="Entry One")
    entries = store.get([id1])
    assert len(entries) == 1
    assert entries[0]["text"] == "full text here"
    assert entries[0]["title"] == "Entry One"


def test_get_missing_ids_returns_empty(tmp_path):
    store = make_store(tmp_path)
    entries = store.get([999, 1000])
    assert entries == []


def test_get_mixed_ids(tmp_path):
    store = make_store(tmp_path)
    id1 = store.save(text="first")
    store.save(text="second")
    entries = store.get([id1, 999])
    assert len(entries) == 1
    assert entries[0]["id"] == id1


# ---------------------------------------------------------------------------
# timeline
# ---------------------------------------------------------------------------


def test_timeline_by_anchor(tmp_path):
    store = make_store(tmp_path)
    for i in range(10):
        store.save(text=f"entry {i}")
    # anchor=5, depth=2 before, 2 after → ids 3,4,5,6,7
    results = store.timeline(anchor=5, depth_before=2, depth_after=2)
    ids = [r["id"] for r in results]
    assert 5 in ids
    assert len(results) == 5


def test_timeline_by_query(tmp_path):
    store = make_store(tmp_path)
    for i in range(5):
        store.save(text=f"entry {i}")
    store.save(text="target observation for timeline")
    # query finds the last entry, returns context around it
    results = store.timeline(query="target", depth_before=2, depth_after=2)
    assert any("target" in r["text"] for r in results)


def test_timeline_requires_anchor_or_query(tmp_path):
    store = make_store(tmp_path)
    store.save(text="entry")
    with pytest.raises(ValueError, match="anchor.*query"):
        store.timeline()


def test_timeline_at_edge(tmp_path):
    store = make_store(tmp_path)
    for i in range(3):
        store.save(text=f"entry {i}")
    # anchor=1, depth_before=5 → just return what's available
    results = store.timeline(anchor=1, depth_before=5, depth_after=2)
    assert results[0]["id"] == 1


# ---------------------------------------------------------------------------
# Corruption handling
# ---------------------------------------------------------------------------


def test_repair_skips_malformed_lines(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    valid = json.dumps({"id": 1, "text": "ok", "title": "", "timestamp": "2026-01-01T00:00:00Z",
                        "type": "discovery", "project": "cohezion", "tags": []})
    jsonl_path.write_text(valid + "\n{INVALID JSON}\n")

    store = MemoryStore(jsonl_path=jsonl_path)
    results = store.search("ok")
    assert len(results) == 1


def test_repair_rewrites_valid_only(tmp_path):
    jsonl_path = tmp_path / "observations.jsonl"
    valid = json.dumps({"id": 1, "text": "good", "title": "", "timestamp": "2026-01-01T00:00:00Z",
                        "type": "discovery", "project": "cohezion", "tags": []})
    jsonl_path.write_text(valid + "\nbad line\n")

    store = MemoryStore(jsonl_path=jsonl_path)
    store.repair()
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["text"] == "good"


# ---------------------------------------------------------------------------
# FIFO eviction
# ---------------------------------------------------------------------------


def test_fifo_eviction_at_max_entries(tmp_path):
    store = MemoryStore(jsonl_path=tmp_path / "observations.jsonl", max_entries=3)
    store.save(text="entry 1")
    store.save(text="entry 2")
    store.save(text="entry 3")
    store.save(text="entry 4")  # should evict entry 1
    results = store.search("entry")
    ids = [r["id"] for r in results]
    assert 1 not in ids
    assert 4 in ids
    assert len(ids) == 3
