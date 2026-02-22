"""Tests for the vault publisher module."""

import json
import pytest
from datetime import date
from pathlib import Path
from research.pipeline import Finding


@pytest.fixture
def scored_findings():
    """Scored findings ready for publishing."""
    return [
        Finding(
            title="Building Compound AI Systems with Knowledge Graphs",
            url="https://example.com/compound-ai",
            source="web_search",
            snippet="A guide to compound AI architecture using knowledge graph memory.",
            category="compound_engineering",
            raw_score=8.5,
        ),
        Finding(
            title="KV Cache Optimization for LLMs",
            url="https://example.com/kv-cache",
            source="arxiv",
            snippet="Novel approach to KV cache compression reducing token usage by 40%.",
            category="token_efficiency",
            raw_score=7.2,
        ),
        Finding(
            title="New MCP Server Framework for Agents",
            url="https://example.com/mcp-framework",
            source="hackernews",
            snippet="A reusable framework for building MCP servers with tool orchestration.",
            category="app_creation",
            raw_score=6.8,
        ),
    ]


@pytest.fixture
def skill_results(scored_findings):
    """Skill detection results paired with findings."""
    return [
        {"finding": scored_findings[0], "skill_candidate": False, "skill_type": None},
        {"finding": scored_findings[1], "skill_candidate": False, "skill_type": None},
        {"finding": scored_findings[2], "skill_candidate": True, "skill_type": "framework"},
    ]


@pytest.fixture
def publish_config(tmp_path):
    """Config with a temp vault path."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "daily").mkdir()
    return {
        "publishing": {
            "max_inbox_notes": 40,
            "vault_path": str(tmp_path),
        },
    }


# --- Inbox notes ---


def test_create_inbox_note_has_frontmatter(scored_findings, skill_results, publish_config):
    """Inbox notes have valid YAML frontmatter."""
    from research.publisher import create_inbox_notes

    notes = create_inbox_notes(scored_findings, skill_results, publish_config)
    assert len(notes) >= 1
    # Check first note has frontmatter markers
    content = notes[0]["content"]
    assert content.startswith("---\n")
    assert "title:" in content
    assert "tags:" in content


def test_create_inbox_note_tags_are_arrays(scored_findings, skill_results, publish_config):
    """Tags in frontmatter are YAML arrays, not strings."""
    from research.publisher import create_inbox_notes

    notes = create_inbox_notes(scored_findings, skill_results, publish_config)
    content = notes[0]["content"]
    # Tags should be in array format [research, ...]
    assert "tags: [" in content


def test_create_inbox_note_filenames_are_slugified(scored_findings, skill_results, publish_config):
    """Inbox note filenames are date-prefixed and slugified."""
    from research.publisher import create_inbox_notes

    notes = create_inbox_notes(scored_findings, skill_results, publish_config)
    filename = notes[0]["filename"]
    assert filename.startswith("research-")
    assert filename.endswith(".md")
    # No spaces or special chars
    assert " " not in filename


def test_inbox_notes_limited_by_config(scored_findings, skill_results, publish_config):
    """Number of inbox notes respects max_inbox_notes config."""
    publish_config["publishing"]["max_inbox_notes"] = 1
    from research.publisher import create_inbox_notes

    notes = create_inbox_notes(scored_findings, skill_results, publish_config)
    assert len(notes) <= 1


# --- Daily digest ---


def test_create_digest_has_summary_stats(scored_findings, skill_results, publish_config):
    """Digest note includes summary statistics."""
    from research.publisher import create_digest

    metadata = {"total_findings": 200, "keyword_positive": 80, "top_n_selected": 3}
    digest = create_digest(scored_findings, skill_results, metadata, publish_config)

    assert "Raw findings:" in digest["content"]
    assert "After scoring:" in digest["content"]


def test_create_digest_has_focus_area_sections(scored_findings, skill_results, publish_config):
    """Digest note has per-focus-area sections."""
    from research.publisher import create_digest

    metadata = {"total_findings": 200, "keyword_positive": 80, "top_n_selected": 3}
    digest = create_digest(scored_findings, skill_results, metadata, publish_config)

    assert "Compound Engineering" in digest["content"] or "compound_engineering" in digest["content"].lower()


def test_create_digest_has_skill_candidates_table(scored_findings, skill_results, publish_config):
    """Digest includes skill candidates section when present."""
    from research.publisher import create_digest

    metadata = {"total_findings": 200, "keyword_positive": 80, "top_n_selected": 3}
    digest = create_digest(scored_findings, skill_results, metadata, publish_config)

    assert "Skill Candidates" in digest["content"]


# --- Deduplication ---


def test_dedup_prevents_duplicate_urls(scored_findings, skill_results, publish_config, tmp_path):
    """Dedup index prevents creating notes for already-seen URLs."""
    from research.publisher import create_inbox_notes, load_seen_urls, save_seen_urls

    seen_file = tmp_path / "seen_urls.json"

    # First run - no duplicates
    notes1 = create_inbox_notes(scored_findings, skill_results, publish_config)
    save_seen_urls(seen_file, {n["url"]: n["filename"] for n in notes1})

    # Second run with same findings
    seen = load_seen_urls(seen_file)
    notes2 = create_inbox_notes(scored_findings, skill_results, publish_config, seen_urls=seen)
    assert len(notes2) == 0  # All URLs already seen


# --- Full publish ---


def test_publish_writes_files_to_vault(scored_findings, skill_results, publish_config, tmp_path):
    """Publish writes inbox notes and digest to vault directories."""
    from research.publisher import publish

    metadata = {"total_findings": 200, "keyword_positive": 80, "top_n_selected": 3}
    result = publish(scored_findings, skill_results, metadata, publish_config)

    inbox_dir = tmp_path / "inbox"
    daily_dir = tmp_path / "daily"

    assert result["inbox_notes_created"] >= 1
    assert result["digest_created"] is True
    assert len(list(inbox_dir.glob("*.md"))) >= 1
    assert len(list(daily_dir.glob("*.md"))) == 1
