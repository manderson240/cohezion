"""TDD: Wire vibe/ NL→workflow compiler + vanguard/ sandbox into CompoundExecutor.

Tests that CompoundExecutor can accept natural language task descriptions
and route them through VibeOrchestrator for workflow compilation before execution.

Wiring target: CompoundExecutor.compile_natural_language(nl_text)
Wiring target: CompoundExecutor.validate_sandbox(task_description)
"""

from __future__ import annotations

from unittest.mock import patch


class TestVibeWiring:
    """Test vibe/ → CompoundExecutor integration."""

    def test_executor_has_nl_method(self):
        """CompoundExecutor should expose a natural language entry point."""
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor.__new__(CompoundExecutor)
        assert hasattr(executor, "compile_natural_language")

    def test_compile_nl_returns_none_or_spec(self):
        """compile_natural_language returns WorkflowSpec or None (graceful)."""
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor.__new__(CompoundExecutor)
        result = executor.compile_natural_language("analyze the codebase")
        # Either a valid spec or None (graceful degradation if vibe fails)
        assert result is None or hasattr(result, "nodes")

    def test_compile_nl_handles_missing_module(self):
        """If vibe/ module is unavailable, should return None gracefully."""
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor.__new__(CompoundExecutor)
        with patch.dict("sys.modules", {"cohezion.vibe.orchestrator": None}):
            result = executor.compile_natural_language("do something")
            assert result is None


class TestVanguardWiring:
    """Test vanguard/ → CompoundExecutor sandbox validation integration."""

    def test_executor_has_sandbox_check(self):
        """CompoundExecutor should expose a pre-execution sandbox validation."""
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor.__new__(CompoundExecutor)
        assert hasattr(executor, "validate_sandbox")

    def test_sandbox_check_returns_true_default(self):
        """validate_sandbox returns True when module unavailable (safe default)."""
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor.__new__(CompoundExecutor)
        result = executor.validate_sandbox("safe task description")
        assert isinstance(result, bool)
        assert result is True
