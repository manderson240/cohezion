"""Tests for SkillQualityDataPipeline — TDD, fast, no live services.

Covers:
- save_report appends JSONL with timestamp + report dict
- load_history returns chronological list, empty list for unknown skill
- get_trend computes deltas / direction / avg over N sessions
- malformed JSONL lines are skipped gracefully
- safe filenames for skills with path-like characters
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cohezion.compound.skill_quality_data_pipeline import SkillQualityDataPipeline
from cohezion.compound.skill_quality_scorer import (
    DimensionScore,
    SkillQualityReport,
    SkillQualityScorer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_pipeline():
    with tempfile.TemporaryDirectory() as d:
        yield SkillQualityDataPipeline(storage_dir=Path(d))


@pytest.fixture
def dummy_report():
    return SkillQualityReport(
        skill_name="test-skill",
        skill_path=Path("/fake/path.md"),
        overall_score=0.75,
        dimensions=[
            DimensionScore(name="hiho_coherence", score=0.8, weight=0.25),
            DimensionScore(name="structural", score=0.7, weight=0.20),
        ],
        hiho_stable=True,
    )


# =============================================================================
# save_report
# =============================================================================


@pytest.mark.fast
class TestSaveReport:
    def test_creates_jsonl_file(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        path = tmp_pipeline.save_report("test-skill", dummy_report)
        assert path.exists()
        assert path.suffix == ".jsonl"
        assert path.name == "test-skill.jsonl"

    def test_appends_multiple_reports(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        tmp_pipeline.save_report("test-skill", dummy_report)
        dummy_report.overall_score = 0.85
        tmp_pipeline.save_report("test-skill", dummy_report)

        file_path = tmp_pipeline._file_for("test-skill")
        lines = file_path.read_text().splitlines()
        assert len(lines) == 2
        for line in lines:
            assert json.loads(line)["report"]["skill_name"] == "test-skill"

    def test_includes_timestamp(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        tmp_pipeline.save_report("test-skill", dummy_report)
        history = tmp_pipeline.load_history("test-skill")
        assert len(history) == 1
        assert "timestamp" in history[0]
        assert history[0]["timestamp"].startswith("20")  # ISO year prefix

    def test_safe_filename_for_pathlike_skill(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        path = tmp_pipeline.save_report("skills/test", dummy_report)
        assert path.name == "skills_test.jsonl"
        assert path.exists()


# =============================================================================
# load_history
# =============================================================================


@pytest.mark.fast
class TestLoadHistory:
    def test_returns_empty_for_unknown_skill(self, tmp_pipeline: SkillQualityDataPipeline):
        assert tmp_pipeline.load_history("never-saved") == []

    def test_returns_chronological_order(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        for score in [0.1, 0.5, 0.9]:
            dummy_report.overall_score = score
            tmp_pipeline.save_report("trend-skill", dummy_report)

        history = tmp_pipeline.load_history("trend-skill")
        scores = [h["report"]["overall_score"] for h in history]
        assert scores == [0.1, 0.5, 0.9]

    def test_skips_malformed_lines(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        tmp_pipeline.save_report("bad-lines", dummy_report)
        file_path = tmp_pipeline._file_for("bad-lines")
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write("this is not json\n")
            fh.write('{"valid": true}\n')

        history = tmp_pipeline.load_history("bad-lines")
        # Should keep the first valid report, skip the garbage, keep the trailing valid line
        assert len(history) >= 1
        # The first record is the report
        assert "report" in history[0]


# =============================================================================
# get_trend
# =============================================================================


@pytest.mark.fast
class TestGetTrend:
    def test_empty_history(self, tmp_pipeline: SkillQualityDataPipeline):
        trend = tmp_pipeline.get_trend("no-history", n_sessions=5)
        assert trend["skill_name"] == "no-history"
        assert trend["n_sessions"] == 0
        assert trend["scores"] == []
        assert trend["trend_direction"] == "stable"

    def test_single_session_stable(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        tmp_pipeline.save_report("one-shot", dummy_report)
        trend = tmp_pipeline.get_trend("one-shot", n_sessions=5)
        assert trend["n_sessions"] == 1
        assert trend["scores"] == [pytest.approx(0.75)]
        assert trend["trend_direction"] == "stable"
        assert trend["delta"] == 0.0

    def test_improving_trend(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        for score in [0.3, 0.5, 0.7]:
            dummy_report.overall_score = score
            tmp_pipeline.save_report("improving", dummy_report)

        trend = tmp_pipeline.get_trend("improving", n_sessions=5)
        assert trend["n_sessions"] == 3
        assert trend["scores"] == [pytest.approx(0.3), pytest.approx(0.5), pytest.approx(0.7)]
        assert trend["delta"] == pytest.approx(0.4)
        assert trend["trend_direction"] == "improving"
        assert trend["avg_score"] == pytest.approx(0.5)
        assert trend["max_score"] == pytest.approx(0.7)
        assert trend["min_score"] == pytest.approx(0.3)

    def test_declining_trend(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        for score in [0.9, 0.6, 0.2]:
            dummy_report.overall_score = score
            tmp_pipeline.save_report("declining", dummy_report)

        trend = tmp_pipeline.get_trend("declining", n_sessions=5)
        assert trend["trend_direction"] == "declining"
        assert trend["delta"] == pytest.approx(-0.7)

    def test_respects_n_sessions_window(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        for score in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
            dummy_report.overall_score = score
            tmp_pipeline.save_report("windowed", dummy_report)

        trend = tmp_pipeline.get_trend("windowed", n_sessions=3)
        assert trend["n_sessions"] == 3
        assert trend["scores"] == [pytest.approx(0.4), pytest.approx(0.5), pytest.approx(0.6)]

    def test_stable_within_epsilon(self, tmp_pipeline: SkillQualityDataPipeline, dummy_report: SkillQualityReport):
        for score in [0.500, 0.505, 0.509]:
            dummy_report.overall_score = score
            tmp_pipeline.save_report("stable", dummy_report)

        trend = tmp_pipeline.get_trend("stable", n_sessions=5)
        assert trend["trend_direction"] == "stable"


# =============================================================================
# Integration with real scorer
# =============================================================================


@pytest.mark.fast
class TestIntegrationWithScorer:
    def test_round_trip_with_real_report(self, tmp_pipeline: SkillQualityDataPipeline, tmp_path: Path):
        # Create a minimal skill file so scorer produces a real report
        skill_file = tmp_path / "mini_skill.md"
        skill_file.write_text(
            "---\nname: mini-skill\nmetadata:\n  version: \"1.0.0\"\n  project: cohezion\n---\n\n"
            "# SKILL: MINI_SKILL\n\n## When to Use\nTest.\n\n## Key Texts\n- **0.5** = HIHO\n"
            "- **256** = FLUME\n- **SU(2)** = gauge\n\n## Instruction\n1. Step\n\n"
            "```python\npass\n```\n\n## See Also\n- other\n"
        )
        scorer = SkillQualityScorer()
        report = scorer.evaluate(skill_file)

        tmp_pipeline.save_report(report.skill_name, report)
        history = tmp_pipeline.load_history(report.skill_name)
        assert len(history) == 1
        assert history[0]["report"]["skill_name"] == report.skill_name
        assert history[0]["report"]["overall_score"] == pytest.approx(report.overall_score, abs=0.001)

        trend = tmp_pipeline.get_trend(report.skill_name, n_sessions=5)
        assert trend["n_sessions"] == 1
        assert trend["max_score"] == pytest.approx(report.overall_score, abs=0.001)
