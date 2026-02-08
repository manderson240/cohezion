"""Tests for compound engineering operations."""

import pytest

from mcp_server.compound_ops import CompoundOps
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
