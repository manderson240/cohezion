"""Tests for compound health monitor."""

from cohezion.compound.health_monitor import (
    get_health_report,
)
from cohezion.compound.health_monitor import (
    test_autoresearch_available as check_autoresearch,
)
from cohezion.compound.health_monitor import (
    test_error_classifier_available as check_error_classifier,
)
from cohezion.compound.health_monitor import (
    test_session_metrics_available as check_session_metrics,
)


class TestHealthMonitor:
    def test_autoresearch_check_passes(self):
        result = check_autoresearch()
        assert result["ok"] is True
        assert result["experiments"] == 1

    def test_error_classifier_check_passes(self):
        result = check_error_classifier()
        assert result["ok"] is True
        assert result["sample"] == "logic"  # ValueError → logic

    def test_session_metrics_check_passes(self):
        result = check_session_metrics()
        assert result["ok"] is True

    def test_health_report_structure(self):
        report = get_health_report()
        assert "healthy" in report
        assert "timestamp" in report
        assert "checks" in report
        assert isinstance(report["checks"], dict)

    def test_health_report_is_healthy(self):
        report = get_health_report()
        assert report["healthy"] is True, f"Health check failed: {report['checks']}"

    def test_health_report_has_all_checks(self):
        report = get_health_report()
        assert "autoresearch" in report["checks"]
        assert "error_classifier" in report["checks"]
        assert "session_metrics" in report["checks"]
        assert "experiment_recommender" in report["checks"]
        assert "experiment_scheduler" in report["checks"]
        assert "compound_engine" in report["checks"]
        assert "loop_visualizer" in report["checks"]
