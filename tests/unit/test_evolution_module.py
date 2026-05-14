"""Tests for the Autogenesis-based evolution module."""

from unittest.mock import MagicMock

from cohezion.evolution.skill_optimizer import (
    SkillOptimizer,
    _parse_prime_sections,
    _rebuild_prime,
)
from cohezion.evolution.variable import Variable, from_prime_section


# ── Variable ───────────────────────────────────────────────────────────────────


def test_variable_gradient_accumulation():
    v = Variable(name="x", value="initial", require_grad=True)
    v.add_gradient("too vague")
    v.add_gradient("missing edge cases")
    assert len(v.gradients) == 2
    assert "too vague" in v.get_gradient_text()


def test_variable_deduplicates_gradients():
    v = Variable(name="x", value="val", require_grad=True)
    v.add_gradient("same feedback")
    v.add_gradient("same feedback")
    assert len(v.gradients) == 1


def test_variable_reset_gradients():
    v = Variable(name="x", value="v", require_grad=True)
    v.add_gradient("some feedback")
    v.reset_gradients()
    assert v.gradients == []


def test_variable_history_records_updates():
    v = Variable(name="x", value="old", require_grad=True)
    v.record_update("old", "new", "improved clarity")
    assert len(v.history) == 1
    assert v.history[0]["new"] == "new"


def test_from_prime_section():
    v = from_prime_section("Instructions", "## Instructions\ndo X", require_grad=True)
    assert v.require_grad is True
    assert v.name == "Instructions"


# ── _parse_prime_sections / _rebuild_prime ─────────────────────────────────────

SAMPLE_PRIME = """\
---
title: Test Skill
version: 1.0.3
---

## Instructions
Step 1: do this.
Step 2: do that.

## Examples
Input: foo → Output: bar
"""


def test_parse_frontmatter():
    sections = _parse_prime_sections(SAMPLE_PRIME)
    assert "frontmatter" in sections
    assert "version: 1.0.3" in sections["frontmatter"]


def test_parse_sections():
    sections = _parse_prime_sections(SAMPLE_PRIME)
    assert "Instructions" in sections
    assert "Step 1" in sections["Instructions"]


def test_rebuild_roundtrip():
    sections = _parse_prime_sections(SAMPLE_PRIME)
    rebuilt = _rebuild_prime(sections)
    # Key content preserved
    assert "version: 1.0.3" in rebuilt
    assert "Step 1: do this." in rebuilt


def test_rebuild_with_modified_section():
    sections = _parse_prime_sections(SAMPLE_PRIME)
    sections["Instructions"] = "## Instructions\nImproved step."
    rebuilt = _rebuild_prime(sections)
    assert "Improved step." in rebuilt
    assert "Step 1: do this." not in rebuilt


# ── SkillOptimizer._bump_version_in_frontmatter ────────────────────────────────


def test_bump_version():
    content = "---\nversion: 1.0.3\n---\n## Instructions\nfoo"
    bumped = SkillOptimizer._bump_version_in_frontmatter(content)
    assert "version: 1.0.4" in bumped


def test_bump_version_no_frontmatter():
    content = "## Instructions\nfoo"
    result = SkillOptimizer._bump_version_in_frontmatter(content)
    assert result == content  # unchanged


# ── SkillOptimizer.optimize_prime ─────────────────────────────────────────────


def test_optimize_prime_skips_low_confidence(tmp_path):
    prime_file = tmp_path / "test.md"
    prime_file.write_text(SAMPLE_PRIME)
    opt = SkillOptimizer(confidence_threshold=0.7)
    result = opt.optimize_prime(prime_file, feedback=["bad"], task="improve", confidence=0.5)
    assert result is None


def test_optimize_prime_missing_file(tmp_path):
    opt = SkillOptimizer()
    result = opt.optimize_prime(
        tmp_path / "nonexistent.md", feedback=["x"], task="y", confidence=0.9
    )
    assert result is None


def test_optimize_prime_no_trainable_section(tmp_path):
    prime_file = tmp_path / "test.md"
    prime_file.write_text("---\nversion: 1.0.0\n---\n## Context\nsome text\n")
    opt = SkillOptimizer()
    # No Instructions/Procedure/Rules/Guidelines/Steps section
    result = opt.optimize_prime(prime_file, feedback=["x"], task="y", confidence=0.9)
    assert result is None


def test_optimize_prime_uses_optimizer_and_rewrites(tmp_path):
    """When optimizer returns satisfied=True, file is rewritten with improved content."""
    from cohezion.evolution.reflection_optimizer import OptimizationResult

    prime_file = tmp_path / "test.md"
    prime_file.write_text(SAMPLE_PRIME)

    improved_result = OptimizationResult(
        variable_name="Instructions",
        old_value="## Instructions\nStep 1: do this.\nStep 2: do that.",
        new_value="## Instructions\nStep 1: do this (improved).\nStep 2: clarified.",
        reasoning="Added specificity",
        satisfied=True,
        step=1,
    )

    opt = SkillOptimizer()
    mock_opt = MagicMock()
    opt._optimizer = mock_opt
    if True:  # context manager replaced
        mock_opt.optimize.return_value = [improved_result]
        result = opt.optimize_prime(
            prime_file, feedback=["too vague"], task="improve", confidence=0.8
        )

    assert result is not None
    new_content = prime_file.read_text()
    assert "improved" in new_content
    # Version was bumped
    assert "version: 1.0.4" in new_content


def test_optimize_prime_no_satisfied_result_returns_none(tmp_path):
    from cohezion.evolution.reflection_optimizer import OptimizationResult

    prime_file = tmp_path / "test.md"
    prime_file.write_text(SAMPLE_PRIME)

    unsatisfied = OptimizationResult(
        variable_name="Instructions",
        old_value="old",
        new_value="new",
        reasoning="not enough",
        satisfied=False,
        step=1,
    )
    opt = SkillOptimizer()
    mock_opt = MagicMock()
    opt._optimizer = mock_opt
    if True:  # context manager replaced
        mock_opt.optimize.return_value = [unsatisfied]
        result = opt.optimize_prime(prime_file, feedback=["x"], task="y", confidence=0.9)

    assert result is None
