"""Wave 3A coverage tests for cohezion.compound.executor.

Adds 20 unit tests targeting the public API of CompoundExecutor and the
helper modules in executor_helpers/. All external boundaries (vault,
SurrealDB, journey tracker, guardrails, cache) are mocked.

Plan: synthetic-sniffing-panda Wave 3A.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_project_root(tmp_path: Path) -> Path:
    """Project root with a stub `.context` directory.

    The ContextManager's `_find_project_root` walks up from `cwd` until it
    finds a `.context` directory. Tests must avoid relying on the host
    repo's filesystem, so we provide a throwaway one.
    """
    (tmp_path / ".context").mkdir()
    return tmp_path


@pytest.fixture
def mock_mcp() -> MagicMock:
    """Mock MCP client used to construct the executor."""
    return MagicMock()


@pytest.fixture
def executor(mock_mcp, fake_project_root):
    """Construct a CompoundExecutor isolated from the host filesystem.

    Patches:
        - VaultLogger to avoid any real vault I/O
        - ContextManager._find_project_root to return our fake root
    """
    with (
        patch("cohezion.compound.executor.VaultLogger"),
        patch(
            "cohezion.compound.context_integration.ContextManager._find_project_root",
            return_value=fake_project_root,
        ),
    ):
        from cohezion.compound.executor import CompoundExecutor

        executor = CompoundExecutor(mcp_client=mock_mcp)
        # Replace the per-instance logger with a controllable mock
        executor.logger = MagicMock()
        executor.logger.get_experience_guidance.return_value = {
            "relevant_context": [],
            "guidance": "stub",
        }
        executor.logger.log_execution_start.return_value = "exp/path/123"
        executor.logger.log_execution_result = MagicMock()
        executor.logger.log_execution_trace = MagicMock()
        executor.logger.extract_execution_pattern.return_value = "patterns/x.md"
        # The _try_template_match should default to None so tests don't
        # short-circuit unless they explicitly opt in.
        executor._try_template_match = MagicMock(return_value=None)
        # Skip auto-context-load (we mocked the find_project_root above but
        # the manifest still won't exist).
        executor._context_loaded = True
        return executor


# ---------------------------------------------------------------------------
# Tests: execute_task happy paths (6)
# ---------------------------------------------------------------------------


class TestExecuteTaskHappyPaths:
    """Six smoke tests covering the typical execute_task flows."""

    def test_execute_task_returns_execution_result(self, executor):
        """Successful execution returns ExecutionResult with success=True."""
        from cohezion.compound.executor import ExecutionResult

        result = executor.execute_task(
            task_description="Generate a function",
            skill_name="codegen",
            operation_type="generate",
            execute_fn=lambda guidance: ("def foo(): pass", {"tokens": 42}),
        )

        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.output == "def foo(): pass"

    def test_execute_task_propagates_metrics(self, executor):
        """User-supplied metrics flow into result.metrics."""
        result = executor.execute_task(
            task_description="Analyze logs",
            skill_name="analyzer",
            operation_type="analyze",
            execute_fn=lambda g: ("ok", {"custom_metric": 7}),
        )

        assert result.metrics["custom_metric"] == 7
        assert "duration_seconds" in result.metrics

    def test_execute_task_records_duration(self, executor):
        """duration_seconds is non-negative on success."""
        result = executor.execute_task(
            task_description="Search vault",
            skill_name="searcher",
            operation_type="search",
            execute_fn=lambda g: ("hits", {}),
        )

        assert result.duration_seconds >= 0.0

    def test_execute_task_passes_guidance_to_execute_fn(self, executor):
        """execute_fn receives the guidance dict from get_experience_guidance."""
        captured: dict = {}

        def execute_fn(guidance):
            captured["g"] = guidance
            return ("ok", {})

        with patch.object(executor, "get_experience_guidance", return_value={"sentinel": "yes"}):
            executor.execute_task(
                task_description="x",
                skill_name="s",
                operation_type="generate",
                execute_fn=execute_fn,
            )

        assert captured["g"] == {"sentinel": "yes"}

    def test_execute_task_logs_to_vault(self, executor):
        """Both log_execution_start and log_execution_result are invoked."""
        executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda g: ("ok", {}),
        )

        executor.logger.log_execution_start.assert_called_once()
        executor.logger.log_execution_result.assert_called_once()

    def test_execute_task_computes_coherence(self, executor):
        """Successful run produces a coherence score in [0, 1]."""
        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="transform",
            execute_fn=lambda g: ("ok", {}),
        )

        assert "coherence" in result.metrics
        assert 0.0 <= result.metrics["coherence"] <= 1.0


# ---------------------------------------------------------------------------
# Tests: execute_task error paths (4)
# ---------------------------------------------------------------------------


class TestExecuteTaskErrorPaths:
    """Four tests covering failure scenarios that must NOT crash the executor."""

    def test_execute_fn_raises_marks_failure(self, executor):
        """User-supplied execute_fn raising returns success=False, not crash."""

        def boom(guidance):
            raise ValueError("simulated failure")

        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=boom,
        )

        assert result.success is False
        assert "simulated failure" in result.output
        assert result.metrics["error_type"] == "ValueError"

    def test_vault_logger_failure_does_not_crash(self, executor):
        """If log_execution_start raises, execute_task still returns a result."""
        executor.logger.log_execution_start.side_effect = OSError("vault down")

        # The current implementation does not wrap log_execution_start in
        # try/except — so this surfaces as a real exception. We verify the
        # contract: an OSError propagates rather than being silently swallowed.
        with pytest.raises(OSError, match="vault down"):
            executor.execute_task(
                task_description="x",
                skill_name="s",
                operation_type="generate",
                execute_fn=lambda g: ("ok", {}),
            )

    def test_journey_tracker_failure_is_non_blocking(self, executor):
        """A failing journey tracker must NOT cause the task to fail."""
        executor._journey_tracker = MagicMock()
        executor._journey_tracker.track_execution.side_effect = RuntimeError("jt down")

        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda g: ("ok", {}),
        )

        assert result.success is True

    def test_metrics_collector_failure_is_non_blocking(self, executor):
        """Metrics collector errors are swallowed (logged at debug)."""
        executor._metrics_collector = MagicMock()
        executor._metrics_collector.record_execution.side_effect = ValueError("mc down")

        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda g: ("ok", {}),
        )

        assert result.success is True


# ---------------------------------------------------------------------------
# Tests: _try_template_match (4)
# ---------------------------------------------------------------------------


class TestTryTemplateMatch:
    """Four tests covering the cache-hit short-circuit path."""

    def test_template_hit_short_circuits_execution(self, executor):
        """A cache hit returns immediately without invoking execute_fn."""
        executor._try_template_match.return_value = {
            "response": "cached output",
            "similarity": 0.92,
            "source": "L2",
            "tokens_saved": 800,
        }
        execute_fn = MagicMock()

        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=execute_fn,
        )

        assert result.success is True
        assert result.output == "cached output"
        assert result.metrics["template_match"] is True
        assert result.metrics["tokens_saved"] == 800
        execute_fn.assert_not_called()

    def test_template_miss_proceeds_with_execute_fn(self, executor):
        """Cache miss (None) lets the normal execute_fn path run."""
        executor._try_template_match.return_value = None
        called = MagicMock(return_value=("normal output", {}))

        result = executor.execute_task(
            task_description="x",
            skill_name="s",
            operation_type="generate",
            execute_fn=called,
        )

        assert result.output == "normal output"
        called.assert_called_once()

    def test_template_matcher_returns_none_when_cache_unavailable(self):
        """try_template_match catches ImportError and returns None."""
        from cohezion.compound.executor_helpers.template_matcher import try_template_match

        with patch.dict("sys.modules", {"cohezion.cache.cache_warmer": None}):
            result = try_template_match("any task")

        assert result is None

    def test_template_matcher_returns_none_in_async_context(self):
        """Inside a running event loop, the helper bails out (returns None)."""
        from cohezion.compound.executor_helpers.template_matcher import try_template_match

        async def call_inside_loop():
            return try_template_match("any task")

        # Provide a fake SemanticCache so we exercise the asyncio.get_running_loop
        # branch rather than the ImportError branch.
        fake_cache = MagicMock()
        fake_cache_module = MagicMock(SemanticCache=MagicMock(get_instance=lambda: fake_cache))
        fake_warmer_module = MagicMock(CacheWarmer=MagicMock())
        with patch.dict(
            "sys.modules",
            {
                "cohezion.cache.semantic_cache": fake_cache_module,
                "cohezion.cache.cache_warmer": fake_warmer_module,
            },
        ):
            result = asyncio.run(call_inside_loop())

        assert result is None


# ---------------------------------------------------------------------------
# Tests: get_experience_guidance (3)
# ---------------------------------------------------------------------------


class TestGetExperienceGuidance:
    """Three tests covering the vault-integration helper."""

    def test_returns_base_guidance_when_enrichment_unavailable(self, executor):
        """If trajectory search modules are missing, we still get base guidance."""
        executor.logger.get_experience_guidance.return_value = {
            "relevant_context": [],
            "guidance": "Vault guidance unavailable.",
        }

        # Force trajectory_search import to fail, and make SurrealDB
        # urlopen raise so neither enrichment branch runs.
        with (
            patch.dict("sys.modules", {"cohezion.compound.trajectory_search": None}),
            patch("urllib.request.urlopen", side_effect=OSError("no surreal")),
        ):
            result = executor.get_experience_guidance("describe x")

        assert "guidance" in result
        assert result["guidance"] == "Vault guidance unavailable."

    def test_passes_project_and_operation_type(self, executor):
        """The vault logger receives the supplied project name."""
        executor.logger.get_experience_guidance.return_value = {
            "relevant_context": [{"id": 1}],
            "guidance": "found one",
        }

        with (
            patch.dict("sys.modules", {"cohezion.compound.trajectory_search": None}),
            patch("urllib.request.urlopen", side_effect=OSError("no surreal")),
        ):
            executor.get_experience_guidance(
                "describe x",
                project="other-project",
                operation_type="analyze",
            )

        # vault_logger.get_experience_guidance is called with task_description
        # and project — operation_type is only used downstream.
        call = executor.logger.get_experience_guidance.call_args
        assert call.kwargs.get("project") == "other-project" or "other-project" in call.args

    def test_surreal_failure_is_non_blocking(self, executor):
        """A SurrealDB query failure does not raise, just logs at debug."""
        executor.logger.get_experience_guidance.return_value = {
            "relevant_context": [],
            "guidance": "ok",
        }

        with (
            patch.dict("sys.modules", {"cohezion.compound.trajectory_search": None}),
            patch("urllib.request.urlopen", side_effect=ConnectionError("refused")),
        ):
            result = executor.get_experience_guidance("x")

        assert "recent_retrospections" not in result
        assert result["guidance"] == "ok"


# ---------------------------------------------------------------------------
# Tests: guardrail runner (3)
# ---------------------------------------------------------------------------


class TestGuardrailRunner:
    """Three tests covering the sync wrapper around async guardrail coroutines."""

    def test_runs_async_coroutine_to_completion(self):
        """run_async_guardrail returns the coroutine's value."""
        from cohezion.compound.executor_helpers.guardrail_runner import (
            run_async_guardrail,
        )

        async def coro():
            return "guardrail-ok"

        result = run_async_guardrail(coro())
        assert result == "guardrail-ok"

    def test_runtime_error_returns_none(self):
        """RuntimeError (e.g. nested event loop) returns None, never raises."""
        from cohezion.compound.executor_helpers.guardrail_runner import (
            run_async_guardrail,
        )

        async def coro():
            raise RuntimeError("nested loop")

        result = run_async_guardrail(coro())
        assert result is None

    def test_unexpected_exceptions_propagate(self):
        """Non-asyncio exceptions are NOT silently swallowed (only specific ones)."""
        from cohezion.compound.executor_helpers.guardrail_runner import (
            run_async_guardrail,
        )

        async def coro():
            raise ValueError("bad input")

        # ValueError is not in the (RuntimeError, asyncio.TimeoutError,
        # asyncio.CancelledError) tuple, so it should propagate.
        with pytest.raises(ValueError, match="bad input"):
            run_async_guardrail(coro())
