"""Tests for Version Telemetry Dashboard (Story 7.4)."""

from __future__ import annotations

from cohezion.registry.version_telemetry import (
    DriftStatus,
    VersionConflict,
    VersionTelemetry,
)


class TestVersionTelemetry:
    def test_up_to_date_deps_green(self):
        telemetry = VersionTelemetry()
        current = {"numpy": "2.0.0"}
        latest = {"numpy": "2.0.0"}
        panel = telemetry.scan(current, latest)
        assert panel.coherence_score == 1.0
        assert len(panel.drifts) == 0

    def test_drifted_dep_detected(self):
        telemetry = VersionTelemetry()
        current = {"requests": "2.28.0"}
        latest = {"requests": "2.31.0"}
        panel = telemetry.scan(current, latest)
        assert len(panel.drifts) == 1
        assert panel.drifts[0].status == DriftStatus.AMBER

    def test_coherence_drops_on_drift(self):
        telemetry = VersionTelemetry()
        current = {"a": "1.0.0", "b": "1.0.0"}
        latest = {"a": "1.5.0", "b": "1.0.0"}
        panel = telemetry.scan(current, latest)
        assert panel.coherence_score < 1.0

    def test_conflict_triggers_healing(self):
        telemetry = VersionTelemetry()
        conflicts = [VersionConflict("x", ">=2.0", "<2.0", ["pkgA", "pkgB"])]
        panel = telemetry.scan({}, {}, conflicts=conflicts)
        assert panel.healing_triggered is True

    def test_coherence_collapse_below_threshold(self):
        telemetry = VersionTelemetry()
        # Lots of drift + conflict → collapse
        current = {f"pkg{i}": "1.0.0" for i in range(5)}
        latest = {f"pkg{i}": "1.9.0" for i in range(5)}
        conflicts = [VersionConflict("pkgX", ">=1.0", "<1.0", ["a", "b"])]
        panel = telemetry.scan(current, latest, conflicts=conflicts)
        assert panel.healing_triggered is True

    def test_panel_serializable(self):
        telemetry = VersionTelemetry()
        panel = telemetry.scan({"numpy": "2.0.0"}, {"numpy": "2.0.0"})
        d = panel.to_dict()
        assert "coherence_score" in d
        assert "drifts" in d
