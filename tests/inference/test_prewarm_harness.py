"""Discriminating tests for PrewarmLocalModelHarness (wiring-gap fix, 2026-08-13).

``prewarm_model()`` was a stub: ``time.sleep(0.1)`` then unconditionally return True and
persist a "completed" kanban item — it never touched the router at all. Validated against
the overnight local-inference autoresearch loop (branch autoresearch/local-inference-20260813,
Run 8 vs Run 9): run-start timeout clusters were tasks queueing behind a model load/swap;
an untimed probe call before the measurement clock removed them entirely (Run 9: first
zero-timeout run of the night). This test suite fails against the old stub and against any
fix that fakes success without actually calling the target model.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from cohezion.inference.orchestrator import OrchestrationResult
from cohezion.inference.prewarm_harness import PrewarmLocalModelHarness


def _tier_returning(result: OrchestrationResult):
    """A fake GaiaAgentTier-shaped object whose .run() is awaitable and inspectable."""
    tier = AsyncMock()
    tier.run.return_value = result
    return tier


def _patch_router_alive():
    """Mock the router-liveness pre-flight so tests never touch the network."""
    return patch(
        "cohezion.inference.prewarm_harness.is_lemonade_alive",
        new=AsyncMock(return_value=True),
    )


class TestPrewarmModelCallsTheRouter:
    def test_calls_build_gaia_llm_tier_with_target_model(self) -> None:
        """The old stub never referenced the target model beyond string interpolation
        in a log line. A real fix must construct a tier FOR that exact model."""
        harness = PrewarmLocalModelHarness(target_model="Qwen3-Coder-30B-A3B-Instruct-GGUF")
        ok_result = OrchestrationResult(
            text="ready", primary_model="x", final_model="x", escalation_count=0
        )
        with (
            _patch_router_alive(),
            patch(
                "cohezion.inference.prewarm_harness.build_gaia_llm_tier",
                return_value=_tier_returning(ok_result),
            ) as mock_build,
        ):
            harness.prewarm_model()
        assert mock_build.called, "prewarm_model must build a tier — the old stub never did"
        _, kwargs = mock_build.call_args
        assert kwargs.get("model_id") == "Qwen3-Coder-30B-A3B-Instruct-GGUF"

    def test_success_requires_a_real_nonempty_response(self) -> None:
        """Discriminating: an empty/errored response must NOT count as a successful warm-up.
        The old stub returned True unconditionally — this fails against it."""
        harness = PrewarmLocalModelHarness(target_model="Qwen3-Coder-30B-A3B-Instruct-GGUF")
        fail_result = OrchestrationResult(
            text="",
            primary_model="x",
            final_model="x",
            escalation_count=0,
            error="model_load_error: llama-server failed to start",
        )
        with (
            _patch_router_alive(),
            patch(
                "cohezion.inference.prewarm_harness.build_gaia_llm_tier",
                return_value=_tier_returning(fail_result),
            ),
        ):
            ok = harness.prewarm_model()
        assert ok is False, (
            "a load-error response must produce prewarm_model()==False — "
            "the stub always returned True regardless of the router's actual state"
        )

    def test_success_returns_true_on_real_nonempty_response(self) -> None:
        harness = PrewarmLocalModelHarness(target_model="Qwen3-Coder-30B-A3B-Instruct-GGUF")
        ok_result = OrchestrationResult(
            text="ready", primary_model="x", final_model="x", escalation_count=0
        )
        with (
            _patch_router_alive(),
            patch(
                "cohezion.inference.prewarm_harness.build_gaia_llm_tier",
                return_value=_tier_returning(ok_result),
            ),
        ):
            ok = harness.prewarm_model()
        assert ok is True

    def test_uses_configured_lemonade_port_in_base_url(self) -> None:
        harness = PrewarmLocalModelHarness(target_model="Gemma-4-E4B-it-GGUF", lemonade_port=13305)
        ok_result = OrchestrationResult(
            text="ready", primary_model="x", final_model="x", escalation_count=0
        )
        with (
            _patch_router_alive(),
            patch(
                "cohezion.inference.prewarm_harness.build_gaia_llm_tier",
                return_value=_tier_returning(ok_result),
            ) as mock_build,
        ):
            harness.prewarm_model()
        _, kwargs = mock_build.call_args
        assert "13305" in kwargs.get("base_url", "")

    def test_callable_from_inside_a_running_event_loop(self) -> None:
        """Discriminating (cloud-review finding, 2026-08-14): a bare asyncio.run()
        impl raises RuntimeError when prewarm_model() is called from an async
        context (e.g. an async startup hook). Must complete and return a bool."""
        import asyncio

        harness = PrewarmLocalModelHarness(target_model="Gemma-4-E4B-it-GGUF")
        ok_result = OrchestrationResult(
            text="ready", primary_model="x", final_model="x", escalation_count=0
        )

        async def call_from_async_context() -> bool:
            with (
                _patch_router_alive(),
                patch(
                    "cohezion.inference.prewarm_harness.build_gaia_llm_tier",
                    return_value=_tier_returning(ok_result),
                ),
            ):
                return harness.prewarm_model()

        assert asyncio.run(call_from_async_context()) is True

    def test_skips_tier_build_when_router_unreachable(self) -> None:
        """Discriminating: when the router itself is down, prewarm_model must fail fast
        WITHOUT attempting to build/call a tier (that call would just time out)."""
        harness = PrewarmLocalModelHarness(target_model="Qwen3-Coder-30B-A3B-Instruct-GGUF")
        with (
            patch(
                "cohezion.inference.prewarm_harness.is_lemonade_alive",
                new=AsyncMock(return_value=False),
            ),
            patch("cohezion.inference.prewarm_harness.build_gaia_llm_tier") as mock_build,
        ):
            ok = harness.prewarm_model()
        assert ok is False
        assert not mock_build.called, "must not attempt a tier call when the router is down"
