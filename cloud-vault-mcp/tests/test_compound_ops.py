"""Tests for compound engineering operations."""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.compound_ops import CompoundOps, relevance_score
from mcp_server.obsidian_ops import ObsidianOps
from mcp_server.vault_ops import VaultOps


@pytest.fixture
def compound(tmp_path):
    """Create a compound ops instance with a temporary vault."""
    for d in ["decisions", "patterns", "experiments", "projects", "concepts"]:
        (tmp_path / d).mkdir()

    # Add templates
    (tmp_path / "decisions" / "_template.md").write_text(
        "---\ndate: {{date}}\nproject: {{project}}\nstatus: accepted\n"
        "tags: [decision, {{project}}]\n---\n# {{title}}\n\n"
        "## Context\n{{context}}\n\n## Decision\n{{decision}}\n\n"
        "## Rationale\n{{rationale}}\n\n## Alternatives Considered\n{{alternatives}}\n"
    )
    (tmp_path / "experiments" / "_template.md").write_text(
        "---\ndate: {{date}}\nproject: {{project}}\n"
        "status: in-progress\noutcome: inconclusive\n"
        "tags: [experiment, {{project}}]\n---\n# {{title}}\n\n"
        "## Hypothesis\n{{hypothesis}}\n\n## Method\n{{method}}\n\n"
        "## Results\n{{result}}\n\n## Learnings\n{{learnings}}\n"
    )
    (tmp_path / "patterns" / "_template.md").write_text(
        "---\ndate: {{date}}\nsource_project: {{project}}\n"
        "tags: [pattern, {{domain}}]\n---\n# {{pattern_name}}\n\n"
        "## Problem\nWhat recurring problem does this solve?\n\n"
        "## Solution\n{{description}}\n\n## Example\n```\n{{code_example}}\n```\n"
    )

    # Seed some existing content for search tests
    (tmp_path / "decisions" / "use-reward-shaping.md").write_text(
        "---\ndate: 2025-01-10\nproject: rl-env\ntags: [decision, rl-env]\n---\n"
        "# Use Reward Shaping with Curriculum\n\n"
        "## Context\nAgent struggles with sparse rewards.\n\n"
        "## Decision\nImplement progressive reward shaping.\n"
    )
    (tmp_path / "patterns" / "curriculum-learning.md").write_text(
        "---\ndate: 2025-01-12\ntags: [pattern, rl]\n---\n"
        "# Curriculum Learning\n\nGradually increase task difficulty for RL agents.\n"
        "Reward shaping is part of the curriculum.\n"
    )

    vault = VaultOps(str(tmp_path))
    obsidian = ObsidianOps(vault)
    return CompoundOps(vault, obsidian)


class TestLogDecision:
    def test_creates_adr(self, compound):
        result = compound.log_decision(
            project="cohezion",
            title="Use FastMCP",
            context="Need an MCP server framework",
            decision="Use FastMCP from the mcp package",
            rationale="Official Python SDK, well-maintained",
            alternatives_considered="Build from scratch",
        )
        assert "Created" in result or "decision" in result.lower()

        # Verify file was created
        files = compound.vault.list_dir("decisions", recursive=True)
        matching = [f for f in files if "use-fastmcp" in f]
        assert len(matching) == 1

        content = compound.vault.read(matching[0])
        assert "FastMCP" in content
        assert "cohezion" in content


class TestLogExperiment:
    def test_creates_experiment(self, compound):
        result = compound.log_experiment(
            project="rl-env",
            hypothesis="PPO converges faster with shaped rewards",
            method="Train with and without reward shaping, compare convergence",
            result="PPO converged 2x faster with shaping",
            learnings="Shaped rewards need careful scaling",
        )
        assert "Created" in result or "experiment" in result.lower()


class TestExtractPattern:
    def test_creates_pattern(self, compound):
        result = compound.extract_pattern(
            source_path="projects/rl-env",
            pattern_name="Reward Normalization",
            description="Normalize rewards to unit variance for stable training",
            code_example="rewards = (rewards - mean) / (std + 1e-8)",
            domain="rl",
        )
        assert "Created" in result or "pattern" in result.lower()

        files = compound.vault.list_dir("patterns", recursive=True)
        matching = [f for f in files if "reward-normalization" in f]
        assert len(matching) == 1


class TestFindRelevantContext:
    def test_finds_decisions_and_patterns(self, compound):
        results = compound.find_relevant_context("reward shaping")
        assert len(results) > 0
        paths = [r["path"] for r in results]
        assert any("reward-shaping" in p for p in paths)
        assert any("curriculum" in p for p in paths)

    def test_project_scoping(self, compound):
        results = compound.find_relevant_context("reward", project="rl-env")
        assert len(results) > 0
        # All results should be related to rl-env
        for r in results:
            content = compound.vault.read(r["path"])
            assert "rl" in content.lower() or "reward" in content.lower()

    def test_no_results(self, compound):
        results = compound.find_relevant_context("quantum computing blockchain")
        assert len(results) == 0

    def test_results_include_relevance_score(self, compound):
        results = compound.find_relevant_context("reward shaping")
        for r in results:
            assert "relevance_score" in r
            assert r["relevance_score"] > 0


# ── relevance_score unit tests ────────────────────────────────────────────────


class TestRelevanceScore:
    def test_fresh_document_scores_higher(self):
        fresh = relevance_score(5, datetime.now(timezone.utc).isoformat(), 10)
        stale = relevance_score(
            5,
            (datetime.now(timezone.utc) - timedelta(days=180)).isoformat(),
            10,
        )
        assert fresh > stale

    def test_half_life_at_90_days(self):
        score_90d = relevance_score(
            1, (datetime.now(timezone.utc) - timedelta(days=90)).isoformat(), 0
        )
        score_fresh = relevance_score(1, datetime.now(timezone.utc).isoformat(), 0)
        assert 0.45 < (score_90d / score_fresh) < 0.55

    def test_access_count_boost(self):
        high_access = relevance_score(5, datetime.now(timezone.utc).isoformat(), 100)
        low_access = relevance_score(5, datetime.now(timezone.utc).isoformat(), 1)
        assert high_access > low_access

    def test_unknown_age_gets_half_weight(self):
        unknown = relevance_score(5, "", 0)
        fresh = relevance_score(5, datetime.now(timezone.utc).isoformat(), 0)
        assert 0.45 < (unknown / fresh) < 0.55

    def test_zero_match_count(self):
        assert relevance_score(0, datetime.now(timezone.utc).isoformat(), 10) == 0.0

    def test_graceful_on_invalid_date(self):
        score = relevance_score(5, "not-a-date", 0)
        assert score > 0

    def test_zero_access_count_boost_floors_at_one(self):

        score = relevance_score(5, datetime.now(timezone.utc).isoformat(), 0)
        # log1p(0)=0 → boost clamped to 1.0, decay≈1.0 when fresh
        assert abs(score - 5 * 1.0 * 1.0) < 0.05

    def test_custom_half_life(self):
        score_30d = relevance_score(
            1,
            (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            0,
            half_life_days=30.0,
        )
        score_fresh = relevance_score(
            1, datetime.now(timezone.utc).isoformat(), 0, half_life_days=30.0
        )
        assert 0.45 < (score_30d / score_fresh) < 0.55


# ── find_relevant_context with mocked metadata ───────────────────────────────


@pytest.fixture
def compound_mocked():
    """CompoundOps with mocked vault and obsidian (no filesystem needed)."""
    vault = MagicMock()
    obsidian = MagicMock()
    vault.search.return_value = []
    return CompoundOps(vault=vault, obsidian=obsidian)


class TestFindRelevantContextDecay:
    def test_falls_back_gracefully_when_surreal_down(self, compound_mocked):
        compound_mocked.vault.search.return_value = [
            {"path": "decisions/foo.md", "snippet": "x"},
            {"path": "decisions/foo.md", "snippet": "y"},
            {"path": "patterns/bar.md", "snippet": "z"},
        ]

        with patch.object(compound_mocked, "_fetch_neuron_metadata_batch", return_value={}):
            with patch.object(compound_mocked, "_track_access"):
                results = compound_mocked.find_relevant_context("test")

        assert len(results) == 2
        # foo.md has 2 match hits per directory → higher match_count than bar.md
        assert results[0]["path"] == "decisions/foo.md"
        assert results[0]["match_count"] > results[1]["match_count"]

    def test_metadata_boosts_recently_accessed_doc(self, compound_mocked):
        compound_mocked.vault.search.return_value = [
            {"path": "decisions/new.md", "snippet": "hit"},
            {"path": "decisions/old.md", "snippet": "hit"},
        ]
        now = datetime.now(timezone.utc)
        metadata = {
            "decisions/new.md": {
                "path": "decisions/new.md",
                "last_accessed": now.isoformat(),
                "access_count": 50,
            },
            "decisions/old.md": {
                "path": "decisions/old.md",
                "last_accessed": (now - timedelta(days=200)).isoformat(),
                "access_count": 0,
            },
        }

        with patch.object(compound_mocked, "_fetch_neuron_metadata_batch", return_value=metadata):
            with patch.object(compound_mocked, "_track_access"):
                results = compound_mocked.find_relevant_context("test")

        assert results[0]["path"] == "decisions/new.md"

    def test_relevance_score_field_present(self, compound_mocked):
        compound_mocked.vault.search.return_value = [
            {"path": "patterns/foo.md", "snippet": "match"}
        ]

        with patch.object(compound_mocked, "_fetch_neuron_metadata_batch", return_value={}):
            with patch.object(compound_mocked, "_track_access"):
                results = compound_mocked.find_relevant_context("foo")

        assert "relevance_score" in results[0]
        assert results[0]["relevance_score"] > 0

    def test_empty_vault_returns_empty_list(self, compound_mocked):
        compound_mocked.vault.search.return_value = []

        with patch.object(compound_mocked, "_fetch_neuron_metadata_batch", return_value={}):
            with patch.object(compound_mocked, "_track_access"):
                results = compound_mocked.find_relevant_context("nothing")

        assert results == []

    def test_track_access_receives_top_result_paths(self, compound_mocked):
        compound_mocked.vault.search.return_value = [
            {"path": "decisions/a.md", "snippet": "hit"}
        ]

        with patch.object(compound_mocked, "_fetch_neuron_metadata_batch", return_value={}):
            with patch.object(compound_mocked, "_track_access") as mock_track:
                compound_mocked.find_relevant_context("test")

        mock_track.assert_called_once_with(["decisions/a.md"])


# ── _fetch_neuron_metadata_batch graceful degradation ────────────────────────


class TestFetchNeuronMetadataBatch:
    def test_returns_empty_on_connection_error(self, compound_mocked):
        with patch(
            "mcp_server.compound_ops.asyncio.run",
            side_effect=ConnectionRefusedError("SurrealDB down"),
        ):
            result = compound_mocked._fetch_neuron_metadata_batch(["decisions/foo.md"])
        assert result == {}

    def test_returns_empty_on_event_loop_conflict(self, compound_mocked):
        with patch(
            "mcp_server.compound_ops.asyncio.run",
            side_effect=RuntimeError("This event loop is already running"),
        ):
            result = compound_mocked._fetch_neuron_metadata_batch(["decisions/foo.md"])
        assert result == {}

    def test_empty_paths_skips_query(self, compound_mocked):
        # Should return immediately without touching asyncio
        with patch("mcp_server.compound_ops.asyncio.run") as mock_run:
            result = compound_mocked._fetch_neuron_metadata_batch([])
        assert result == {}
        mock_run.assert_not_called()
