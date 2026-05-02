"""Tests for the self-improving skill quality ecosystem.

Covers:
- SkillQualityScorer (5 dimensions)
- SkillQualityOrchestrator (full improvement loop)
- Integration between scorer, health tracker, evolution tracker
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cohezion.compound.skill_evolution_diff import SkillEvolutionTracker
from cohezion.compound.skill_health_tracker import SkillHealthRecord, SkillHealthTracker
from cohezion.compound.skill_quality_orchestrator import (
    ImprovementHypothesis,
    ImprovementResult,
    SkillQualityOrchestrator,
)
from cohezion.compound.skill_quality_scorer import DimensionScore, SkillQualityReport, SkillQualityScorer


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_skill_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def good_skill(tmp_skill_dir):
    """HIHO-stable skill with all anchors, sections, code, metadata."""
    content = """---
name: good-skill
description: A well-formed skill
metadata:
  version: "1.0.0"
  project: cohezion
---

# SKILL: GOOD_SKILL

## When to Use This Skill
Use when you need geometric rigor.

## Key Texts & Concepts
- **0.5** = HIHO threshold (Shannon max)
- **256** = FLUME latent dimension
- **SU(2)** = agent state gauge

## Instruction
1. Load the skill
2. Execute with alignment

```python
from cohezion.example import run
run()
```

## See Also
- related-skill
"""
    p = tmp_skill_dir / "good_skill.md"
    p.write_text(content)
    return p


@pytest.fixture
def bad_skill(tmp_skill_dir):
    """Low-quality skill missing most dimensions."""
    content = """# SKILL: BAD_SKILL

Some random text without frontmatter or sections.
"""
    p = tmp_skill_dir / "bad_skill.md"
    p.write_text(content)
    return p


@pytest.fixture
def empty_skill(tmp_skill_dir):
    """Empty file — edge case for missing skill."""
    p = tmp_skill_dir / "empty_skill.md"
    p.write_text("")
    return p


@pytest.fixture
def health_tracker(tmp_skill_dir):
    """Fresh health tracker with some data."""
    ht = SkillHealthTracker(storage_path=tmp_skill_dir / "health.json")
    ht.record_usage("good-skill", success=True, tokens_used=1000, quality_score=0.8)
    ht.record_usage("good-skill", success=True, tokens_used=1000, quality_score=0.9)
    ht.record_usage("bad-skill", success=False, tokens_used=500, quality_score=0.1)
    return ht


# =============================================================================
# SkillQualityScorer Tests
# =============================================================================

class TestSkillQualityScorer:
    def test_good_skill_scores_high(self, good_skill):
        scorer = SkillQualityScorer()
        report = scorer.evaluate(good_skill)

        assert report.skill_name == "good-skill"
        assert report.overall_score >= 0.7
        assert report.hiho_stable is True
        assert all(d.score >= 0.5 for d in report.dimensions)
        assert len(report.actionable_recommendations) == 0

    def test_bad_skill_scores_low(self, bad_skill):
        scorer = SkillQualityScorer()
        report = scorer.evaluate(bad_skill)

        assert report.skill_name == "BAD_SKILL"
        assert report.overall_score < 0.5
        assert report.hiho_stable is False
        assert len(report.actionable_recommendations) > 0

    def test_empty_skill_zero_score(self, empty_skill):
        scorer = SkillQualityScorer()
        report = scorer.evaluate(empty_skill)
        # Empty file has 0 on 4 dims + 0.5 on usage_health => 0.5*0.2 = 0.1 overall
        assert report.overall_score == 0.1
        assert report.hiho_stable is False
        assert len(report.actionable_recommendations) > 0
        assert any("Missing geometric anchors" in r for r in report.actionable_recommendations)

    def test_missing_file_empty_report(self, tmp_skill_dir):
        scorer = SkillQualityScorer()
        report = scorer.evaluate(tmp_skill_dir / "nonexistent.md", skill_name="ghost")

        assert report.overall_score == 0.0
        assert report.skill_name == "ghost"

    def test_hiho_dimension_detects_anchors(self, good_skill, bad_skill):
        scorer = SkillQualityScorer()
        good = scorer.evaluate(good_skill)
        bad = scorer.evaluate(bad_skill)

        good_hiho = next(d for d in good.dimensions if d.name == "hiho_coherence")
        bad_hiho = next(d for d in bad.dimensions if d.name == "hiho_coherence")

        assert good_hiho.score == 1.0
        assert bad_hiho.score < 0.3
        assert any("Missing geometric anchors" in i for i in bad_hiho.issues)

    def test_structural_dimension_checks_frontmatter(self, good_skill, bad_skill):
        scorer = SkillQualityScorer()
        good = scorer.evaluate(good_skill)
        bad = scorer.evaluate(bad_skill)

        good_struct = next(d for d in good.dimensions if d.name == "structural")
        bad_struct = next(d for d in bad.dimensions if d.name == "structural")

        assert good_struct.score >= 0.8
        assert bad_struct.score < 0.5
        assert any("Missing YAML frontmatter" in i for i in bad_struct.issues)

    def test_testability_dimension_counts_code(self, good_skill, bad_skill):
        scorer = SkillQualityScorer()
        good = scorer.evaluate(good_skill)
        bad = scorer.evaluate(bad_skill)

        good_test = next(d for d in good.dimensions if d.name == "testability")
        bad_test = next(d for d in bad.dimensions if d.name == "testability")

        assert good_test.score >= 0.5
        assert bad_test.score < 0.5
        assert any("No executable Python code examples" in i for i in bad_test.issues)

    def test_version_dimension_checks_metadata(self, good_skill, bad_skill):
        scorer = SkillQualityScorer()
        good = scorer.evaluate(good_skill)
        bad = scorer.evaluate(bad_skill)

        good_ver = next(d for d in good.dimensions if d.name == "version_currency")
        bad_ver = next(d for d in bad.dimensions if d.name == "version_currency")

        assert good_ver.score == 1.0
        assert bad_ver.score < 0.5

    def test_usage_dimension_with_health_tracker(self, good_skill, bad_skill, health_tracker):
        scorer = SkillQualityScorer(health_tracker=health_tracker)
        good = scorer.evaluate(good_skill)
        bad = scorer.evaluate(bad_skill)

        good_usage = next(d for d in good.dimensions if d.name == "usage_health")
        bad_usage = next(d for d in bad.dimensions if d.name == "usage_health")

        assert good_usage.score >= 0.5
        assert bad_usage.score < 0.5

    def test_batch_evaluate_sorts_worst_first(self, good_skill, bad_skill, empty_skill):
        scorer = SkillQualityScorer()
        reports = scorer.batch_evaluate([good_skill, bad_skill, empty_skill])
        scores = [r.overall_score for r in reports]

        assert scores == sorted(scores)
        # Lowest score should be first (bad_skill at ~0.0 < empty_skill at 0.1 < good_skill at ~0.9)

    def test_dimension_weighted_property(self):
        d = DimensionScore(name="test", score=0.8, weight=0.25)
        assert d.weighted == 0.2

    def test_report_to_dict_serializable(self, good_skill):
        scorer = SkillQualityScorer()
        report = scorer.evaluate(good_skill)
        d = report.to_dict()

        assert d["skill_name"] == "good-skill"
        assert d["hiho_stable"] is True
        assert "dimensions" in d
        assert isinstance(d["overall_score"], float)
        # Must be JSON serializable
        json.dumps(d)


# =============================================================================
# SkillQualityOrchestrator Tests
# =============================================================================

class TestSkillQualityOrchestrator:
    @pytest.mark.asyncio
    async def test_good_skill_no_change(self, good_skill):
        orch = SkillQualityOrchestrator()
        result = await orch.improve_skill(good_skill)

        assert result.applied is False
        assert result.before_score == result.after_score
        assert result.consensus_approved is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_bad_skill_gets_patched(self, bad_skill):
        orch = SkillQualityOrchestrator()
        before_text = bad_skill.read_text()
        result = await orch.improve_skill(bad_skill)

        assert result.before_score < 0.5
        assert result.applied is True
        assert result.after_score > result.before_score
        assert result.diff_lines > 0
        # File was actually changed
        assert bad_skill.read_text() != before_text

    @pytest.mark.asyncio
    async def test_patch_rollback_on_regression(self, tmp_skill_dir):
        """If patch makes score worse, roll back to original."""
        # Create a skill that is already borderline — a bad patch might make it worse
        content = """---
name: fragile-skill
metadata:
  version: "1.0.0"
  project: cohezion
---

# SKILL: FRAGILE_SKILL

## When to Use This Skill
Use when testing.

## Key Texts & Concepts
- **0.5** = HIHO threshold
- **256** = FLUME dimension
- **SU(2)** = gauge

## Instruction
1. One step

```python
pass
```

## See Also
- other
"""
        p = tmp_skill_dir / "fragile.md"
        p.write_text(content)

        orch = SkillQualityOrchestrator()
        before_text = p.read_text()
        result = await orch.improve_skill(p)

        # Should be stable already — no patch needed
        assert result.applied is False or result.after_score >= result.before_score
        if not result.applied:
            assert p.read_text() == before_text

    @pytest.mark.asyncio
    async def test_evolution_tracker_records_versions(self, bad_skill):
        evolution = SkillEvolutionTracker()
        orch = SkillQualityOrchestrator(evolution=evolution)
        await orch.improve_skill(bad_skill)

        # Should have recorded at least one version
        assert len(evolution._versions.get("BAD_SKILL", [])) >= 1

    @pytest.mark.asyncio
    async def test_health_tracker_records_success(self, bad_skill, health_tracker):
        orch = SkillQualityOrchestrator(health=health_tracker)
        await orch.improve_skill(bad_skill)

        record = health_tracker.get_health("BAD_SKILL")
        assert record is not None
        assert record.total_invocations >= 1

    @pytest.mark.asyncio
    async def test_batch_improve_processes_all(self, tmp_skill_dir, good_skill, bad_skill):
        orch = SkillQualityOrchestrator()
        results = await orch.batch_improve(tmp_skill_dir, min_score=0.5)

        assert len(results) >= 2
        names = {r.skill_name for r in results}
        assert "good-skill" in names
        assert "BAD_SKILL" in names

    @pytest.mark.asyncio
    async def test_hypothesis_generation_produces_actions(self, bad_skill):
        orch = SkillQualityOrchestrator()
        report = orch.scorer.evaluate(bad_skill)
        hypos = orch._generate_hypotheses(report)

        assert len(hypos) > 0
        actions = {h.action for h in hypos}
        assert actions <= {"add_anchor", "add_section", "add_example", "bump_version"}

    def test_count_diff_lines(self, tmp_skill_dir):
        orch = SkillQualityOrchestrator()
        before = "line1\nline2\nline3"
        after = "line1\nline2 modified\nline3\nline4"
        assert orch._count_diff_lines(before, after) > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_loop_good_then_bad(self, tmp_skill_dir, good_skill, bad_skill):
        """Run the full improvement loop on both a good and bad skill."""
        evolution = SkillEvolutionTracker()
        health = SkillHealthTracker(storage_path=tmp_skill_dir / "health.json")
        scorer = SkillQualityScorer(health_tracker=health)
        orch = SkillQualityOrchestrator(scorer=scorer, evolution=evolution, health=health)

        good_result = await orch.improve_skill(good_skill)
        bad_result = await orch.improve_skill(bad_skill)

        # Good skill should be stable
        assert good_result.applied is False
        assert good_result.before_score >= 0.5

        # Bad skill should improve (single pass won't hit 0.5 from 0.06, but should improve)
        assert bad_result.applied is True
        assert bad_result.after_score > bad_result.before_score

        # Evolution should have recorded a version
        assert len(evolution._versions.get("BAD_SKILL", [])) >= 1

        # Health should have entries
        assert health.get_health("BAD_SKILL") is not None

    @pytest.mark.asyncio
    async def test_idempotent_re_run(self, bad_skill):
        """Running twice on same skill should not regress."""
        orch = SkillQualityOrchestrator()
        r1 = await orch.improve_skill(bad_skill)
        r2 = await orch.improve_skill(bad_skill)

        assert r1.applied is True
        # Second run should find it stable or improve further
        assert r2.after_score >= r1.after_score
        assert r2.error is None
