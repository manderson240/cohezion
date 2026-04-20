"""
Repository Health Engine Test Suite

Tests verify:
- Code quality metrics extraction
- Test health metrics
- Technical debt detection
- Git health checks
- Documentation coverage
- Health score calculation
"""

import sys
from pathlib import Path

import pytest


# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _bmad._config.traceability.repo_health.repo_health_engine import (
    RepoHealthEngine,
    RepoHealthReport,
)


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")


class TestCodeQualityMetrics:
    """Tests for code quality checking."""

    @pytest.mark.fast
    def test_lint_error_counting(self):
        """Verify lint error counting with realistic bounds."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_code_quality()
        # Realistic bounds: expect 0-100 errors for healthy codebase
        assert 0 <= metrics.lint_errors < 100, (
            f"Lint errors {metrics.lint_errors} outside expected range"
        )
        assert 0 <= metrics.lint_warnings < 200, (
            f"Lint warnings {metrics.lint_warnings} outside expected range"
        )

    @pytest.mark.fast
    def test_type_error_counting(self):
        """Verify type error counting with realistic bounds."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_code_quality()
        # Expect 0-50 type errors for healthy codebase
        assert 0 <= metrics.type_errors < 50, (
            f"Type errors {metrics.type_errors} outside expected range"
        )

    @pytest.mark.fast
    def test_loc_counting(self):
        """Verify lines of code counting."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_code_quality()
        # Expect substantial codebase
        assert metrics.lines_of_code > 10000, f"LOC {metrics.lines_of_code} seems too low"
        assert metrics.lines_of_code < 1000000, f"LOC {metrics.lines_of_code} seems too high"


class TestTestHealthMetrics:
    """Tests for test health checking."""

    @pytest.mark.fast
    def test_test_counting(self):
        """Verify test counting."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_test_health()
        assert metrics.total_tests >= 0

    @pytest.mark.fast
    def test_coverage_percent(self):
        """Verify coverage percentage."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_test_health()
        assert 0 <= metrics.coverage_percent <= 100


class TestTechDebtMetrics:
    """Tests for technical debt detection."""

    @pytest.mark.fast
    def test_todo_detection(self):
        """Verify TODO marker detection."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_tech_debt()
        assert metrics.todo_count >= 0

    @pytest.mark.fast
    def test_fixme_detection(self):
        """Verify FIXME marker detection."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_tech_debt()
        assert metrics.fixme_count >= 0

    @pytest.mark.fast
    def test_long_file_detection(self):
        """Verify long file detection (>500 lines)."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_tech_debt()
        assert isinstance(metrics.long_files, list)


class TestGitHealthMetrics:
    """Tests for Git health checking."""

    @pytest.mark.fast
    def test_branch_counting(self):
        """Verify branch counting."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_git_health()
        assert metrics.total_branches > 0

    @pytest.mark.fast
    def test_untracked_file_counting(self):
        """Verify untracked file counting."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_git_health()
        assert metrics.untracked_files >= 0


class TestDocumentationHealthMetrics:
    """Tests for documentation health checking."""

    @pytest.mark.fast
    def test_module_counting(self):
        """Verify module counting."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_documentation_health()
        assert metrics.total_modules > 0

    @pytest.mark.fast
    def test_doc_coverage(self):
        """Verify documentation coverage calculation."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        metrics = engine.check_documentation_health()
        assert 0 <= metrics.doc_coverage_percent <= 100


class TestHealthScoreCalculation:
    """Tests for health score calculation."""

    @pytest.mark.fast
    def test_health_score_range(self):
        """Verify health score is in 0-100 range."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = engine.run_full_health_check()
        assert 0 <= report.overall_health_score <= 100

    @pytest.mark.fast
    def test_health_score_weights(self):
        """Verify health score weights are applied."""
        # Code quality (30%), test health (25%), tech debt (20%),
        # git health (15%), doc health (10%)
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = RepoHealthReport()
        report.code_quality.lint_errors = 100  # Should lower score
        score = engine.calculate_health_score(report)
        assert score < 100


class TestRecommendations:
    """Tests for recommendation generation."""

    @pytest.mark.fast
    def test_lint_recommendations(self):
        """Verify lint recommendations generated."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = RepoHealthReport()
        report.code_quality.lint_errors = 15
        engine.generate_recommendations(report)
        assert any("ruff" in rec for rec in report.recommendations)

    @pytest.mark.fast
    def test_coverage_recommendations(self):
        """Verify coverage recommendations generated."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = RepoHealthReport()
        report.test_health.coverage_percent = 50
        engine.generate_recommendations(report)
        assert any("coverage" in rec.lower() for rec in report.recommendations)


class TestCriticalIssues:
    """Tests for critical issue detection."""

    @pytest.mark.fast
    def test_failing_test_critical(self):
        """Verify failing tests trigger critical issue."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = RepoHealthReport()
        report.test_health.failing_tests = 15
        engine.generate_critical_issues(report)
        assert len(report.critical_issues) > 0

    @pytest.mark.fast
    def test_type_error_critical(self):
        """Verify type errors trigger critical issue."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = RepoHealthReport()
        report.code_quality.type_errors = 25
        engine.generate_critical_issues(report)
        assert len(report.critical_issues) > 0


class TestIntegration:
    """Integration tests requiring actual file system."""

    @pytest.mark.integration
    def test_full_health_check(self):
        """End-to-end health check."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = engine.run_full_health_check()
        assert report.timestamp != ""
        assert report.overall_health_score >= 0

    @pytest.mark.integration
    def test_report_writing(self):
        """Verify report file writing."""
        engine = RepoHealthEngine(PROJECT_ROOT)
        report = engine.run_full_health_check()
        report_file = engine.write_report(report)
        assert report_file.exists()
