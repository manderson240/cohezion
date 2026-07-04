"""Tests for KanbanBridge — V-model invariants KB1–KB5.

KB1: structural — persist_item / backfill_items importable, return correct types
KB2: SurrealDB write — correct HTTP call shape (url, method, headers, body)
KB3: Obsidian write — file created at correct path with YAML frontmatter
KB4: fail-open — SurrealDB down doesn't prevent Obsidian write (and vice versa)
KB5: backfill_items — counts successes across a batch; idempotent (UPSERT, not INSERT)

Discriminating invariant: break the SurrealDB write → obsidian_ok still True
(proves the two sinks are independent and not short-circuited).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.data_mesh.kanban_bridge import (
    _obsidian_write,
    _surreal_write,
    backfill_items,
    persist_item,
)

# ── shared fixture ─────────────────────────────────────────────────────────────


@pytest.fixture
def sample_item() -> dict:
    return {
        "id": "abc123def456",
        "title": "Research AutoMem",
        "description": "AutoMem integration for SkillRefiner",
        "url": "https://arxiv.org/abs/2607.01224",
        "status": "approved",
        "relevance": "APPLY",
        "domain": "compound-loop",
        "notes": "Priority integration",
        "feedback": "",
        "created_at": "2026-07-01T00:00:00Z",
        "approved_at": "2026-07-01T12:00:00Z",
        "priority": 2,
        "type": "research",
    }


# ── KB1: structural ────────────────────────────────────────────────────────────


def test_kb1_persist_item_returns_dict_with_two_keys(sample_item, tmp_path):
    with (
        patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path),
        patch("cohezion.data_mesh.kanban_bridge._surreal_write", return_value=True),
    ):
        result = persist_item(sample_item)
    assert isinstance(result, dict)
    assert set(result.keys()) == {"surreal", "obsidian"}
    assert isinstance(result["surreal"], bool)
    assert isinstance(result["obsidian"], bool)


def test_kb1_backfill_items_returns_counts(tmp_path):
    items = [{"id": f"item{i:02d}", "title": f"T{i}"} for i in range(3)]
    with (
        patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path),
        patch("cohezion.data_mesh.kanban_bridge._surreal_write", return_value=True),
    ):
        counts = backfill_items(items)
    assert counts["total"] == 3
    assert "surreal_ok" in counts
    assert "obsidian_ok" in counts


# ── KB2: SurrealDB write ───────────────────────────────────────────────────────


def test_kb2_surreal_write_sends_upsert(sample_item):
    """_surreal_write must send an UPSERT with the item id and JSON content."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    calls: list[urllib.request.Request] = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = _surreal_write(sample_item)

    assert result is True
    assert len(calls) == 1
    req = calls[0]
    # Must be POST to SurrealDB SQL endpoint
    assert req.get_method() == "POST"
    assert "8001/sql" in req.full_url
    # Body must contain UPSERT and the item id
    body = req.data.decode()
    assert "UPSERT" in body
    assert sample_item["id"] in body
    # Headers must have namespace and db
    assert req.get_header("Surreal-ns") == "cohezion"
    assert req.get_header("Surreal-db") == "main"
    # Content must be the item as JSON
    parsed = json.loads(body.split("CONTENT", 1)[1].rstrip(";"))
    assert parsed["title"] == sample_item["title"]
    assert parsed["status"] == sample_item["status"]


def test_kb2_surreal_write_returns_false_on_network_error(sample_item):
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        result = _surreal_write(sample_item)
    assert result is False


def test_kb2_surreal_write_skips_item_without_id():
    result = _surreal_write({"title": "no id here"})
    assert result is False


def test_kb2_surreal_write_backtick_quotes_hyphenated_id():
    """IDs with hyphens (e.g. slugs) must be backtick-quoted in the UPSERT body."""
    item = {"id": "automem-2607-01224", "title": "AutoMem", "status": "pending_review"}
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    calls: list[urllib.request.Request] = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = _surreal_write(item)

    assert result is True
    body = calls[0].data.decode()  # type: ignore[union-attr]
    # ID with hyphens must be backtick-quoted so SurrealDB parses it correctly
    assert "`automem-2607-01224`" in body


# ── KB3: Obsidian write ────────────────────────────────────────────────────────


def test_kb3_obsidian_write_creates_file(sample_item, tmp_path):
    """_obsidian_write must create <id>.md in the kanban dir."""
    with patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path):
        result = _obsidian_write(sample_item)

    assert result is True
    note = tmp_path / f"{sample_item['id']}.md"
    assert note.exists(), "note file must exist"


def test_kb3_obsidian_write_has_yaml_frontmatter(sample_item, tmp_path):
    """Note must start with --- and contain mandatory YAML fields."""
    with patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path):
        _obsidian_write(sample_item)
    content = (tmp_path / f"{sample_item['id']}.md").read_text()
    assert content.startswith("---"), "must open with YAML frontmatter"
    assert "type: kanban" in content
    assert f"id: {sample_item['id']}" in content
    assert f"status: {sample_item['status']}" in content


def test_kb3_obsidian_write_contains_title(sample_item, tmp_path):
    with patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path):
        _obsidian_write(sample_item)
    content = (tmp_path / f"{sample_item['id']}.md").read_text()
    assert sample_item["title"] in content


def test_kb3_obsidian_write_creates_parent_dir(sample_item, tmp_path):
    """kanban/ subdir must be created even if it doesn't exist."""
    nested = tmp_path / "nested" / "kanban"
    with patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", nested):
        result = _obsidian_write(sample_item)
    assert result is True
    assert nested.exists()


# ── KB4: fail-open (discriminating) ───────────────────────────────────────────


def test_kb4_surreal_failure_does_not_prevent_obsidian_write(sample_item, tmp_path):
    """Breaking SurrealDB must not stop the Obsidian write.

    This is the discriminating test: if the two writes were short-circuited
    (e.g. `if not surreal_ok: return`), obsidian_ok would be False here.
    """
    with (
        patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path),
        patch("cohezion.data_mesh.kanban_bridge._surreal_write", return_value=False),
    ):
        result = persist_item(sample_item)

    # SurrealDB failed, but Obsidian must have succeeded
    assert result["surreal"] is False
    assert result["obsidian"] is True
    assert (tmp_path / f"{sample_item['id']}.md").exists()


def test_kb4_obsidian_failure_does_not_prevent_surreal_write(sample_item, tmp_path):
    """Breaking Obsidian must not stop the SurrealDB write."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    with (
        patch("urllib.request.urlopen", return_value=mock_resp),
        patch("cohezion.data_mesh.kanban_bridge._obsidian_write", return_value=False),
    ):
        result = persist_item(sample_item)

    assert result["obsidian"] is False
    assert result["surreal"] is True


# ── KB5: backfill idempotency ─────────────────────────────────────────────────


def test_kb5_backfill_twice_does_not_duplicate_obsidian_notes(tmp_path):
    """Running backfill twice on the same items must not corrupt Obsidian notes
    (UPSERT is idempotent for SurrealDB; file write just overwrites)."""
    items = [
        {"id": "aaaa111111", "title": "Item A", "status": "approved"},
        {"id": "bbbb222222", "title": "Item B", "status": "pending_review"},
    ]
    with (
        patch("cohezion.data_mesh.kanban_bridge._VAULT_KANBAN_DIR", tmp_path),
        patch("cohezion.data_mesh.kanban_bridge._surreal_write", return_value=True),
    ):
        first = backfill_items(items)
        second = backfill_items(items)

    assert first["total"] == 2
    assert second["total"] == 2
    # Exactly 2 files, not 4
    md_files = list(tmp_path.glob("*.md"))
    assert len(md_files) == 2
