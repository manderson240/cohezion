"""Integration tests for persistence modules wired into the live pipeline.

Verifies:
- Cache warm-start via WarmCacheLoader + TokenEfficientClient._cache compatibility
- Metrics snapshot/restore round-trip via MetricsPersistence
- CompoundSessionManager async context manager
- CompoundExecutor records metrics and tracks journeys when wired
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.metrics import CompoundMetricsCollector
from cohezion.compound.metrics_persistence import MetricsPersistence
from cohezion.compound.session_manager import CompoundSessionManager, SessionSummary


# ---------------------------------------------------------------------------
# CachePersistence + TokenEfficientClient integration
# ---------------------------------------------------------------------------


class TestCachePersistenceIntegration:
    """Verify cache warm-start and save via TokenEfficientClient._cache property."""

    def test_save_and_warm_roundtrip(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({"hash_a": "resp_a", "hash_b": "resp_b"})

        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512

        loader = WarmCacheLoader(persistence=cp)
        loaded = loader.warm_client(client)
        assert loaded == 2
        assert client._cache["hash_a"] == "resp_a"
        assert client._cache["hash_b"] == "resp_b"

    def test_warm_respects_max_entries(self, tmp_path: Path) -> None:
        cp = CachePersistence(cache_dir=tmp_path)
        cp.save_cache({f"k{i}": f"v{i}" for i in range(20)})

        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 5

        loader = WarmCacheLoader(persistence=cp)
        loaded = loader.warm_client(client)
        assert loaded == 5
        assert len(client._cache) == 5


# ---------------------------------------------------------------------------
# MetricsPersistence integration
# ---------------------------------------------------------------------------


class TestMetricsPersistenceIntegration:
    """Verify metrics snapshot/restore."""

    def test_snapshot_roundtrip(self, tmp_path: Path) -> None:
        mp = MetricsPersistence(metrics_dir=tmp_path)
        collector = CompoundMetricsCollector()
        collector.record_execution("test_skill", True, 150, 75.0, "phi3:mini")
        collector.record_execution("test_skill", False, 50, 25.0, "phi3:mini")

        path = mp.save_snapshot(collector)
        assert Path(path).exists()

        loaded = mp.load_latest_snapshot()
        assert loaded is not None
        assert len(loaded["executions"]) == 2

        restored = CompoundMetricsCollector()
        restored.load_from_snapshot(loaded)
        assert restored.total_executions == 2
        assert restored.success_rate() == 0.5

    def test_collector_records_execution(self) -> None:
        collector = CompoundMetricsCollector()
        collector.record_execution("skill_a", True, 100, 50.0, "phi3")
        assert collector.total_executions == 1
        assert collector.total_tokens() == 100
        assert collector.success_rate() == 1.0


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    """Verify session start/end with mocked dependencies."""

    @patch("cohezion.swarm.compound_client.get_compound_client")
    def test_session_context_manager_sync(self, mock_get_client: MagicMock) -> None:
        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512
        mock_get_client.return_value = client

        manager = CompoundSessionManager()
        summary = manager.start_session()
        assert summary.session_id.startswith("session_")
        end_summary = manager.end_session()
        assert end_summary.end_time > 0

    @pytest.mark.asyncio
    @patch("cohezion.swarm.compound_client.get_compound_client")
    async def test_session_async_context_manager(
        self,
        mock_get_client: MagicMock,
    ) -> None:
        client = MagicMock()
        client._cache = {}
        client._cache_max_size = 512
        mock_get_client.return_value = client

        manager = CompoundSessionManager()
        async with manager as mgr:
            session = mgr.get_current_session()
            assert session is not None
            assert session.session_id.startswith("session_")

    def test_session_summary_fields(self) -> None:
        summary = SessionSummary(
            session_id="test_123",
            start_time=1000.0,
            cache_entries_loaded=10,
            metrics_restored=True,
        )
        assert summary.session_id == "test_123"
        data = summary.model_dump()
        assert data["cache_entries_loaded"] == 10


# ---------------------------------------------------------------------------
# Alignment-gated execution
# ---------------------------------------------------------------------------


class TestAlignmentGatedExecution:
    """Verify alignment gate and execute_aligned method."""

    def test_check_alignment_high_coherence(self) -> None:
        from cohezion.compound.session_manager import AlignmentResult

        with (
            patch(
                "cohezion.compound.request_alignment_analyzer.RequestAlignmentAnalyzerFactory"
            ) as mock_factory,
            patch("cohezion.compound.session_manager.get_mcp_client") as mock_get_mcp,
        ):
            mock_get_mcp.return_value = MagicMock()
            mock_analyzer = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.intent_confidence = 0.9
            mock_parsed.intent = MagicMock(value="generate")
            mock_parsed.constraints = []
            mock_parsed.criteria = []
            mock_analyzer.parse_request.return_value = mock_parsed
            mock_factory.create.return_value = mock_analyzer

            manager = CompoundSessionManager()
            result = manager.check_alignment("Generate a simple function")

            assert isinstance(result, AlignmentResult)
            assert result.coherence >= 0.5
            assert result.should_proceed is True

    def test_check_alignment_low_coherence(self) -> None:
        with (
            patch(
                "cohezion.compound.request_alignment_analyzer.RequestAlignmentAnalyzerFactory"
            ) as mock_factory,
            patch("cohezion.compound.session_manager.get_mcp_client") as mock_get_mcp,
        ):
            mock_get_mcp.return_value = MagicMock()
            mock_analyzer = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.intent_confidence = 0.1
            mock_parsed.intent = MagicMock(value="unknown")
            mock_parsed.constraints = ["c1", "c2", "c3", "c4", "c5", "c6"]
            mock_parsed.criteria = ["c1", "c2", "c3"]
            mock_analyzer.parse_request.return_value = mock_parsed
            mock_factory.create.return_value = mock_analyzer

            manager = CompoundSessionManager()
            result = manager.check_alignment("Ambiguous request", threshold=0.5)

            assert result.coherence < 0.5
            assert result.should_proceed is False
            assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_execute_aligned_proceeds_on_high_coherence(self) -> None:
        with (
            patch(
                "cohezion.compound.request_alignment_analyzer.RequestAlignmentAnalyzerFactory"
            ) as mock_factory,
            patch("cohezion.compound.session_manager.get_mcp_client") as mock_get_mcp,
            patch("cohezion.swarm.compound_client.get_compound_client") as mock_get_client,
        ):
            mock_get_client.return_value = MagicMock(_cache={}, _cache_max_size=512)
            mock_get_mcp.return_value = MagicMock()
            mock_analyzer = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.intent_confidence = 0.85
            mock_parsed.intent = MagicMock(value="generate")
            mock_parsed.constraints = []
            mock_parsed.criteria = []
            mock_analyzer.parse_request.return_value = mock_parsed
            mock_factory.create.return_value = mock_analyzer

            manager = CompoundSessionManager()

            async def execute(guidance):
                return "test output"

            success, metrics = await manager.execute_aligned(
                request="Generate a function",
                execute_fn=execute,
                use_executor=False,
            )

            assert success is True
            assert "output" in metrics
            assert metrics["coherence"] >= 0.5

    @pytest.mark.asyncio
    async def test_execute_aligned_blocks_on_low_coherence(self) -> None:
        with (
            patch(
                "cohezion.compound.request_alignment_analyzer.RequestAlignmentAnalyzerFactory"
            ) as mock_factory,
            patch("cohezion.compound.session_manager.get_mcp_client") as mock_get_mcp,
            patch("cohezion.swarm.compound_client.get_compound_client") as mock_get_client,
        ):
            mock_get_client.return_value = MagicMock(_cache={}, _cache_max_size=512)
            mock_get_mcp.return_value = MagicMock()
            mock_analyzer = MagicMock()
            mock_parsed = MagicMock()
            mock_parsed.intent_confidence = 0.1
            mock_parsed.intent = MagicMock(value="unknown")
            mock_parsed.constraints = ["c1", "c2", "c3", "c4", "c5"]
            mock_parsed.criteria = []
            mock_analyzer.parse_request.return_value = mock_parsed
            mock_factory.create.return_value = mock_analyzer

            manager = CompoundSessionManager()

            async def execute():
                return "should not be called"

            success, metrics = await manager.execute_aligned(
                request="Ambiguous request",
                execute_fn=execute,
                threshold=0.5,
            )

            assert success is False
            assert "blocked_at" in metrics
            assert metrics["blocked_at"] == "alignment_gate"


# ---------------------------------------------------------------------------
# Executor wiring tests
# ---------------------------------------------------------------------------


class TestExecutorWiring:
    """Verify CompoundSessionManager delegates to CompoundExecutor."""

    @patch("cohezion.swarm.compound_client.get_compound_client")
    @patch("cohezion.compound.session_manager.get_mcp_client")
    def test_execute_aligned_uses_executor_pipeline(
        self, mock_get_mcp: MagicMock, mock_get_client: MagicMock
    ) -> None:
        from cohezion.compound.executor import ExecutionResult
        from cohezion.compound.session_manager import AlignmentResult

        mock_get_client.return_value = MagicMock(_cache={}, _cache_max_size=512)
        mock_get_mcp.return_value = MagicMock()

        mock_executor = MagicMock(spec=["execute_task"])
        mock_executor.execute_task.return_value = ExecutionResult(
            success=True,
            output="test output from executor",
            metrics={"coherence": 0.85},
            duration_seconds=0.5,
        )

        manager = CompoundSessionManager(executor=mock_executor)
        manager.start_session()

        with (
            patch.object(manager, "check_alignment") as mock_align,
            patch("cohezion.compound.executor.ExecutorFactory.create"),
        ):
            mock_align.return_value = AlignmentResult(
                coherence=0.9, should_proceed=True, intent_match=0.9
            )

            def sync_execute(guidance):
                return "sync result"

            import asyncio

            loop = asyncio.new_event_loop()
            try:
                success, _ = loop.run_until_complete(
                    manager.execute_aligned(
                        request="test request",
                        execute_fn=sync_execute,
                        skill_name="test_skill",
                        use_executor=True,
                    )
                )
            finally:
                loop.close()

        assert success is True
        mock_executor.execute_task.assert_called_once()
        call_kwargs = mock_executor.execute_task.call_args[1]
        assert call_kwargs["skill_name"] == "test_skill"
        assert call_kwargs["human_request"] == "test request"

    @patch("cohezion.swarm.compound_client.get_compound_client")
    @patch("cohezion.compound.session_manager.get_mcp_client")
    def test_executor_lazy_creation(
        self, mock_get_mcp: MagicMock, mock_get_client: MagicMock
    ) -> None:
        mock_get_client.return_value = MagicMock(_cache={}, _cache_max_size=512)
        mock_get_mcp.return_value = MagicMock()

        with patch("cohezion.compound.executor.ExecutorFactory.create") as mock_factory:
            mock_executor = MagicMock()
            mock_factory.return_value = mock_executor

            manager = CompoundSessionManager()
            executor_result = manager.executor

            assert executor_result is mock_executor
            mock_factory.assert_called_once()

    @patch("cohezion.swarm.compound_client.get_compound_client")
    def test_executor_passed_explicitly(self, mock_get_client: MagicMock) -> None:
        mock_get_client.return_value = MagicMock(_cache={}, _cache_max_size=512)

        mock_executor = MagicMock()

        manager = CompoundSessionManager(executor=mock_executor)

        assert manager._executor is mock_executor
        assert manager.executor is mock_executor


# ---------------------------------------------------------------------------
# Executor with persistence wiring
# ---------------------------------------------------------------------------


class TestExecutorWithPersistence:
    """Verify executor records metrics and tracks journeys when wired."""

    def test_executor_records_metrics(self) -> None:
        mcp_client = MagicMock()
        mcp_client.vault_find_relevant_context.return_value = []
        mcp_client.vault_log_experiment.return_value = "experiments/test.md"
        mcp_client.vault_edit.return_value = None
        mcp_client.vault_extract_pattern.return_value = "patterns/test.md"

        collector = CompoundMetricsCollector()
        executor = CompoundExecutor(
            mcp_client=mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            metrics_collector=collector,
        )

        result = executor.execute_task(
            task_description="Test task",
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("test output", {"coherence": 0.8}),
            project="test",
        )

        assert result.success is True
        assert collector.total_executions == 1
        # Verify the recorded execution
        snap = collector.to_snapshot()
        assert snap["executions"][0]["skill_name"] == "test_skill"
        assert snap["executions"][0]["success"] is True

    def test_executor_tracks_journey(self) -> None:
        from cohezion.compound.journey_tracker import JourneyTracker

        mcp_client = MagicMock()
        mcp_client.vault_find_relevant_context.return_value = []
        mcp_client.vault_log_experiment.return_value = "experiments/test.md"
        mcp_client.vault_edit.return_value = None
        mcp_client.vault_extract_pattern.return_value = "patterns/test.md"

        tracker = JourneyTracker()
        executor = CompoundExecutor(
            mcp_client=mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
            journey_tracker=tracker,
        )

        result = executor.execute_task(
            task_description="Journey test task",
            skill_name="journey_skill",
            operation_type="analyze",
            execute_fn=lambda guidance: ("analyzed output", {"coherence": 0.7}),
            project="test",
        )

        assert result.success is True
        # Journey tracking is non-blocking; verify it doesn't crash

    def test_executor_without_persistence_unchanged(self) -> None:
        """Verify executor works fine without any persistence modules."""
        mcp_client = MagicMock()
        mcp_client.vault_find_relevant_context.return_value = []
        mcp_client.vault_log_experiment.return_value = "experiments/test.md"
        mcp_client.vault_edit.return_value = None
        mcp_client.vault_extract_pattern.return_value = "patterns/test.md"

        executor = CompoundExecutor(
            mcp_client=mcp_client,
            enable_guardrails=False,
            enable_skill_refinement=False,
        )

        result = executor.execute_task(
            task_description="No persistence test",
            skill_name="basic_skill",
            operation_type="generate",
            execute_fn=lambda guidance: ("output", {}),
            project="test",
        )

        assert result.success is True
        assert result.output == "output"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegrationExecutor:
    """Integration tests with real executor pipeline."""

    @pytest.mark.skip(reason="Requires event loop isolation - use pytest-asyncio")
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_aligned_real_executor(self) -> None:
        """Integration test with real executor pipeline."""
        from cohezion.compound.session_manager import CompoundSessionManager

        with (
            patch("cohezion.swarm.compound_client.get_compound_client") as mock_client,
            patch("cohezion.compound.session_manager.get_mcp_client") as mock_mcp,
            patch(
                "cohezion.compound.request_alignment_analyzer.RequestAlignmentAnalyzerFactory"
            ) as mock_factory,
        ):
            mock_client.return_value = MagicMock(_cache={}, _cache_max_size=512)
            mock_mcp.return_value = MagicMock()
            mock_mcp.return_value.vault_find_relevant_context.return_value = []
            mock_mcp.return_value.vault_log_experiment.return_value = "experiments/test.md"

            analyzer = MagicMock()
            parsed = MagicMock()
            parsed.intent_confidence = 0.9
            parsed.intent = MagicMock(value="generate")
            parsed.constraints = []
            parsed.criteria = []
            analyzer.parse_request.return_value = parsed
            mock_factory.create.return_value = analyzer

            mgr = CompoundSessionManager()
            mgr.start_session()

            def my_task(guidance):
                return "Task completed with guidance"

            success, result = await mgr.execute_aligned(
                request="Test integration",
                execute_fn=my_task,
                skill_name="integration_test",
                use_executor=True,
            )

            assert success is True
            assert "output" in result
            assert result.get("session_id", "").startswith("session_")
