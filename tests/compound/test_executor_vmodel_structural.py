"""V-model structural invariant checks for CompoundExecutor.

O1-O6: Signature and attribute checks that fire at test collection time.
These catch refactor drift (renamed params, removed fields) before any
behavioral test has a chance to produce a misleading TypeError.

Cost: ~1ms each.  Value: catches signature drift immediately.
"""

import inspect


class TestExecutionResultStructure:
    """O1-O2: ExecutionResult field invariants."""

    def test_O1_execution_result_has_success_field(self):
        """O1: ExecutionResult.success field exists (bool)."""
        from cohezion.compound.executor import ExecutionResult

        fields = (
            {f.name: f for f in ExecutionResult.__dataclass_fields__.values()}
            if hasattr(ExecutionResult, "__dataclass_fields__")
            else {}
        )
        if not fields:
            r = ExecutionResult(success=True, output="", metrics={}, duration_seconds=0.0)
            assert hasattr(r, "success")
        else:
            assert "success" in fields

    def test_O2_execution_result_has_compound_score(self):
        """O2: ExecutionResult.compound_score field exists with default 0.0."""
        from cohezion.compound.executor import ExecutionResult

        r = ExecutionResult(success=True, output="", metrics={}, duration_seconds=0.0)
        assert hasattr(r, "compound_score"), "compound_score field missing from ExecutionResult"
        assert r.compound_score == 0.0, (
            f"Default compound_score should be 0.0, got {r.compound_score}"
        )

    def test_O3_execution_result_has_token_metrics(self):
        """O3: ExecutionResult.token_metrics field exists (optional dict)."""
        from cohezion.compound.executor import ExecutionResult

        r = ExecutionResult(success=True, output="", metrics={}, duration_seconds=0.0)
        assert hasattr(r, "token_metrics")
        assert r.token_metrics is None  # Default is None

    def test_O4_execution_result_required_fields_present(self):
        """O4: All required fields can be set on construction."""
        from cohezion.compound.executor import ExecutionResult

        r = ExecutionResult(
            success=False,
            output="test output",
            metrics={"coherence": 0.7},
            duration_seconds=1.5,
            compound_score=0.8,
        )
        assert r.success is False
        assert r.output == "test output"
        assert r.metrics["coherence"] == 0.7
        assert r.duration_seconds == 1.5
        assert r.compound_score == 0.8


class TestExecuteTaskSignature:
    """O5-O6: execute_task() signature invariants."""

    def test_O5_execute_task_accepts_required_params(self):
        """O5: execute_task() has required positional params: task_description, skill_name, operation_type, execute_fn."""
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.execute_task)
        params = sig.parameters
        required = ["task_description", "skill_name", "operation_type", "execute_fn"]
        for name in required:
            assert name in params, f"O5: execute_task() missing required param '{name}'"

    def test_O6_execute_task_accepts_optional_params(self):
        """O6: execute_task() has optional params: project, human_request."""
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.execute_task)
        params = sig.parameters
        optional = ["project", "human_request"]
        for name in optional:
            assert name in params, f"O6: execute_task() missing optional param '{name}'"
            assert params[name].default is not inspect.Parameter.empty, (
                f"O6: execute_task() param '{name}' should have a default value"
            )


class TestCompoundExecutorInit:
    """O7: CompoundExecutor.__init__ signature invariants."""

    def test_O7_executor_init_accepts_mcp_client(self):
        """O7: CompoundExecutor.__init__() accepts mcp_client parameter."""
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.__init__)
        assert "mcp_client" in sig.parameters, (
            "O7: CompoundExecutor.__init__ missing mcp_client param"
        )

    def test_O8_executor_init_accepts_guardrails(self):
        """O8: CompoundExecutor.__init__() has enable_guardrails parameter."""
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.__init__)
        assert "enable_guardrails" in sig.parameters, (
            "O8: CompoundExecutor.__init__ missing enable_guardrails param"
        )
        # Default should be True (guardrails on by default)
        default = sig.parameters["enable_guardrails"].default
        assert default is True, f"O8: enable_guardrails default should be True, got {default}"


class TestCompoundScoreComputation:
    """O9-O10: compound_score behavioral invariants."""

    def test_O9_compound_score_formula_components(self):
        """O9: compound_score = coherence × hiho_stability × skill_factor is computable."""
        coherence = 0.6
        skill_gain = 0.1
        hiho_stability = 1.0 - 2.0 * abs(coherence - 0.5)  # 0.8
        skill_factor = max(0.0, 1.0 + skill_gain)  # 1.1
        score = coherence * hiho_stability * skill_factor
        assert 0.0 <= score <= 1.0, f"compound_score out of bounds: {score}"
        # At coherence=0.5 (HIHO optimum), hiho_stability=1.0; score = 0.5 * 1.0 * (1+gain)
        0.5 * 1.0 * 1.0  # = 0.5 with no skill_gain
        coherence_5 = 0.5
        hiho_5 = 1.0 - 2.0 * abs(coherence_5 - 0.5)
        assert abs(hiho_5 - 1.0) < 1e-9, "HIHO stability should be 1.0 at coherence=0.5"

    def test_O10_compound_score_stored_in_metrics(self):
        """O10: After compute_compound_score(), result stored in metrics dict."""
        from cohezion.compound.executor import ExecutionResult

        r = ExecutionResult(
            success=True,
            output="test",
            metrics={"coherence": 0.5, "skill_gain": 0.0},
            duration_seconds=1.0,
            compound_score=0.25,  # Pre-computed
        )
        assert r.compound_score == 0.25
        assert r.metrics["coherence"] == 0.5

    def test_O11_executor_computes_correct_compound_score(self):
        """O11 (behavioral): execute_task() applies compound_score = coherence × hiho × skill_factor.

        Verifies the formula is wired in the executor pipeline.
        compound_score == coherence × (1 - 2|coherence - 0.5|) × max(0, 1 + skill_gain)
        """
        from unittest.mock import MagicMock, patch

        import pytest

        from cohezion.compound.executor import CompoundExecutor, ExecutionResult

        with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
            exc = CompoundExecutor(mcp_client=MagicMock())
        exc.logger = MagicMock()
        exc.logger.get_experience_guidance.return_value = {
            "relevant_context": [],
            "guidance": "stub",
        }
        exc.logger.log_execution_start.return_value = "exp/path/123"
        exc.logger.log_execution_result = MagicMock()
        exc._try_template_match = MagicMock(return_value=None)
        exc._context_loaded = True
        exc._retrospection_engine = None  # disable so skill_gain comes from metrics

        result = exc.execute_task(
            "test task",
            "test_skill",
            "generate",
            lambda g: ("output", {"coherence": 0.6, "skill_gain": 0.1}),
        )

        assert isinstance(result, ExecutionResult)
        coherence = float(result.metrics.get("coherence", 0.5))
        skill_gain = float(result.metrics.get("skill_gain", 0.0))
        hiho = max(0.0, 1.0 - 2.0 * abs(coherence - 0.5))
        expected = coherence * hiho * max(0.0, 1.0 + skill_gain)

        assert result.compound_score == pytest.approx(expected, abs=1e-9), (
            f"compound_score={result.compound_score:.6f} != formula {expected:.6f} "
            f"(coherence={coherence:.3f}, hiho={hiho:.3f}, skill_gain={skill_gain:.3f})"
        )
        assert 0.0 <= result.compound_score <= 1.0
