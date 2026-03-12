"""Tests for Substrate Governor & Temporal Dilation (Story 1.3, NFR-5)."""

from __future__ import annotations

from cohezion.core.substrate_governor import (
    PressureLevel,
    SubstrateGovernor,
)


class TestSubstrateGovernor:
    def test_normal_pressure_no_dilation(self):
        """Pressure below 90% doesn't trigger dilation."""
        gov = SubstrateGovernor()
        state = gov.update_pressure(0.5)
        assert state.factor == 1.0
        assert state.level == PressureLevel.NORMAL

    def test_elevated_pressure_triggers_dilation(self):
        """Pressure above 90% triggers graduated dilation."""
        gov = SubstrateGovernor()
        state = gov.update_pressure(0.92)
        assert state.factor > 1.0
        assert state.level == PressureLevel.ELEVATED

    def test_critical_pressure_max_dilation(self):
        """Pressure above 95% triggers max dilation + emergency eviction."""
        gov = SubstrateGovernor()
        state = gov.update_pressure(0.96)
        assert state.factor == 10.0
        assert state.level == PressureLevel.CRITICAL

    def test_graduated_dilation_scales(self):
        """Dilation factor scales linearly between thresholds."""
        gov1 = SubstrateGovernor()
        gov2 = SubstrateGovernor()
        state1 = gov1.update_pressure(0.91)
        state2 = gov2.update_pressure(0.94)
        assert state2.factor > state1.factor

    def test_recovery_removes_dilation(self):
        """Pressure dropping below recovery target removes dilation."""
        gov = SubstrateGovernor()
        gov.update_pressure(0.92)  # Trigger dilation
        assert gov.state.factor > 1.0
        gov.update_pressure(0.80)  # Recovery
        assert gov.state.factor == 1.0
        assert gov.state.level == PressureLevel.NORMAL

    def test_pulse_interval_dilated(self):
        """Pulse interval increases with dilation."""
        gov = SubstrateGovernor()
        normal = gov.get_pulse_interval(100.0)
        assert normal == 100.0

        gov.update_pressure(0.92)
        dilated = gov.get_pulse_interval(100.0)
        assert dilated > 100.0

    def test_events_logged(self):
        """Governor events are tracked."""
        gov = SubstrateGovernor()
        gov.update_pressure(0.92)
        gov.update_pressure(0.96)
        gov.update_pressure(0.80)
        assert len(gov.events) == 3

    def test_state_serialization(self):
        """DilationState serializes to dict."""
        gov = SubstrateGovernor()
        gov.update_pressure(0.92)
        d = gov.state.to_dict()
        assert "factor" in d
        assert "level" in d
