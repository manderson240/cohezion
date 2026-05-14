"""Coverage batch Z45: team_metrics, sandbox_validation, mhd_mereon."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: swarm/team_metrics.py
# ---------------------------------------------------------------------------


class TestTeamMetrics:
    def test_wave_metrics_model(self):
        from cohezion.swarm.team_metrics import WaveMetrics

        wm = WaveMetrics(wave_index=1, task_count=5, duration_ms=120.5, tokens=1000)
        assert wm.wave_index == 1
        assert wm.successes == 0

    def test_team_compound_metrics_model(self):
        from cohezion.swarm.team_metrics import TeamCompoundMetrics

        metrics = TeamCompoundMetrics(plan_name="test-plan", total_tasks=10)
        assert metrics.plan_name == "test-plan"
        assert metrics.timestamp > 0

    def test_record_wave_basic(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator(plan_name="plan1")
        results = [
            {"tokens": 100, "model": "phi3:mini", "status": "completed"},
            {"tokens": 200, "model": "llama3", "status": "completed"},
        ]
        wave = agg.record_wave(wave_index=0, task_results=results, duration_ms=50.0)
        assert wave.wave_index == 0
        assert wave.task_count == 2
        assert wave.tokens == 300
        assert wave.successes == 2
        assert wave.failures == 0

    def test_record_wave_failures(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator()
        results = [
            {"tokens": 50, "model": "phi3:mini", "status": "error"},  # non-completed = failure
            {"tokens": 50, "model": "phi3:mini", "status": "completed"},
        ]
        wave = agg.record_wave(wave_index=0, task_results=results, duration_ms=100.0)
        assert wave.failures == 1
        assert wave.successes == 1

    def test_record_wave_model_usage_aggregated(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator()
        results = [
            {"tokens": 100, "model": "phi3:mini", "status": "completed"},
            {"tokens": 100, "model": "phi3:mini", "status": "completed"},
            {"tokens": 100, "model": "llama3", "status": "completed"},
        ]
        agg.record_wave(wave_index=0, task_results=results, duration_ms=30.0)
        agg.record_wave(wave_index=1, task_results=results, duration_ms=25.0)
        metrics = agg.finalize(total_duration_ms=55.0)
        assert metrics.model_usage["phi3:mini"] >= 2

    def test_finalize_returns_metrics(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator(plan_name="my-plan")
        results = [{"tokens": 200, "model": "phi3:mini", "status": "completed"}]
        agg.record_wave(0, results, 100.0)
        metrics = agg.finalize(total_duration_ms=100.0, compound_score_delta=0.05)
        assert metrics.plan_name == "my-plan"
        assert metrics.total_tasks == 1
        assert metrics.total_tokens == 200
        assert metrics.parallel_efficiency == pytest.approx(1.0)
        assert metrics.compound_score_delta == pytest.approx(0.05)
        assert metrics.success_rate == pytest.approx(1.0)

    def test_finalize_zero_duration(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator()
        metrics = agg.finalize(total_duration_ms=0.0)
        assert metrics.parallel_efficiency == pytest.approx(1.0)

    def test_finalize_parallel_efficiency(self):
        from cohezion.swarm.team_metrics import TeamMetricsAggregator

        agg = TeamMetricsAggregator()
        results = [{"tokens": 50, "model": "m", "status": "completed"}]
        # Two waves of 50ms each → 100ms total sequential
        # But actual time = 60ms (parallelism saved 40ms)
        agg.record_wave(0, results, 50.0)
        agg.record_wave(1, results, 50.0)
        metrics = agg.finalize(total_duration_ms=60.0)
        assert metrics.parallel_efficiency > 1.0


# ---------------------------------------------------------------------------
# Module 2: vanguard/sandbox_validation.py
# ---------------------------------------------------------------------------


class TestSandboxValidation:
    def test_validation_verdict_enum(self):
        from cohezion.vanguard.sandbox_validation import ValidationVerdict

        assert ValidationVerdict.PASSED.value == "passed"
        assert ValidationVerdict.QUARANTINED.value == "quarantined"

    def test_sandbox_script_defaults(self):
        from cohezion.vanguard.sandbox_validation import SANDBOX_GTT_QUOTA_BYTES, SandboxScript

        script = SandboxScript(script_id="s1", source_url="http://x.com", code="x = 1")
        assert script.requested_bytes == SANDBOX_GTT_QUOTA_BYTES

    def test_validation_report_to_dict(self):
        from cohezion.vanguard.sandbox_validation import ValidationReport, ValidationVerdict

        report = ValidationReport(script_id="s1", verdict=ValidationVerdict.PASSED, reason="ok", memory_used_bytes=1024)
        d = report.to_dict()
        assert d["verdict"] == "passed"
        assert d["memory_used_bytes"] == 1024

    def test_validate_safe_script_passes(self):
        from cohezion.vanguard.sandbox_validation import SandboxScript, SubstrateSandbox, ValidationVerdict

        validator = SubstrateSandbox()
        script = SandboxScript(script_id="safe_s1", source_url="http://safe.com", code="x = 1 + 2")
        report = validator.validate(script)
        assert report.verdict == ValidationVerdict.PASSED
        assert report.memory_used_bytes > 0

    def test_validate_unsafe_pattern_quarantined(self):
        from cohezion.vanguard.sandbox_validation import SandboxScript, SubstrateSandbox, ValidationVerdict

        validator = SubstrateSandbox()
        script = SandboxScript(script_id="bad_s1", source_url="http://bad.com", code="result = process_spawn('ls')")
        report = validator.validate(script)
        assert report.verdict == ValidationVerdict.QUARANTINED
        assert "process_spawn" in report.reason

    def test_validate_quota_exceeded_quarantined(self):
        from cohezion.vanguard.sandbox_validation import SandboxScript, SubstrateSandbox, ValidationVerdict

        validator = SubstrateSandbox(gtt_quota_bytes=1024)
        script = SandboxScript(script_id="fat_s1", source_url="http://fat.com", code="x = 1", requested_bytes=2048)
        report = validator.validate(script)
        assert report.verdict == ValidationVerdict.QUARANTINED
        assert "exceeds quota" in report.reason

    def test_results_returns_list(self):
        from cohezion.vanguard.sandbox_validation import SandboxScript, SubstrateSandbox

        validator = SubstrateSandbox()
        script = SandboxScript(script_id="s1", source_url="http://x.com", code="x = 1")
        validator.validate(script)
        results = validator.results()
        assert len(results) == 1
        assert results[0]["script_id"] == "s1"

    def test_quarantine_count_property(self):
        from cohezion.vanguard.sandbox_validation import SandboxScript, SubstrateSandbox

        validator = SubstrateSandbox()
        validator.validate(SandboxScript(script_id="ok", source_url="u", code="x=1"))
        validator.validate(SandboxScript(script_id="bad", source_url="u", code="shell_invoke('rm -rf')"))
        assert validator.quarantine_count == 1

    def test_scan_for_unsafe_patterns(self):
        from cohezion.vanguard.sandbox_validation import SubstrateSandbox

        validator = SubstrateSandbox()
        assert validator._scan_for_unsafe_patterns("x = dynamic_import('sys')") == "dynamic_import"
        assert validator._scan_for_unsafe_patterns("x = 1 + 2") is None


# ---------------------------------------------------------------------------
# Module 3: physics/mhd_mereon.py
# ---------------------------------------------------------------------------


class TestMHDMereon:
    def _make_operator(self):
        from cohezion.physics.mhd_mereon import MHDMereonOperator

        mock_projector = MagicMock()
        # project returns a 12D vector
        mock_projector.project.return_value = np.random.randn(12)
        return MHDMereonOperator(projector=mock_projector)

    def test_get_regime_modulation_inside_focus(self):
        op = self._make_operator()
        # Position inside focusing sphere (r < 3.078)
        pos = np.array([1.0, 0.0, 0.0])
        mod = op.get_regime_modulation(pos)
        assert isinstance(mod, float)

    def test_get_regime_modulation_at_focus(self):
        op = self._make_operator()
        # Position at focusing sphere (r = 3.078)
        pos = np.array([3.078, 0.0, 0.0])
        mod = op.get_regime_modulation(pos)
        assert isinstance(mod, float)

    def test_get_regime_modulation_outside_focus(self):
        op = self._make_operator()
        pos = np.array([10.0, 0.0, 0.0])
        mod = op.get_regime_modulation(pos)
        assert isinstance(mod, float)

    def test_mhd_state_namedtuple(self):
        from cohezion.physics.mhd_mereon import MHDState

        state = MHDState(
            velocity=np.array([1.0, 0.0, 0.0]),
            magnetic_field=np.array([0.0, 1.0, 0.0]),
            pressure=1.0,
            density=1.0,
        )
        assert state.pressure == pytest.approx(1.0)

    def test_operator_has_projector(self):
        op = self._make_operator()
        assert op.projector is not None

    def test_mhd_operator_default_constants(self):
        op = self._make_operator()
        assert op.focusing_sphere_radius == pytest.approx(3.078)
        assert op.conductance_boost == pytest.approx(10.0)
