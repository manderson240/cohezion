"""End-to-end test for UnifiedOrchestrator — the compound engineering keystone.

Validates the full dispatch loop:
    classify → route → verify → dispatch → score → collect trace

Tests cover all dispatch paths:
    1. Simple prompts → swarm path (fast)
    2. Complex prompts → LatentEngine path (deep)
    3. AutoHarness rejection path
    4. Circuit breaker isolation
    5. Batch dispatch with concurrency bounds
    6. Experience trace collection
    7. Quality scorer integration (CoE fallback)
    8. Graceful degradation when LatentEngine unavailable
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.unified_orchestrator import (
    AdaptiveRouter,
    DefaultQualityScorer,
    DispatchSource,
    ExperienceCollector,
    NodeKind,
    NodeMetrics,
    UnifiedResult,
    classify_complexity,
    create_default_orchestrator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scorer():
    """Default quality scorer."""
    return DefaultQualityScorer()


@pytest.fixture
def router():
    """Fresh adaptive router with 3 test nodes."""
    r = AdaptiveRouter()
    r.register("test:npu", "model-a", NodeKind.NPU)
    r.register("test:igpu", "model-b", NodeKind.IGPU)
    r.register("test:ollama", "phi4-mini", NodeKind.OLLAMA)
    return r


@pytest.fixture
def orchestrator():
    """Orchestrator with mocked HTTP calls — no real network."""
    orch = create_default_orchestrator(
        enable_latent=False,
        cpu_models=["phi4-mini"],
        n_cpu_workers=2,
    )
    return orch


# ---------------------------------------------------------------------------
# classify_complexity
# ---------------------------------------------------------------------------


class TestComplexityClassifier:
    """Test the zero-cost complexity heuristic."""

    def test_simple_prompt_is_low(self):
        score = classify_complexity("Hello, how are you?")
        assert score < 0.3

    def test_reasoning_prompt_is_high(self):
        score = classify_complexity(
            "Prove step by step that the square root of 2 is irrational. "
            "Derive the theorem from first principles."
        )
        assert score >= 0.4

    def test_code_prompt_gets_code_bonus(self):
        score = classify_complexity("```python\ndef foo(): pass\n```\nImplement this algorithm")
        assert score > classify_complexity("hello")

    def test_multi_question_scores_higher(self):
        single = classify_complexity("What is 2+2?")
        multi = classify_complexity(
            "What is 2+2? How does it relate to group theory? "
            "Why is this fundamental? Can you prove it?"
        )
        assert multi > single

    def test_empty_prompt(self):
        assert classify_complexity("") == 0.0


# ---------------------------------------------------------------------------
# DefaultQualityScorer
# ---------------------------------------------------------------------------


class TestQualityScorer:
    """Test the compound quality scorer."""

    def test_empty_text_scores_zero(self, scorer):
        assert scorer.score("", "any prompt") == 0.0

    def test_short_text_scores_low(self, scorer):
        assert scorer.score("ok", "a long complex prompt") < 0.5

    def test_good_response_scores_high(self, scorer):
        response = (
            "The Riemann hypothesis states that all non-trivial zeros of the "
            "Riemann zeta function have a real part equal to 1/2. This is one "
            "of the most important unsolved problems in mathematics. "
            "It connects number theory to complex analysis."
        )
        score = scorer.score(response, "Explain the Riemann hypothesis")
        assert score > 0.5

    def test_repetitive_text_penalised(self, scorer):
        repetitive = "the the the the the the the the the the"
        diverse = "quick brown fox jumps over lazy dog moon stars"
        assert scorer.score(diverse, "test") > scorer.score(repetitive, "test")


# ---------------------------------------------------------------------------
# AdaptiveRouter
# ---------------------------------------------------------------------------


class TestAdaptiveRouter:
    """Test node ranking and circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_ranked_nodes_returns_best_first(self, router):
        # Give node A good metrics, node B bad
        await router.record_success("test:npu", 50.0, 0.9)
        await router.record_success("test:igpu", 500.0, 0.3)
        ranked = router.ranked_nodes()
        assert ranked[0].node_id == "test:npu"

    @pytest.mark.asyncio
    async def test_kind_filter(self, router):
        await router.record_success("test:npu", 50.0, 0.9)
        await router.record_success("test:ollama", 100.0, 0.7)
        ranked = router.ranked_nodes(kind_filter=NodeKind.OLLAMA)
        assert all(n.kind == NodeKind.OLLAMA for n in ranked)

    @pytest.mark.asyncio
    async def test_circuit_breaker_excludes_broken_nodes(self, router):
        # Trip circuit breaker with 5 consecutive failures
        for _ in range(5):
            await router.record_error("test:npu")

        ranked = router.ranked_nodes()
        node_ids = [n.node_id for n in ranked]
        assert "test:npu" not in node_ids

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, router):
        for _ in range(4):
            await router.record_error("test:npu")
        # One more failure would trip it, but a success resets
        await router.record_success("test:npu", 50.0, 0.9)
        ranked = router.ranked_nodes()
        node_ids = [n.node_id for n in ranked]
        assert "test:npu" in node_ids

    def test_all_metrics_export(self, router):
        metrics = router.all_metrics()
        assert len(metrics) == 3
        assert all("node_id" in m for m in metrics)
        assert all("circuit_open" in m for m in metrics)


# ---------------------------------------------------------------------------
# NodeMetrics circuit breaker
# ---------------------------------------------------------------------------


class TestNodeMetricsCircuitBreaker:
    """Test the integrated circuit breaker on NodeMetrics."""

    def test_not_open_before_threshold(self):
        n = NodeMetrics(node_id="test", model="m", kind=NodeKind.OLLAMA)
        for _ in range(4):
            n.record_error()
        assert not n.circuit_is_open

    def test_opens_at_threshold(self):
        n = NodeMetrics(node_id="test", model="m", kind=NodeKind.OLLAMA)
        for _ in range(5):
            n.record_error()
        assert n.circuit_is_open

    def test_success_resets_counter(self):
        n = NodeMetrics(node_id="test", model="m", kind=NodeKind.OLLAMA)
        for _ in range(4):
            n.record_error()
        n.record_success(50.0, 0.9)
        assert n.consecutive_failures == 0
        n.record_error()
        assert not n.circuit_is_open  # only 1 failure


# ---------------------------------------------------------------------------
# UnifiedOrchestrator — dispatch paths
# ---------------------------------------------------------------------------


class TestUnifiedOrchestrator:
    """Test the core dispatch loop with mocked HTTP backends."""

    @pytest.mark.asyncio
    async def test_swarm_dispatch_basic(self, orchestrator):
        """Simple prompt dispatches via swarm path."""
        with patch(
            "cohezion.inference.unified_orchestrator._call_ollama",
            new_callable=AsyncMock,
            return_value=("The answer is 42.", 50.0),
        ):
            result = await orchestrator.run("What is the answer?")

        assert isinstance(result, UnifiedResult)
        assert result.source == DispatchSource.SWARM
        assert result.text == "The answer is 42."
        assert result.quality_score > 0
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_latent_engine_activates_for_complex_prompt(self):
        """Complex prompt activates LatentEngine when enabled."""
        orch = create_default_orchestrator(
            enable_latent=True,
            complexity_threshold=0.1,  # Low threshold to trigger
        )

        mock_result = MagicMock()
        mock_result.final_answer = "Proof: assume sqrt(2) = p/q..."
        mock_result.confidence = 0.85
        mock_result.coe_assessment = {"coe_score": 0.85}
        mock_result.coconut_bfs_explored = 3
        mock_result.soft_prefix_used = True
        mock_result.state_trajectory = [1, 2, 3]

        with patch("cohezion.inference.unified_orchestrator.LatentEngine") as MockEngine:
            instance = MockEngine.return_value
            instance.reason = AsyncMock(return_value=mock_result)

            result = await orch.run(
                "Prove step by step that sqrt(2) is irrational. "
                "Derive the theorem from first principles."
            )

        assert result.source == DispatchSource.LATENT_ENGINE
        assert "Proof" in result.text
        assert result.quality_score == 0.85

    @pytest.mark.asyncio
    async def test_latent_fallback_to_swarm(self, orchestrator):
        """When LatentEngine fails, falls back to swarm dispatch."""
        orch = create_default_orchestrator(
            enable_latent=True,
            complexity_threshold=0.1,
            cpu_models=["phi4-mini"],
        )

        with (
            patch(
                "cohezion.inference.unified_orchestrator.LatentEngine",
                side_effect=ImportError("numpy not installed"),
            ),
            patch(
                "cohezion.inference.unified_orchestrator._call_ollama",
                new_callable=AsyncMock,
                return_value=("Fallback answer.", 100.0),
            ),
        ):
            result = await orch.run("Prove step by step that sqrt(2) is irrational.")

        assert result.source == DispatchSource.SWARM
        assert result.text == "Fallback answer."

    @pytest.mark.asyncio
    async def test_autoharness_rejection(self):
        """AutoHarness verifier blocks unsafe actions."""
        verifier = MagicMock()
        verifier.verify.return_value = (False, "unsafe import detected")

        orch = create_default_orchestrator(action_verifier=verifier)
        result = await orch.run("import os; os.system('rm -rf /')")

        assert result.source == DispatchSource.FALLBACK
        assert "rejected" in result.error
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_batch_dispatch(self, orchestrator):
        """Batch dispatch processes all prompts."""
        with patch(
            "cohezion.inference.unified_orchestrator._call_ollama",
            new_callable=AsyncMock,
            return_value=("Answer.", 30.0),
        ):
            results = await orchestrator.run_batch(["q1", "q2", "q3"], max_tokens=64)

        assert len(results) == 3
        assert all(r.text == "Answer." for r in results)

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_failing_nodes(self):
        """Nodes that fail repeatedly are skipped via circuit breaker."""
        orch = create_default_orchestrator(
            cpu_models=["phi4-mini", "mistral:7b"],
            enable_latent=False,
        )

        call_count = 0

        async def _mock_ollama(model, prompt, **kw):
            nonlocal call_count
            call_count += 1
            if model == "phi4-mini":
                raise ConnectionError("node down")
            return "good answer from mistral", 50.0

        # Make phi4-mini fail 6 times to trip breaker
        with (
            patch(
                "cohezion.inference.unified_orchestrator._call_ollama",
                side_effect=_mock_ollama,
            ),
            patch(
                "cohezion.inference.unified_orchestrator._call_lemonade",
                new_callable=AsyncMock,
                side_effect=ConnectionError("lemonade down"),
            ),
        ):
            for _ in range(6):
                await orch.run("test")

            # Now phi4-mini should be circuit-broken
            # Next call should skip it
            call_count = 0
            result = await orch.run("test")
            # phi4-mini should have been skipped or failed quickly
            assert result.text != ""

    @pytest.mark.asyncio
    async def test_health_report(self, orchestrator):
        """Health report includes node metrics and circuit state."""
        report = orchestrator.health_report()
        assert "total_nodes" in report
        assert "healthy_nodes" in report
        assert "circuit_open_nodes" in report
        assert "nodes" in report
        assert isinstance(report["nodes"], list)


# ---------------------------------------------------------------------------
# ExperienceCollector
# ---------------------------------------------------------------------------


class TestExperienceCollector:
    """Test trace persistence and flush behavior."""

    @pytest.mark.asyncio
    async def test_trace_persistence(self, tmp_path):
        """Traces are persisted as JSON files."""
        collector = ExperienceCollector(flush_every=100)
        collector._trace_dir = tmp_path

        from cohezion.inference.unified_orchestrator import (
            ExperienceTrace as ET,
        )

        trace = ET(
            trace_id="test123",
            prompt_digest="abc",
            source="swarm",
            node_id="test:npu",
            model="model-a",
            quality_score=0.8,
            latency_ms=50.0,
            complexity=0.3,
            phi_score=0.6,
        )
        await collector.record(trace)

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

        import json

        data = json.loads(files[0].read_text())
        assert data["trace_id"] == "test123"
        assert data["quality_score"] == 0.8

    @pytest.mark.asyncio
    async def test_flush_triggered_at_threshold(self, tmp_path):
        """Flush is triggered when buffer reaches threshold."""
        collector = ExperienceCollector(flush_every=3)
        collector._trace_dir = tmp_path

        from cohezion.inference.unified_orchestrator import (
            ExperienceTrace as ET,
        )

        with patch.object(collector, "_flush", new_callable=AsyncMock) as mock_flush:
            for i in range(3):
                trace = ET(
                    trace_id=f"trace{i}",
                    prompt_digest="d",
                    source="swarm",
                    node_id="n",
                    model="m",
                    quality_score=0.5,
                    latency_ms=10.0,
                    complexity=0.1,
                    phi_score=0.5,
                )
                await collector.record(trace)

            assert mock_flush.called


# ---------------------------------------------------------------------------
# Integration: full loop
# ---------------------------------------------------------------------------


class TestIntegrationLoop:
    """Test the full classify→route→dispatch→score→trace loop."""

    @pytest.mark.asyncio
    async def test_full_loop_produces_trace(self, tmp_path):
        """A complete dispatch produces a quality-scored experience trace."""
        orch = create_default_orchestrator(
            enable_latent=False,
            cpu_models=["phi4-mini"],
        )
        orch._collector._trace_dir = tmp_path

        with (
            patch(
                "cohezion.inference.unified_orchestrator._call_ollama",
                new_callable=AsyncMock,
                return_value=("A thoughtful and detailed answer.", 45.0),
            ),
            patch(
                "cohezion.inference.unified_orchestrator._call_lemonade",
                new_callable=AsyncMock,
                side_effect=ConnectionError("no lemonade"),
            ),
        ):
            result = await orch.run("Explain quantum entanglement")

        assert result.text != ""
        assert result.quality_score > 0
        assert result.trace_id != ""

        # Verify trace was persisted
        files = list(tmp_path.glob("*.json"))
        assert len(files) >= 1
