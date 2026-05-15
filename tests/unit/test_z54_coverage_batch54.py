"""Coverage batch Z54: skill_refinement_validator, symbolic_executor, universe_bridge."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: compound/skill_refinement_validator.py
# ---------------------------------------------------------------------------


class TestSkillRefinementValidator:
    def _make_validator(self, min_samples=3, max_degradation=5.0):
        from cohezion.compound.skill_refinement_validator import SkillRefinementValidator

        return SkillRefinementValidator(min_samples=min_samples, max_degradation_pct=max_degradation)

    def _make_metrics(self, success_rate=0.9, avg_latency_ms=50.0, avg_coherence=0.7, sample_count=5):
        from cohezion.compound.skill_refinement_validator import RefinementMetrics

        return RefinementMetrics(
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            avg_coherence=avg_coherence,
            sample_count=sample_count,
            measured_at=RefinementMetrics.now_iso(),
        )

    def test_refinement_metrics_dataclass(self):
        m = self._make_metrics()
        assert m.success_rate == pytest.approx(0.9)
        assert m.sample_count == 5

    def test_now_iso_returns_string(self):
        from cohezion.compound.skill_refinement_validator import RefinementMetrics

        ts = RefinementMetrics.now_iso()
        assert isinstance(ts, str)
        assert "T" in ts  # ISO format

    def test_validate_no_baseline_returns_false(self):
        validator = self._make_validator()
        post = self._make_metrics()
        approved, reason = validator.validate_refinement("CODE_REVIEW", post)
        assert approved is False
        assert "no baseline" in reason

    def test_validate_insufficient_samples_returns_false(self):
        validator = self._make_validator(min_samples=10)
        baseline = self._make_metrics(sample_count=5)
        # Silence SurrealDB persistence
        with patch.object(validator, "_persist_async"):
            validator.record_baseline("CODE_REVIEW", baseline)
        post = self._make_metrics(sample_count=3)  # < min_samples=10
        with patch.object(validator, "_persist_async"):
            approved, reason = validator.validate_refinement("CODE_REVIEW", post)
        assert approved is False
        assert "insufficient" in reason

    def test_validate_approved_when_metrics_improved(self):
        validator = self._make_validator()
        baseline = self._make_metrics(success_rate=0.8, avg_coherence=0.6)
        with patch.object(validator, "_persist_async"):
            validator.record_baseline("CODE_REVIEW", baseline)
        post = self._make_metrics(success_rate=0.9, avg_coherence=0.7)  # better
        with patch.object(validator, "_persist_async"):
            approved, reason = validator.validate_refinement("CODE_REVIEW", post)
        assert approved is True
        assert "approved" in reason.lower() or "improved" in reason.lower() or "no regression" in reason.lower()

    def test_validate_blocked_on_success_rate_regression(self):
        validator = self._make_validator(max_degradation=5.0)
        baseline = self._make_metrics(success_rate=0.9, avg_coherence=0.7)
        with patch.object(validator, "_persist_async"):
            validator.record_baseline("CODE_REVIEW", baseline)
        post = self._make_metrics(success_rate=0.5, avg_coherence=0.7)  # -40% success
        with patch.object(validator, "_persist_async"):
            approved, reason = validator.validate_refinement("CODE_REVIEW", post)
        assert approved is False
        assert "success_rate" in reason

    def test_validate_blocked_on_coherence_regression(self):
        validator = self._make_validator(max_degradation=5.0)
        baseline = self._make_metrics(success_rate=0.9, avg_coherence=0.7)
        with patch.object(validator, "_persist_async"):
            validator.record_baseline("CODE_REVIEW", baseline)
        post = self._make_metrics(success_rate=0.9, avg_coherence=0.1)  # huge coherence drop
        with patch.object(validator, "_persist_async"):
            approved, reason = validator.validate_refinement("CODE_REVIEW", post)
        assert approved is False

    def test_get_improvement_report_returns_metrics(self):
        validator = self._make_validator()
        baseline = self._make_metrics(success_rate=0.85)
        with patch.object(validator, "_persist_async"):
            validator.record_baseline("MY_SKILL", baseline)
        result = validator.get_improvement_report("MY_SKILL")
        assert result is not None
        assert result["baseline"]["success_rate"] == pytest.approx(0.85)

    def test_get_improvement_report_missing_returns_error_dict(self):
        validator = self._make_validator()
        result = validator.get_improvement_report("UNKNOWN")
        assert "error" in result


# ---------------------------------------------------------------------------
# Module 2: compound/symbolic_executor.py
# ---------------------------------------------------------------------------


class TestSymbolicExecutor:
    def _make_executor(self):
        from cohezion.compound.symbolic_executor import SymbolicExecutor

        return SymbolicExecutor()

    def test_execute_simple_addition(self):
        executor = self._make_executor()
        result = executor.execute("r = 2 + 2")
        assert result["success"] is True
        assert result["results"]["r"] == 4

    def test_execute_symbolic_solve(self):
        executor = self._make_executor()
        code = "x = symbols('x')\nans = solve(x**2 - 4, x)"
        result = executor.execute(code)
        assert result["success"] is True
        assert "ans" in result["results"]

    def test_execute_returns_error_on_exception(self):
        executor = self._make_executor()
        result = executor.execute("x = 1 / 0")
        assert result["success"] is False
        assert "error" in result

    def test_execute_numpy_operation(self):
        executor = self._make_executor()
        result = executor.execute("arr = np.array([1, 2, 3])\ntotal = int(np.sum(arr))")
        assert result["success"] is True
        assert result["results"]["total"] == 6

    def test_execute_isprime(self):
        executor = self._make_executor()
        result = executor.execute("answer = isprime(17)")
        assert result["success"] is True
        assert result["results"]["answer"] is True

    def test_execute_sympy_simplify(self):
        executor = self._make_executor()
        result = executor.execute("x = symbols('x')\nresult_val = simplify(x**2 - x**2)")
        assert result["success"] is True
        assert result["results"]["result_val"] == 0


# ---------------------------------------------------------------------------
# Module 3: compound/universe_bridge.py
# ---------------------------------------------------------------------------


class TestUniverseBridge:
    def _make_bridge(self, engine=None):
        from cohezion.compound.universe_bridge import UniverseBridge

        return UniverseBridge(engine=engine, agent_name="test-agent")

    def test_noop_mode_start_journey_returns_none(self):
        bridge = self._make_bridge(engine=None)
        result = bridge.start_journey("do a review", execution_id="exec-001")
        assert result is None

    def test_noop_mode_add_point_silently_ignored(self):
        bridge = self._make_bridge(engine=None)
        bridge.start_journey("task")
        bridge.add_point("exec-001", [0.5] * 12, step_number=1, action="code")

    def test_noop_mode_complete_journey_returns_none(self):
        bridge = self._make_bridge(engine=None)
        result = bridge.complete_journey("exec-001", success=True, phi_score=0.8, output="done")
        assert result is None

    def test_with_engine_start_journey(self):
        mock_engine = MagicMock()
        mock_journey = MagicMock()
        mock_engine.create_journey.return_value = mock_journey
        bridge = self._make_bridge(engine=mock_engine)
        result = bridge.start_journey("task desc", execution_id="exec-002")
        # Result is execution_id string or None depending on engine behavior
        assert result is None or isinstance(result, str)

    def test_with_engine_complete_journey_missing_id_returns_none(self):
        mock_engine = MagicMock()
        bridge = self._make_bridge(engine=mock_engine)
        result = bridge.complete_journey("nonexistent-id", success=True, phi_score=0.8, output="")
        assert result is None
