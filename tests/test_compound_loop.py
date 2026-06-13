"""Tests for Phase 4D compound feedback loop (SkillRefiner + RetrospectionEngine)."""

from __future__ import annotations

from cohezion.core.compound.retrospection import (
    RetrospectionEngine,
    SkillRefinement,
)
from cohezion.core.compound.skill_refiner import RefinementResult, SkillRefiner
from cohezion.core.plan_executor import ExecutionResult
from cohezion.swarm.execution_orchestrator import ExecutionReport, TaskResult


# ---------------------------------------------------------------------------
# SkillRefiner
# ---------------------------------------------------------------------------


class TestSkillRefiner:
    def test_refine_creates_section(self, tmp_path):
        """Refining a skill appends a LEARNED REFINEMENTS section."""
        md_file = tmp_path / "TEST_SKILL_PRIME.md"
        md_file.write_text(
            "# SKILL: TEST_SKILL_PRIME\n\n## DOMAIN EXPERTISE\nTest domain.\n\n## VERSION\n1.0\n"
        )

        refiner = SkillRefiner(skills_dir=tmp_path)
        result = refiner.refine_skill(
            "TEST_SKILL_PRIME",
            learnings=["Caching reduces latency", "Retry logic improves reliability"],
            reason="Execution analysis found these patterns",
        )

        assert isinstance(result, RefinementResult)
        assert result.skill_name == "TEST_SKILL_PRIME"
        assert len(result.additions) == 2
        assert result.version_before == "1.0"
        assert result.version_after == "1.1"

        content = md_file.read_text()
        assert "## LEARNED REFINEMENTS" in content
        assert "Caching reduces latency" in content
        assert "1.1" in content

    def test_refine_appends_to_existing_section(self, tmp_path):
        """Second refinement appends to existing LEARNED REFINEMENTS."""
        md_file = tmp_path / "TEST_SKILL_PRIME.md"
        md_file.write_text(
            "# SKILL: TEST_SKILL_PRIME\n\n## VERSION\n1.0\n\n## LEARNED REFINEMENTS\n\n- First insight\n"
        )

        refiner = SkillRefiner(skills_dir=tmp_path)
        refiner.refine_skill(
            "TEST_SKILL_PRIME",
            learnings=["Second insight"],
        )

        content = md_file.read_text()
        assert "First insight" in content
        assert "Second insight" in content

    def test_refine_missing_skill(self, tmp_path):
        """Refining a nonexistent skill returns empty result."""
        refiner = SkillRefiner(skills_dir=tmp_path)
        result = refiner.refine_skill("NONEXISTENT_PRIME", learnings=["test"])
        assert result.skill_name == "NONEXISTENT_PRIME"
        assert len(result.additions) == 0

    def test_refine_from_suggestions(self, tmp_path):
        """Batch refinement from SkillRefinement objects."""
        md1 = tmp_path / "SKILL_A_PRIME.md"
        md1.write_text("# SKILL: SKILL_A_PRIME\n\n## VERSION\n1.0\n")
        md2 = tmp_path / "SKILL_B_PRIME.md"
        md2.write_text("# SKILL: SKILL_B_PRIME\n\n## VERSION\n2.0\n")

        suggestions = [
            SkillRefinement(
                skill_name="SKILL_A_PRIME",
                reason="High usage",
                suggested_additions=["Learning 1"],
            ),
            SkillRefinement(
                skill_name="SKILL_B_PRIME",
                reason="Error patterns",
                suggested_additions=["Learning 2", "Learning 3"],
            ),
        ]

        refiner = SkillRefiner(skills_dir=tmp_path)
        results = refiner.refine_from_suggestions(suggestions)
        assert len(results) == 2
        assert results[0].version_after == "1.1"
        assert results[1].version_after == "2.1"

    def test_version_bump(self):
        """Version bumping increments patch number."""
        assert SkillRefiner._bump_version("1.0") == "1.1"
        assert SkillRefiner._bump_version("2.3.4") == "2.3.5"
        assert SkillRefiner._bump_version("1") == "2"


# ---------------------------------------------------------------------------
# RetrospectionEngine.analyze_execution
# ---------------------------------------------------------------------------


class TestRetrospectionAnalyzeExecution:
    def test_analyze_execution_basic(self):
        """analyze_execution returns expected structure."""
        engine = RetrospectionEngine()

        # Build a minimal execution report
        report = ExecutionReport(
            report_id="test_001",
            plan_name="test-plan",
            intent="test",
            task_results=[
                TaskResult(
                    task_id="t1",
                    subject="Task A",
                    status="completed",
                    execution=ExecutionResult(
                        skill_name="test",
                        final_output="done",
                        total_tokens=100,
                        total_duration_ms=50.0,
                    ),
                    duration_ms=50.0,
                ),
            ],
            total_tokens=100,
            total_duration_ms=50.0,
        )

        result = engine.analyze_execution(report)
        assert "compound_score_delta" in result
        assert "patterns" in result
        assert "insights" in result
        assert result["tasks_completed"] == 1
        assert result["tasks_failed"] == 0

    def test_analyze_execution_with_failures(self):
        """Failed tasks reduce compound score."""
        engine = RetrospectionEngine()

        report = ExecutionReport(
            report_id="test_002",
            plan_name="fail-plan",
            task_results=[
                TaskResult(task_id="t1", subject="A", status="completed"),
                TaskResult(task_id="t2", subject="B", status="failed", error="boom"),
            ],
        )

        result = engine.analyze_execution(report)
        assert result["tasks_failed"] == 1
        assert result["compound_score_delta"] < 1.0
        assert any("failed" in p for p in result["patterns"])

    def test_analyze_execution_empty_report(self):
        """Empty report handles gracefully."""
        engine = RetrospectionEngine()
        report = ExecutionReport(report_id="empty", plan_name="empty")
        result = engine.analyze_execution(report)
        assert result["tasks_total"] == 0
        assert result["compound_score_delta"] >= 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestSwarmExecuteEndpoint:
    def test_swarm_execute_returns_200(self):
        """POST /swarm/execute returns 200 with execution report."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi.testclient import TestClient

        from cohezion.api import app

        mock_client = MagicMock()
        mock_client.generate = AsyncMock(return_value="mock output")

        with patch(
            "cohezion.swarm.compound_client.get_compound_client",
            return_value=mock_client,
        ):
            client = TestClient(app)
            response = client.post(
                "/swarm/execute",
                json={"intent": "test compound engineering", "max_agents": 2},
            )
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "status" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)


class TestCompoundMetricsEndpoint:
    def test_compound_metrics_returns_200(self):
        """GET /metrics/compound returns 200 with compound metrics."""
        from fastapi.testclient import TestClient

        from cohezion.api import app

        client = TestClient(app)
        response = client.get("/metrics/compound")
        assert response.status_code == 200
        data = response.json()
        assert "total_learnings" in data
        assert "top_compound_scores" in data
        assert "suggested_refinements" in data
