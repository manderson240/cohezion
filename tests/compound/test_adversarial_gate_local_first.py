"""Quarter-on-a-string: `_adversarial_review_gate` must try the LOCAL $0 lane first.

Until 2026-07-27 the gate built the metered frontier cascade (Fable -> Opus -> agy, each a
`subprocess.run` CLI call at timeout=90s) FIRST and used it unconditionally, so every
``refine()`` reached for cloud before local -- contradicting the method's own docstring, which
says "Uses Bonsai-8B-gguf via :13305 OmniRouter ... Quarter-on-a-string: $0 local inference".

The most plausible WRONG implementation is the old one: frontier first. Every test below fails
against it.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.skill_refiner import ExecutionMetrics, LearningSignal, SkillRefiner


def _signal() -> LearningSignal:
    return LearningSignal(
        skill_name="cache_skill",
        operation_type="generate",
        key_insight="raise cache TTL",
        metric_change="quality +0.1",
        recommendation="set TTL to 300s",
        confidence=0.8,
    )


def _metrics() -> ExecutionMetrics:
    return ExecutionMetrics(
        success=True,
        duration_seconds=1.0,
        tokens_used=50,
        token_efficiency=50.0,
        quality_score=0.9,
        anomaly_score=0.1,
        cached_hits=0,
    )


@pytest.fixture
def _frontier_spy():
    """Patch the frontier oracle so any cloud call is observable — and never real."""
    with patch("cohezion.inference.frontier_oracle.frontier_complete_sync") as spy:
        spy.return_value = "APPROVE"
        yield spy


def test_local_lane_is_used_and_frontier_is_never_called(_frontier_spy) -> None:
    """DISCRIMINATING: with lemonade UP, the metered cascade must not be touched at all.

    The pre-fix implementation built `_frontier_wrapper` first and assigned it
    unconditionally, so `frontier_complete_sync` would be called three times (once per
    adversarial persona) and this assertion would fail.
    """
    shim = MagicMock()
    shim.prompt.return_value = "APPROVE"

    with (
        patch("cohezion.compound.local_inference.lemonade_available", return_value=True),
        patch("gaia.llm.lemonade_client.LemonadeClient", MagicMock()),
        patch("cohezion.inference.gaia_adapter._GaiaLLMClientShim", return_value=shim),
    ):
        sr = SkillRefiner()
        assert sr._adversarial_review_gate(_signal(), "cache_skill", _metrics()) is True

    assert _frontier_spy.call_count == 0, "metered frontier was called while local was UP"
    assert shim.prompt.call_count == 3, "expected one local call per adversarial persona"


def test_dead_local_endpoint_does_not_silently_bind(_frontier_spy) -> None:
    """A dead :13305 must NOT bind the local lane.

    ``LemonadeClient(...)`` construction does not prove the endpoint is live. Binding it
    anyway would make every perspective raise at call time and fail-open to APPROVE — a gate
    that can never fail. The liveness probe is what forces a genuine escalation instead.
    """
    with (
        patch("cohezion.compound.local_inference.lemonade_available", return_value=False),
        patch("gaia.llm.lemonade_client.LemonadeClient", MagicMock()),
    ):
        sr = SkillRefiner()
        assert sr._adversarial_review_gate(_signal(), "cache_skill", _metrics()) is True

    assert _frontier_spy.call_count == 3, (
        "a genuine local miss must escalate to the frontier, not bind a dead local lane"
    )


def test_cached_chat_fn_is_reused_and_never_escalates() -> None:
    """An already-built reviewer short-circuits both lanes (no rebuild, no cloud probe)."""
    calls: list[str] = []

    def _fake(prompt: str) -> str:
        calls.append(prompt)
        return "APPROVE"

    sr = SkillRefiner()
    sr._adversarial_chat_fn = _fake

    with patch("cohezion.inference.frontier_oracle.frontier_complete_sync") as spy:
        assert sr._adversarial_review_gate(_signal(), "cache_skill", _metrics()) is True
        assert spy.call_count == 0

    assert len(calls) == 3
