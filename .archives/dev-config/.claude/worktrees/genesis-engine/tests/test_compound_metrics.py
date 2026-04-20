"""Tests for compound metrics collector and health models."""

from __future__ import annotations

import pytest

from cohezion.compound.health import CompoundHealthReport, SkillHistoryResponse
from cohezion.compound.metrics import (
    CompoundMetricsCollector,
    get_collector,
    reset_collector,
)


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """Reset the singleton before each test."""
    reset_collector()


@pytest.fixture
def collector() -> CompoundMetricsCollector:
    return CompoundMetricsCollector()


class TestRecordExecution:
    def test_record_execution(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution(
            skill_name="code_review",
            success=True,
            tokens_used=150,
            duration_ms=320.5,
            model_used="phi3:mini",
        )
        assert collector.total_executions == 1
        assert collector._executions[0].skill_name == "code_review"
        assert collector._executions[0].success is True
        assert collector._executions[0].tokens_used == 150
        assert collector._executions[0].duration_ms == 320.5
        assert collector._executions[0].model_used == "phi3:mini"
        assert collector._executions[0].timestamp > 0


class TestRecordRefinement:
    def test_record_refinement(self, collector: CompoundMetricsCollector) -> None:
        collector.record_refinement(
            skill_name="code_review",
            version_before="1.0",
            version_after="1.1",
            learnings_added=3,
        )
        assert collector.total_refinements == 1
        assert collector._refinements[0].skill_name == "code_review"
        assert collector._refinements[0].version_before == "1.0"
        assert collector._refinements[0].version_after == "1.1"
        assert collector._refinements[0].learnings_added == 3
        assert collector._refinements[0].timestamp > 0


class TestRecordCycle:
    def test_record_cycle(self, collector: CompoundMetricsCollector) -> None:
        collector.record_cycle(
            skill_name="code_review",
            executions=5,
            refinements=2,
            compound_score_delta=0.15,
            total_tokens=800,
            total_duration_ms=5000.0,
        )
        assert collector.total_cycles == 1
        assert collector._cycles[0].skill_name == "code_review"
        assert collector._cycles[0].executions == 5
        assert collector._cycles[0].refinements == 2
        assert collector._cycles[0].compound_score_delta == 0.15
        assert collector._cycles[0].total_tokens == 800
        assert collector._cycles[0].total_duration_ms == 5000.0


class TestSuccessRate:
    def test_success_rate(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution("a", True, 100, 10.0)
        collector.record_execution("b", True, 100, 10.0)
        collector.record_execution("c", False, 100, 10.0)
        assert abs(collector.success_rate() - 2 / 3) < 1e-6

    def test_success_rate_empty(self, collector: CompoundMetricsCollector) -> None:
        assert collector.success_rate() == 0.0


class TestModelUsage:
    def test_model_usage(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution("a", True, 100, 10.0, model_used="phi3:mini")
        collector.record_execution("b", True, 100, 10.0, model_used="phi3:mini")
        collector.record_execution("c", True, 100, 10.0, model_used="deepseek-r1:70b")
        collector.record_execution("d", True, 100, 10.0)  # no model → "unknown"

        usage = collector.model_usage()
        assert usage["phi3:mini"] == 2
        assert usage["deepseek-r1:70b"] == 1
        assert usage["unknown"] == 1


class TestTopRefinedSkills:
    def test_top_refined_skills(self, collector: CompoundMetricsCollector) -> None:
        collector.record_refinement("skill_a", "1.0", "1.1", 1)
        collector.record_refinement("skill_a", "1.1", "1.2", 2)
        collector.record_refinement("skill_a", "1.2", "1.3", 1)
        collector.record_refinement("skill_b", "1.0", "1.1", 1)
        collector.record_refinement("skill_c", "1.0", "1.1", 1)
        collector.record_refinement("skill_c", "1.1", "1.2", 1)

        top = collector.top_refined_skills(limit=2)
        assert len(top) == 2
        assert top[0] == ("skill_a", 3)
        assert top[1] == ("skill_c", 2)


class TestCompoundScoreTrend:
    def test_compound_score_trend(self, collector: CompoundMetricsCollector) -> None:
        collector.record_cycle("a", 3, 1, 0.10, 500, 3000.0)
        collector.record_cycle("b", 5, 2, 0.25, 900, 6000.0)

        trend = collector.compound_score_trend()
        assert len(trend) == 2
        assert trend[0]["skill_name"] == "a"
        assert trend[0]["compound_score_delta"] == 0.10
        assert "timestamp" in trend[0]
        assert trend[1]["skill_name"] == "b"
        assert trend[1]["compound_score_delta"] == 0.25


class TestSkillHistory:
    def test_skill_history(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution("code_review", True, 100, 10.0)
        collector.record_execution("code_review", False, 200, 20.0)
        collector.record_execution("other_skill", True, 50, 5.0)
        collector.record_refinement("code_review", "1.0", "1.1", 2)
        collector.record_cycle("code_review", 2, 1, 0.05, 300, 30.0)

        history = collector.skill_history("code_review")
        assert history["skill_name"] == "code_review"
        assert history["executions"] == 2
        assert history["refinements"] == 1
        assert history["cycles"] == 1
        assert history["total_tokens"] == 300
        assert history["success_rate"] == 0.5
        assert history["latest_execution"] is not None
        assert history["latest_refinement"] is not None

    def test_skill_history_empty(self, collector: CompoundMetricsCollector) -> None:
        history = collector.skill_history("nonexistent")
        assert history["executions"] == 0
        assert history["success_rate"] == 0.0
        assert history["latest_execution"] is None


class TestHealthDict:
    def test_health_dict(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution("a", True, 100, 10.0, model_used="phi3:mini")
        collector.record_execution("a", False, 200, 20.0, model_used="phi3:mini")
        collector.record_refinement("a", "1.0", "1.1", 1)
        collector.record_cycle("a", 2, 1, 0.12, 300, 30.0)

        health = collector.to_health_dict()
        assert health["total_executions"] == 2
        assert health["total_refinements"] == 1
        assert health["total_cycles"] == 1
        assert health["success_rate"] == 0.5
        assert health["total_tokens"] == 300
        assert health["model_usage"] == {"phi3:mini": 2}
        assert len(health["top_refined_skills"]) == 1
        assert health["top_refined_skills"][0] == {"skill": "a", "count": 1}
        assert len(health["compound_score_trend"]) == 1


class TestSingleton:
    def test_singleton(self) -> None:
        c1 = get_collector()
        c2 = get_collector()
        assert c1 is c2

    def test_reset_creates_new_instance(self) -> None:
        c1 = get_collector()
        reset_collector()
        c2 = get_collector()
        assert c1 is not c2


class TestReset:
    def test_reset(self, collector: CompoundMetricsCollector) -> None:
        collector.record_execution("a", True, 100, 10.0)
        collector.record_refinement("a", "1.0", "1.1", 1)
        collector.record_cycle("a", 1, 1, 0.1, 100, 10.0)

        collector.reset()
        assert collector.total_executions == 0
        assert collector.total_refinements == 0
        assert collector.total_cycles == 0


class TestHealthModels:
    def test_compound_health_report_defaults(self) -> None:
        report = CompoundHealthReport()
        assert report.total_executions == 0
        assert report.success_rate == 0.0
        assert report.model_usage == {}

    def test_compound_health_report_from_dict(self) -> None:
        data = {
            "total_executions": 10,
            "total_refinements": 3,
            "total_cycles": 2,
            "success_rate": 0.85,
            "total_tokens": 5000,
            "model_usage": {"phi3:mini": 8, "deepseek-r1:70b": 2},
            "top_refined_skills": [{"skill": "a", "count": 3}],
            "compound_score_trend": [],
        }
        report = CompoundHealthReport(**data)
        assert report.total_executions == 10
        assert report.model_usage["phi3:mini"] == 8

    def test_skill_history_response(self) -> None:
        resp = SkillHistoryResponse(
            skill_name="code_review",
            executions=5,
            refinements=2,
            cycles=1,
            total_tokens=1000,
            success_rate=0.8,
        )
        assert resp.skill_name == "code_review"
        assert resp.latest_execution is None
