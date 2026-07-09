"""Discriminating tests for reporting.NightlyReporter (V-model audit, 2026-06-05).

`reporting` was a no-test module. generate_nightly_report_dict is the pure core (no I/O).
Each test fails a plausible wrong impl:
  - empty metrics that divides by zero instead of reporting 0.0 / "No metrics recorded",
  - an average that crashes or SKIPS a metric missing 'success_rate' (must default it to 0.0),
  - dropping the System Health checklist.
"""
from __future__ import annotations

from cohezion.reporting.nightly import NightlyReporter


def _reporter(tmp_path) -> NightlyReporter:
    return NightlyReporter(report_dir=str(tmp_path / "reports"))


def test_empty_metrics_no_divide_by_zero(tmp_path) -> None:
    d = _reporter(tmp_path).generate_nightly_report_dict([])
    assert d["avg_success_rate"] == 0.0
    assert d["total_executions"] == 0
    assert "No metrics recorded today." in d["content"]


def test_average_success_rate(tmp_path) -> None:
    d = _reporter(tmp_path).generate_nightly_report_dict(
        [{"success_rate": 1.0}, {"success_rate": 0.0}]
    )
    assert d["avg_success_rate"] == 0.5
    assert d["total_executions"] == 2
    assert "Average Success Rate**: 0.50" in d["content"]


def test_missing_success_rate_defaults_to_zero_not_skipped(tmp_path) -> None:
    # Discriminating: a metric without 'success_rate' contributes 0.0 to the mean over ALL
    # metrics. A skip-impl would give 1.0; a crash-impl would raise KeyError.
    d = _reporter(tmp_path).generate_nightly_report_dict(
        [{"success_rate": 1.0}, {"iterations": 5}]
    )
    assert d["avg_success_rate"] == 0.5   # (1.0 + 0.0) / 2
    assert d["total_executions"] == 2


def test_content_always_includes_system_health(tmp_path) -> None:
    for metrics in ([], [{"success_rate": 0.9}]):
        content = _reporter(tmp_path).generate_nightly_report_dict(metrics)["content"]
        assert "## System Health" in content
        assert "Red Wall Isolation Intact" in content
