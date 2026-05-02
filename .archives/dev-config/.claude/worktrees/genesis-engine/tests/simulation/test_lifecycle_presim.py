"""Tests for Lifecycle Pre-Simulation (Story 5.8, FR19)."""

from __future__ import annotations

import numpy as np

from cohezion.simulation.lifecycle_presim import (
    LifecyclePreSimulator,
    SimulationStep,
)


def _make_step(phase: str, coherence: float, position: list[float] | None = None) -> SimulationStep:
    pos = position or np.random.default_rng(hash(phase) % 2**31).standard_normal(12).tolist()
    return SimulationStep(phase=phase, position=pos, coherence=coherence)


class TestLifecyclePreSimulator:
    def test_smooth_trajectory_passes(self):
        """A trajectory with no coherence drops passes."""
        sim = LifecyclePreSimulator()
        steps = [_make_step("requirement", 0.8, [float(i)] * 12) for i in range(4)]
        result = sim.simulate("plan-1", steps)
        assert result.passed

    def test_coherence_drop_detected(self):
        """Significant coherence drop is flagged as blocking."""
        sim = LifecyclePreSimulator(coherence_threshold=0.1)
        steps = [
            _make_step("requirement", 0.8, [0.0] * 12),
            _make_step("architecture", 0.5, [1.0] * 12),  # Drop of 0.3
        ]
        result = sim.simulate("plan-2", steps)
        assert not result.passed
        assert len(result.coherence_drops) == 1

    def test_topological_knot_detected(self):
        """Self-intersecting trajectory is flagged."""
        sim = LifecyclePreSimulator(knot_threshold=0.5)
        # Steps 0 and 2 are at same position (knot)
        steps = [
            _make_step("requirement", 0.8, [0.0] * 12),
            _make_step("architecture", 0.8, [5.0] * 12),  # Far away
            _make_step("code", 0.8, [0.01] * 12),  # Very close to step 0
        ]
        result = sim.simulate("plan-3", steps)
        assert not result.passed
        assert len(result.knots) == 1

    def test_blocking_errors_describe_issues(self):
        """Blocking errors have descriptive messages."""
        sim = LifecyclePreSimulator(coherence_threshold=0.1)
        steps = [
            _make_step("req", 0.9, [0.0] * 12),
            _make_step("arch", 0.5, [1.0] * 12),
        ]
        result = sim.simulate("plan-4", steps)
        assert any("Coherence drop" in e for e in result.blocking_errors)

    def test_adjacent_steps_not_flagged_as_knots(self):
        """Adjacent steps are not checked for knots (only skip >= 2)."""
        sim = LifecyclePreSimulator(knot_threshold=10.0)
        steps = [
            _make_step("a", 0.8, [0.0] * 12),
            _make_step("b", 0.8, [0.01] * 12),  # Very close but adjacent
        ]
        result = sim.simulate("plan-5", steps)
        assert len(result.knots) == 0

    def test_serialization(self):
        """Result serializes to dict."""
        sim = LifecyclePreSimulator()
        steps = [_make_step("req", 0.8, [float(i)] * 12) for i in range(3)]
        result = sim.simulate("plan-6", steps)
        d = result.to_dict()
        assert d["plan_id"] == "plan-6"
        assert "passed" in d

    def test_empty_plan_passes(self):
        """Empty plan trivially passes."""
        sim = LifecyclePreSimulator()
        result = sim.simulate("empty", [])
        assert result.passed
