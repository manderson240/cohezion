"""Discriminating tests for dogfooding.PerformanceMonitor (V-model audit, 2026-06-05).

`dogfooding` was a no-test module. PerformanceMonitor is in-memory + jsonl-backed metric
tracking with strict-`>` thresholds and a time-window filter. Each test fails a plausible
wrong impl:
  - a `>=` threshold (exactly-at-warning should be "ok", not "warning"),
  - an unknown metric that isn't reported as "unknown",
  - get_recent that returns OLD metrics outside the window,
  - check_alerts that surfaces "ok" metrics (or suppresses critical ones).
All tests inject tmp_path so the real ~/.config/cohezion metrics file is never touched.
"""

from __future__ import annotations

import json

from cohezion.dogfooding.production_hardening import PerformanceMonitor


def _pm(tmp_path) -> PerformanceMonitor:
    return PerformanceMonitor(data_path=tmp_path / "metrics.jsonl")


def test_check_threshold_strict_boundaries(tmp_path) -> None:
    pm = _pm(tmp_path)
    # metric_latency_ms: warning=5000, critical=10000, strict '>'
    assert pm._check_threshold("metric_latency_ms", 4000) == "ok"
    assert pm._check_threshold("metric_latency_ms", 5000) == "ok"  # exactly at warning -> ok
    assert pm._check_threshold("metric_latency_ms", 6000) == "warning"
    assert (
        pm._check_threshold("metric_latency_ms", 10000) == "warning"
    )  # exactly at critical -> warning
    assert pm._check_threshold("metric_latency_ms", 10001) == "critical"
    assert pm._check_threshold("unknown_metric", 999999) == "unknown"


def test_record_metric_persists_and_returns_status(tmp_path) -> None:
    pm = _pm(tmp_path)
    m = pm.record_metric("dashboard_load_ms", 2000.0)  # warning band (1000<2000<=3000)
    assert m["threshold_status"] == "warning"
    assert m["metric"] == "dashboard_load_ms" and m["value_ms"] == 2000.0
    # persisted as one jsonl line
    lines = (tmp_path / "metrics.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["metric"] == "dashboard_load_ms"


def test_get_recent_excludes_old_metrics(tmp_path) -> None:
    pm = _pm(tmp_path)
    # Inject an OLD metric directly, then record a fresh one.
    old = {
        "timestamp": "2020-01-01T00:00:00",
        "metric": "x",
        "value_ms": 1,
        "context": {},
        "threshold_status": "ok",
    }
    (tmp_path / "metrics.jsonl").write_text(json.dumps(old) + "\n")
    pm.record_metric("lever_adjustment_ms", 100.0)

    recent = pm.get_recent_metrics(minutes=5)
    assert len(recent) == 1  # only the fresh one; the 2020 metric is excluded
    assert recent[0]["metric"] == "lever_adjustment_ms"


def test_get_recent_empty_when_no_file(tmp_path) -> None:
    assert _pm(tmp_path).get_recent_metrics() == []


def test_check_alerts_only_warning_and_critical(tmp_path) -> None:
    pm = _pm(tmp_path)
    pm.record_metric("metric_latency_ms", 100.0)  # ok -> no alert
    pm.record_metric("metric_latency_ms", 11000.0)  # critical -> alert
    alerts = pm.check_alerts()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical" and alerts[0]["value_ms"] == 11000.0
