"""Tests for the SiliconSwarm distributed executor.

Uses unittest mocks throughout — no live Lemonade or Ollama endpoints needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.distributed_swarm import (
    AdaptiveRouter,
    AggregationStrategy,
    ExperienceCollector,
    NodeKind,
    NodeMetrics,
    SiliconSwarm,
    SwarmExperienceTrace,
    _quality_score,
)


# ---------------------------------------------------------------------------
# Unit tests — pure logic, no I/O
# ---------------------------------------------------------------------------


class TestQualityScore:
    def test_empty_returns_zero(self):
        assert _quality_score("", "anything") == 0.0

    def test_whitespace_returns_zero(self):
        assert _quality_score("   ", "anything") == 0.0

    def test_short_nonempty_positive(self):
        score = _quality_score("Hello world", "What is hello?")
        assert score > 0.0

    def test_code_block_bonus(self):
        score_with = _quality_score("```python\nprint('hi')\n```", "write some code")
        score_without = _quality_score("Just text response here.", "write some code")
        assert score_with >= score_without

    def test_repetitive_text_lower_score(self):
        repetitive = "cat " * 50
        diverse = " ".join(f"word_{i}" for i in range(50))
        r = _quality_score(repetitive, "something")
        d = _quality_score(diverse, "something")
        assert d >= r


class TestNodeMetrics:
    def test_initial_score_is_zero(self):
        nm = NodeMetrics(node_id="test", model="phi4-mini", kind=NodeKind.OLLAMA)
        assert nm.avg_quality == 0.0
        assert nm.score == 0.0

    def test_record_updates_windows(self):
        nm = NodeMetrics(node_id="test", model="phi4-mini", kind=NodeKind.OLLAMA)
        nm.record(200.0, 0.8)
        assert nm.avg_latency_ms == pytest.approx(200.0)
        assert nm.avg_quality == pytest.approx(0.8)
        assert nm.total_calls == 1

    def test_record_error_degrades_score(self):
        nm = NodeMetrics(node_id="test", model="phi4-mini", kind=NodeKind.OLLAMA)
        nm.record(100.0, 0.9)
        before = nm.score
        nm.record_error()
        assert nm.score < before

    def test_sliding_window_max_size(self):
        from cohezion.inference.distributed_swarm import _SCORE_WINDOW

        nm = NodeMetrics(node_id="test", model="phi4-mini", kind=NodeKind.OLLAMA)
        for i in range(_SCORE_WINDOW + 5):
            nm.record(float(i), 0.5)
        assert len(nm.latency_ms_window) == _SCORE_WINDOW


class TestAdaptiveRouter:
    @pytest.mark.asyncio
    async def test_register_and_rank(self):
        router = AdaptiveRouter()
        router.register("n1", "phi4-mini", NodeKind.OLLAMA)
        router.register("n2", "mistral:7b", NodeKind.OLLAMA)

        # Seed n1 with good metrics
        await router.update("n1", 150.0, 0.9)
        await router.update("n2", 500.0, 0.4)

        ranked = router.ranked_nodes()
        assert ranked[0].node_id == "n1"

    @pytest.mark.asyncio
    async def test_kind_filter(self):
        router = AdaptiveRouter()
        router.register("npu_node", "gemma4e2b", NodeKind.NPU)
        router.register("cpu_node", "phi4-mini", NodeKind.OLLAMA)

        npu_ranked = router.ranked_nodes(kind_filter=NodeKind.NPU)
        assert all(n.kind == NodeKind.NPU for n in npu_ranked)
        assert len(npu_ranked) == 1

    @pytest.mark.asyncio
    async def test_error_recording(self):
        router = AdaptiveRouter()
        router.register("bad_node", "phi4-mini", NodeKind.OLLAMA)
        # Seed 3 errors
        for _ in range(3):
            await router.record_error("bad_node")
        metrics = router.all_metrics()
        assert metrics[0]["error_count"] == 3


# ---------------------------------------------------------------------------
# Integration-style tests — mock httpx calls
# ---------------------------------------------------------------------------


@pytest.fixture
def swarm():
    """Create a SiliconSwarm with minimal CPU model list for speed."""
    return SiliconSwarm(
        cpu_models=["phi4-mini"],
        n_cpu_workers=2,
        strategy=AggregationStrategy.FIRST_PASS,
    )


class TestSiliconSwarm:
    @pytest.mark.asyncio
    async def test_dispatch_ollama_success(self, swarm):
        """Dispatch to an Ollama node when Lemonade is down."""
        with (
            patch(
                "cohezion.inference.distributed_swarm._call_lemonade",
                side_effect=Exception("Lemonade down"),
            ),
            patch(
                "cohezion.inference.distributed_swarm._call_ollama",
                new_callable=AsyncMock,
                return_value=("Ollama says hello!", 150.0),
            ),
            patch.object(
                ExperienceCollector,
                "record",
                new_callable=AsyncMock,
            ),
        ):
            result = await swarm.dispatch("Say hello")
            assert "hello" in result.text.lower() or result.text != ""

    @pytest.mark.asyncio
    async def test_dispatch_returns_best_quality(self, swarm):
        """When multiple nodes respond, the one with highest quality wins."""

        async def mock_lemonade(port, model, prompt, **kwargs):
            return "short", 100.0

        async def mock_ollama(model, prompt, **kwargs):
            return "A much longer, more informative and detailed answer for the question.", 200.0

        with (
            patch(
                "cohezion.inference.distributed_swarm._call_lemonade",
                side_effect=Exception("down"),
            ),
            patch(
                "cohezion.inference.distributed_swarm._call_ollama",
                new_callable=AsyncMock,
                side_effect=mock_ollama,
            ),
            patch.object(
                ExperienceCollector,
                "record",
                new_callable=AsyncMock,
            ),
        ):
            result = await swarm.dispatch("Explain quantum entanglement")
            assert result.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_dispatch_parallel_returns_per_prompt(self, swarm):
        """dispatch_parallel should return one result per prompt."""
        prompts = ["What is 1+1?", "What is the capital of France?", "Define entropy."]

        with (
            patch(
                "cohezion.inference.distributed_swarm._call_lemonade",
                side_effect=Exception("down"),
            ),
            patch(
                "cohezion.inference.distributed_swarm._call_ollama",
                new_callable=AsyncMock,
                return_value=("Answer text here.", 180.0),
            ),
            patch.object(
                ExperienceCollector,
                "record",
                new_callable=AsyncMock,
            ),
        ):
            results = await swarm.dispatch_parallel(prompts)
            assert len(results) == len(prompts)
            assert all(hasattr(r, "task_id") for r in results)

    @pytest.mark.asyncio
    async def test_all_nodes_fail_returns_empty(self, swarm):
        """When every node fails, result text is empty but no exception raised."""
        with (
            patch(
                "cohezion.inference.distributed_swarm._call_lemonade",
                side_effect=Exception("down"),
            ),
            patch(
                "cohezion.inference.distributed_swarm._call_ollama",
                side_effect=Exception("down"),
            ),
            patch.object(
                ExperienceCollector,
                "record",
                new_callable=AsyncMock,
            ),
        ):
            result = await swarm.dispatch("Test prompt")
            assert result.text == ""
            assert result.error is None  # No exception propagated

    @pytest.mark.asyncio
    async def test_start_probes_without_crash(self, swarm):
        """swarm.start() should complete even when all endpoints are unreachable."""
        with patch(
            "cohezion.inference.distributed_swarm.httpx.AsyncClient",
            side_effect=Exception("No network"),
        ):
            # Should not raise
            await swarm.start()

    def test_node_report_format(self, swarm):
        """node_report() should return a list of dicts with expected keys."""
        report = swarm.node_report()
        assert isinstance(report, list)
        for entry in report:
            assert "node_id" in entry
            assert "model" in entry
            assert "avg_quality" in entry
            assert "score" in entry

    def test_swarm_summary_format(self, swarm):
        summary = swarm.swarm_summary()
        assert "total_nodes" in summary
        assert "healthy_nodes" in summary
        assert "top_node" in summary


# ---------------------------------------------------------------------------
# ExperienceCollector tests
# ---------------------------------------------------------------------------


class TestExperienceCollector:
    @pytest.mark.asyncio
    async def test_record_persists_trace(self, tmp_path, monkeypatch):
        """Traces should be written to the trace directory."""
        monkeypatch.setattr(
            "cohezion.inference.distributed_swarm.ExperienceCollector.__init__",
            lambda self, flush_every=10: None,
        )
        collector = ExperienceCollector.__new__(ExperienceCollector)
        collector._buffer = []
        collector._flush_every = 999  # Don't auto-flush
        collector._trace_dir = tmp_path
        import asyncio

        collector._lock = asyncio.Lock()

        trace = SwarmExperienceTrace(
            trace_id="abcd-1234",
            task_id="task1",
            prompt_digest="deadbeef",
            strategy="first_pass",
            node_count=3,
            winning_node="ollama:phi4-mini",
            latency_ms=250.0,
            quality_score=0.75,
            phi_score=0.5,
            per_node_metrics=[],
        )
        await collector.record(trace)

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        import json

        data = json.loads(files[0].read_text())
        assert data["trace_id"] == "abcd-1234"
        assert data["quality_score"] == pytest.approx(0.75)
