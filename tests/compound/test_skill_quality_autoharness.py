"""Autoharness: verify SkillQualityScorer handles all 225 PRIME skills safely."""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.compound.skill_quality_scorer import SkillQualityScorer

SKILLS_DIR = Path(__file__).parents[2] / "src" / "cohezion" / "skills"


def test_all_skills_parse_without_error() -> None:
    """Every .md must parse without raising (parser safety)."""
    scorer = SkillQualityScorer()
    for skill_path in sorted(SKILLS_DIR.glob("*.md")):
        report = scorer.evaluate(skill_path)
        assert 0.0 <= report.overall_score <= 1.0
        assert all(0.0 <= d.score <= 1.0 for d in report.dimensions)


def test_all_skill_scores_have_required_dimensions() -> None:
    """Each report carries all 5 weighted dimensions."""
    scorer = SkillQualityScorer()
    for skill_path in SKILLS_DIR.glob("*.md"):
        report = scorer.evaluate(skill_path)
        names = {d.name for d in report.dimensions}
        for key in (
            "hiho_coherence",
            "structural",
            "testability",
            "version_currency",
            "usage_health",
        ):
            assert key in names


@pytest.mark.integration
def test_stable_ratio_at_least_twenty_percent() -> None:
    """Per P2c acceptance: >=20% skills HIHO-stable after patching."""
    scorer = SkillQualityScorer()
    total, stable = 0, 0
    for skill_path in SKILLS_DIR.glob("*.md"):
        total += 1
        report = scorer.evaluate(skill_path)
        if report.hiho_stable:
            stable += 1
    assert total > 0
    ratio = stable / total
    assert ratio >= 0.20, f"{stable}/{total} = {ratio:.2%}; need 20%+"
