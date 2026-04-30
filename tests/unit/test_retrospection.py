"""Tests for the RetrospectionEngine."""

import tempfile
from pathlib import Path

import pytest

from cohezion.core.compound.retrospection import (
    LearningPattern,
    RetrospectionEngine,
    SkillRefinement,
)


@pytest.fixture
def engine():
    """Create engine pointing at actual knowledge graph."""
    kg_dir = Path(__file__).parent.parent.parent / "src" / "cohezion" / "knowledge_graph"
    return RetrospectionEngine(kg_dir=kg_dir)


@pytest.fixture
def engine_missing():
    """Create engine pointing at nonexistent directory."""
    return RetrospectionEngine(kg_dir=Path(tempfile.gettempdir()) / "nonexistent_kg")


class TestAnalyzeLearnings:
    def test_parses_real_learnings(self, engine):
        patterns = engine.analyze_learnings()
        assert len(patterns) > 0
        assert all(isinstance(p, LearningPattern) for p in patterns)

    def test_learning_has_id_and_title(self, engine):
        patterns = engine.analyze_learnings()
        for p in patterns:
            assert p.id > 0
            assert len(p.title) > 0

    def test_handles_missing_file(self, engine_missing):
        patterns = engine_missing.analyze_learnings()
        assert patterns == []


class TestCompoundScores:
    def test_returns_scores(self, engine):
        scores = engine.calculate_compound_scores()
        assert isinstance(scores, dict)
        assert len(scores) > 0

    def test_scores_are_normalized(self, engine):
        scores = engine.calculate_compound_scores()
        for score in scores.values():
            assert 0.0 <= score <= 1.5  # Allow slight over due to outgoing refs


class TestSessionReport:
    def test_generates_report_from_facts(self, engine):
        facts = {
            "intent": "test the retrospection engine",
            "files_created": ["test.py"],
            "tests_passing": 100,
        }
        report = engine.generate_session_report(facts)
        assert "Intent" in report
        assert "test the retrospection engine" in report
        assert "Files Created" in report
        assert "100" in report

    def test_empty_facts(self, engine):
        report = engine.generate_session_report({})
        assert "Session Retrospective Report" in report


class TestSkillRefinements:
    def test_returns_refinement_list(self, engine):
        refinements = engine.suggest_skill_refinements()
        assert isinstance(refinements, list)
        assert all(isinstance(r, SkillRefinement) for r in refinements)
