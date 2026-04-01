"""
End-to-End Tests for Traceability Engine

Verify actual end-to-end functionality:
- Run full extraction
- Verify matrices are accurate
- Verify output files exist
- Verify health scores are reasonable
"""

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from base_engine import EngineConfig
from repo_health.repo_health_engine import RepoHealthEngine
from traceability_engine import TraceabilityEngine


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")


class TestTraceabilityE2E:
    """End-to-end tests for traceability engine."""

    @pytest.mark.integration
    def test_full_extraction_generates_matrices(self):
        """Verify full extraction generates all matrices."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT / "_bmad" / "_config" / "traceability" / "test_output",
            verbose=True,
        )
        engine = TraceabilityEngine(config=config)
        matrix = engine.run_full_extraction()

        # Verify matrices have data
        assert matrix.agent_workflow is not None
        assert matrix.workflow_task is not None
        assert matrix.party_module is not None

        # Verify reasonable counts
        assert len(matrix.agent_workflow) > 0, "Agent-workflow matrix should have data"
        assert len(matrix.party_module) == 4, "Should have 4 party configs"

    @pytest.mark.integration
    def test_output_files_created(self):
        """Verify output files are created."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT / "_bmad" / "_config" / "traceability" / "test_output",
            verbose=True,
        )
        engine = TraceabilityEngine(config=config)
        matrix = engine.run_full_extraction()
        output_files = engine.write_matrices(matrix)

        # Verify files exist
        assert output_files["agent_workflow"].exists()
        assert output_files["party_module"].exists()

        # Verify files have content
        assert output_files["agent_workflow"].stat().st_size > 100
        assert output_files["party_module"].stat().st_size > 50

    @pytest.mark.integration
    def test_report_generation(self):
        """Verify report generation."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT / "_bmad" / "_config" / "traceability" / "test_output",
            verbose=True,
        )
        engine = TraceabilityEngine(config=config)
        matrix = engine.run_full_extraction()
        report = engine.generate_report()

        # Verify report has content
        assert len(report) > 100
        assert "# BMAD Traceability Report" in report
        assert "## Summary Statistics" in report


class TestRepoHealthE2E:
    """End-to-end tests for repo health engine."""

    @pytest.mark.integration
    def test_full_health_check(self):
        """Verify full health check runs."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT
            / "_bmad"
            / "_config"
            / "traceability"
            / "repo_health"
            / "test_output",
            verbose=True,
        )
        engine = RepoHealthEngine(config=config)
        report = engine.run_full_health_check()

        # Verify report has data
        assert report.overall_health_score >= 0
        assert report.overall_health_score <= 100

        # Verify all metrics populated
        assert report.code_quality.lines_of_code > 0
        assert report.test_health.total_tests > 0
        assert report.git_health.total_branches > 0

    @pytest.mark.integration
    def test_health_report_written(self):
        """Verify health report is written."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT
            / "_bmad"
            / "_config"
            / "traceability"
            / "repo_health"
            / "test_output",
            verbose=True,
        )
        engine = RepoHealthEngine(config=config)
        report = engine.run_full_health_check()
        report_file = engine.write_report(report)

        # Verify file exists
        assert report_file.exists()
        assert report_file.stat().st_size > 100

    @pytest.mark.integration
    def test_health_score_reasonable(self):
        """Verify health score is reasonable."""
        config = EngineConfig(
            project_root=PROJECT_ROOT,
            output_dir=PROJECT_ROOT
            / "_bmad"
            / "_config"
            / "traceability"
            / "repo_health"
            / "test_output",
            verbose=True,
        )
        engine = RepoHealthEngine(config=config)
        report = engine.run_full_health_check()

        # Score should be in reasonable range (not 0 or 100)
        assert 20 <= report.overall_health_score <= 95, (
            f"Health score {report.overall_health_score} seems unreasonable"
        )


class TestRecursiveLoopE2E:
    """End-to-end tests for recursive loop."""

    @pytest.mark.integration
    def test_snapshot_created(self):
        """Verify snapshot is created."""
        from _bmad._config.traceability.recursive_loop import run_traceability_engine

        result = run_traceability_engine(self_trace=False)
        assert result["returncode"] == 0
        assert "Snapshot saved" in result["stdout"]

    @pytest.mark.integration
    def test_engine_runs_without_errors(self):
        """Verify engine runs without errors."""
        from _bmad._config.traceability.recursive_loop import run_traceability_engine

        result = run_traceability_engine(self_trace=False)
        assert result["returncode"] == 0, f"Engine failed: {result['stderr']}"
        assert "Traceability extraction complete" in result["stdout"]
