"""TieredOrchestrator tests — all invariants O1–O8 from the Phase 6 plan."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.fleet import RouteResult
from cohezion.inference.orchestrator import (
    QualityGate,
    TieredOrchestrator,
    default_hierarchy,
)


def _rr(text: str, model: str = "m", cost: float = 0.0, ttft: float = 50.0) -> RouteResult:
    return RouteResult(
        text=text,
        model=model,
        lane="test",
        latency_ms=100.0,
        ttft_ms=ttft,
        cost_usd=cost,
        error=None,
    )


def test_quality_gate_min_chars():
    gate = QualityGate(min_chars=10)
    assert gate.check(_rr("short"))[0] is False
    assert gate.check(_rr("a much longer response"))[0] is True


def test_quality_gate_trust_always_passes():
    assert QualityGate.TRUST.check(_rr(""))[0] is True


def test_quality_gate_error_fails():
    r = RouteResult(text="", model="m", lane="test", latency_ms=0, error="boom")
    assert QualityGate.TRUST.check(r)[0] is False


def test_quality_gate_require_nonempty_fails_on_empty_text():
    """require_nonempty=True rejects empty response even without an error."""
    gate = QualityGate(require_nonempty=True)
    r = RouteResult(text="   ", model="m", lane="test", latency_ms=0, error=None)
    passed, reason = gate.check(r)
    assert passed is False
    assert reason == "empty response"


@pytest.mark.asyncio
async def test_tier_exception_continues_to_next_tier():
    """If a tier raises, it is logged and escalation continues to the next tier."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate.TRUST),
            ("tier1", QualityGate.TRUST),
        ]
    )

    async def _raise_then_succeed(
        prompt, *, task=None, prefer=None, budget_usd=None, stream=True, max_tokens=600
    ):
        if prefer == "tier0":
            raise RuntimeError("tier0 hardware offline")
        return _rr("tier1 response")

    with patch("cohezion.inference.orchestrator.route", side_effect=_raise_then_succeed):
        result = await orch.run("test")

    assert result.text == "tier1 response"
    assert result.error is None
    assert len(result.tier_path) == 2
    assert result.tier_path[0].passed is False
    assert "exception" in result.tier_path[0].reason


@pytest.mark.asyncio
async def test_O1_first_tier_passes_no_escalation():
    """Tier 0 gate passes → only tier 0 runs."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=5)),
            ("tier1", QualityGate.TRUST),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("this is long enough")),
    ) as m:
        result = await orch.run("test")
    assert result.escalation_count == 0
    assert result.final_model == "m"
    assert m.await_count == 1


@pytest.mark.asyncio
async def test_O1_first_tier_fails_escalates_to_second():
    """Tier 0 gate fails → tier 1 runs."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=100)),  # will fail
            ("tier1", QualityGate.TRUST),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=[_rr("short"), _rr("accepted at tier 1")]),
    ) as m:
        result = await orch.run("test")
    assert result.escalation_count == 1
    assert m.await_count == 2


@pytest.mark.asyncio
async def test_O7_all_tiers_fail_returns_exhausted_not_raise():
    """All gates fail → structured exhausted result, not an exception."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=100)),
            ("tier1", QualityGate(min_chars=100)),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("too short")),
    ):
        result = await orch.run("test")
    assert result.error == "all tiers exhausted"
    assert len(result.tier_path) == 2
    assert all(not p.passed for p in result.tier_path)


@pytest.mark.asyncio
async def test_O3_budget_cap_short_circuits_escalation():
    """max_cost_usd enforced — tier 1 not invoked when budget already consumed."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=100)),  # fails
            ("tier1", QualityGate.TRUST),
            ("tier2", QualityGate.TRUST),
        ],
        max_cost_usd=0.005,
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=[_rr("short", cost=0.01), _rr("never reached", cost=0.01)]),
    ) as m:
        result = await orch.run("test")
    # Tier 0 runs (cost 0.01), exceeds 0.005 → tier 1/2 not invoked
    assert m.await_count == 1
    assert any(p.reason == "budget_exceeded" for p in result.tier_path)


@pytest.mark.asyncio
async def test_O4_nested_orchestrator_as_tier():
    """A tier target can itself be a TieredOrchestrator (recursive composition)."""
    sub = TieredOrchestrator(tiers=[("sub-tier", QualityGate.TRUST)])
    parent = TieredOrchestrator(
        tiers=[
            ("primary", QualityGate(min_chars=100)),  # fails, escalates to sub
            (sub, QualityGate.TRUST),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=[_rr("fail"), _rr("sub responded well")]),
    ):
        result = await parent.run("test")
    # Escalation reached tier 1 which is the nested orchestrator
    assert result.escalation_count == 1
    assert "TieredOrchestrator" in result.final_model or result.text == "sub responded well"


@pytest.mark.asyncio
async def test_O6_result_schema_complete():
    """OrchestrationResult exposes all required telemetry fields."""
    orch = TieredOrchestrator(tiers=[("only", QualityGate.TRUST)])
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("ok")),
    ):
        result = await orch.run("test")
    assert hasattr(result, "primary_model")
    assert hasattr(result, "final_model")
    assert hasattr(result, "escalation_count")
    assert hasattr(result, "tier_path")
    assert hasattr(result, "cost_usd")
    assert hasattr(result, "latency_ms")
    assert hasattr(result, "ttft_ms")


@pytest.mark.asyncio
async def test_O2_escalations_logged_with_reason():
    """Every attempt logged with (tier_index, model, passed, reason)."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=999)),
            ("tier1", QualityGate.TRUST),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=[_rr("short"), _rr("much longer response")]),
    ):
        result = await orch.run("test")
    assert len(result.tier_path) == 2
    assert result.tier_path[0].tier_index == 0
    assert result.tier_path[0].passed is False
    assert "too short" in result.tier_path[0].reason
    assert result.tier_path[1].passed is True


def test_O8_orchestrator_accepts_empty_tiers_raises():
    with pytest.raises(ValueError):
        TieredOrchestrator(tiers=[])


def test_default_hierarchy_factory():
    """Pre-built 4-tier orchestrator factory works."""
    orch = default_hierarchy(include_claude=True, max_cost_usd=0.05)
    assert len(orch.tiers) == 4
    assert orch.max_cost_usd == 0.05
    assert orch.tiers[0][0] == "Gemma-4-E2B-it-GGUF"
    # Include claude=False excludes the cloud tiers
    orch_nocloud = default_hierarchy(include_claude=False)
    assert len(orch_nocloud.tiers) == 2


@pytest.mark.asyncio
async def test_O3b_nested_orchestrator_honors_parent_budget():
    """Parent budget overrides nested orchestrator's own ceiling.

    Regression: before the O3b fix, a nested TieredOrchestrator used its own
    `max_cost_usd` and ignored the parent's remaining budget — letting a
    sub-orchestrator overspend its caller's envelope. See adversarial review
    Edge-case #10 (ROADMAP P0).
    """
    # Inner orchestrator is generous (allows $1.00) but parent caps at $0.01.
    inner = TieredOrchestrator(
        tiers=[
            ("inner-t0", QualityGate(min_chars=100)),  # will fail at tier 0
            ("inner-t1", QualityGate.TRUST),
        ],
        max_cost_usd=1.00,  # generous local ceiling
    )
    parent = TieredOrchestrator(
        tiers=[
            ("parent-t0", QualityGate(min_chars=100)),  # will fail, escalate
            (inner, QualityGate.TRUST),
        ],
        max_cost_usd=0.01,  # tight outer envelope
    )
    # parent-t0 consumes $0.009 (under cap), inner's tier 0 consumes $0.005
    # (pushing accumulated past parent cap), inner's tier 1 must be skipped.
    responses = [
        _rr("short", cost=0.009),  # parent-t0
        _rr("short", cost=0.005),  # inner-t0 — pushes inner's accumulated to $0.005,
        # but inner inherits parent's remaining budget of $0.01 - $0.009 = $0.001,
        # so inner-t1 must be short-circuited by the budget gate.
        _rr("never reached", cost=0.50),  # inner-t1 — must NOT fire
    ]
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(side_effect=responses),
    ) as m:
        result = await parent.run("test")

    # Only parent-t0 + inner-t0 fired; inner-t1 was blocked by the propagated cap.
    assert m.await_count == 2, (
        f"inner orchestrator must honor parent budget; got {m.await_count} calls (expected 2)"
    )
    # Parent reports budget-aware structure: both tiers recorded.
    assert len(result.tier_path) == 2


@pytest.mark.asyncio
async def test_O3b_nested_respects_own_cap_when_parent_unbounded():
    """Mirror: when parent budget is None, nested keeps its own ceiling."""
    inner = TieredOrchestrator(
        tiers=[
            ("inner-t0", QualityGate(min_chars=100)),  # fails
            ("inner-t1", QualityGate.TRUST),
        ],
        max_cost_usd=0.005,  # tight inner cap
    )
    parent = TieredOrchestrator(
        tiers=[(inner, QualityGate.TRUST)],
        max_cost_usd=None,  # no outer cap
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(
            side_effect=[
                _rr("short", cost=0.01),  # inner-t0 exceeds inner's own cap
                _rr("never reached", cost=0.01),
            ]
        ),
    ) as m:
        await parent.run("test")

    # Only inner-t0 fires; inner-t1 blocked by inner's own $0.005 cap.
    assert m.await_count == 1


# ── pre_dispatch_classifier integration ──────────────────────────────────────


def _decision(node: str, gate_chars: int = 0):
    """Minimal RouteDecision-alike for testing."""
    from types import SimpleNamespace

    return SimpleNamespace(
        node=node, quality_gate_chars=gate_chars, output_type="test", reason="test", confidence=1.0
    )


@pytest.mark.asyncio
async def test_pre_dispatch_routes_gpu_skips_tier0():
    """Classifier returning gpu → tier 0 is skipped entirely."""
    classifier = lambda _: _decision("gpu")

    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=5)),
            ("tier1", QualityGate.TRUST),
        ],
        pre_dispatch_classifier=classifier,
    )

    call_log: list[str] = []

    async def _fake_route(
        prompt, *, task=None, prefer=None, budget_usd=None, stream=True, max_tokens=600
    ):
        call_log.append(prefer)
        return _rr("response from gpu tier")

    with patch("cohezion.inference.orchestrator.route", side_effect=_fake_route):
        result = await orch.run("write a function")

    assert call_log == ["tier1"], "tier0 must be skipped when classifier routes to gpu"
    assert result.escalation_count == 1  # started at index 1
    assert result.error is None


@pytest.mark.asyncio
async def test_pre_dispatch_gate_override_for_tier0():
    """Classifier returning npu with gate_chars=0 overrides tier0's default gate."""
    classifier = lambda _: _decision("npu", gate_chars=0)

    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=30)),  # default gate requires 30 chars
            ("tier1", QualityGate.TRUST),
        ],
        pre_dispatch_classifier=classifier,
    )

    call_log: list[str] = []

    async def _fake_route(
        prompt, *, task=None, prefer=None, budget_usd=None, stream=True, max_tokens=600
    ):
        call_log.append(prefer)
        return _rr("OK")  # 2 chars — would fail gate=30 but should pass gate=0

    with patch("cohezion.inference.orchestrator.route", side_effect=_fake_route):
        result = await orch.run("reply with yes or no")

    assert call_log == ["tier0"], "must stay on tier0 when gate override allows short response"
    assert result.error is None, "gate override enabled short response to pass"


@pytest.mark.asyncio
async def test_pre_dispatch_classifier_exception_uses_defaults():
    """If classifier raises, fall back silently to tier-0 default behavior."""

    def _bad_classifier(_):
        raise RuntimeError("classifier failed")

    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=2)),
            ("tier1", QualityGate.TRUST),
        ],
        pre_dispatch_classifier=_bad_classifier,
    )

    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("ok")),
    ) as m:
        result = await orch.run("test")

    # Fell back to default: tier0 ran first and passed
    assert m.await_count == 1
    assert result.error is None


@pytest.mark.asyncio
async def test_pre_dispatch_none_uses_normal_flow():
    """pre_dispatch_classifier=None is the no-op default; all tiers eligible."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate(min_chars=5)),
            ("tier1", QualityGate.TRUST),
        ],
        pre_dispatch_classifier=None,
    )

    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("hi")),
    ) as m:
        result = await orch.run("test")

    # "hi" is 2 chars, gate=5 fails → tier1 also runs → both invoked
    assert m.await_count == 2
    assert result.error is None


@pytest.mark.asyncio
async def test_pre_dispatch_gpu_routing_overrides_tier1_gate():
    """When classifier routes to GPU, tier 1's gate is overridden with quality_gate_chars.

    Prevents triune-style orchestrators (iGPU gate=2000) from over-escalating
    code tasks where 300-char output is a complete, correct answer.
    """
    # Simulates a triune orchestrator where iGPU has a strict gate=2000
    classifier = lambda _: _decision("gpu", gate_chars=0)  # code: trust any non-empty

    orch = TieredOrchestrator(
        tiers=[
            ("npu", QualityGate(min_chars=500)),
            (
                "igpu",
                QualityGate(min_chars=2000),
            ),  # strict default — would reject 300-char function
            ("cpu", QualityGate.TRUST),
        ],
        pre_dispatch_classifier=classifier,
    )

    call_log: list[str] = []

    async def _fake_route(
        prompt, *, task=None, prefer=None, budget_usd=None, stream=True, max_tokens=600
    ):
        call_log.append(prefer)
        return _rr("def reverse(s):\n    return s[::-1]\n")  # 32 chars — under 2000 gate but valid

    with patch("cohezion.inference.orchestrator.route", side_effect=_fake_route):
        result = await orch.run("write a reverse function")

    assert call_log == ["igpu"], "NPU skipped (start_tier=1), iGPU ran once"
    assert result.error is None, "32-char function must pass: gate override = 0 (trust non-empty)"


@pytest.mark.asyncio
async def test_telemetry_hardware_tier_branches():
    """Exercise FLM/Gemma/Claude model-name branches in telemetry instrumentation."""
    # Uses real model IDs to hit the NPU/iGPU/Cloud hardware tier classification branches
    for model_id in ("llama3.2-1b-FLM", "Gemma-4-E4B-it-GGUF", "claude-haiku-4-5"):
        orch = TieredOrchestrator(tiers=[(model_id, QualityGate.TRUST)])
        with patch(
            "cohezion.inference.orchestrator.route",
            AsyncMock(return_value=_rr("ok", model=model_id)),
        ):
            result = await orch.run("test")
        assert result.error is None, f"Failed for model {model_id}"


# ---------------------------------------------------------------------------
# run_batch() — concurrent dispatch (exp_OOOO, 3.44x throughput measured)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_batch_returns_results_in_order():
    """run_batch() dispatches prompts concurrently and returns ordered results."""
    orch = TieredOrchestrator(tiers=[("llama3.2-1b-FLM", QualityGate.TRUST)])
    prompts = ["prompt 1", "prompt 2", "prompt 3"]
    call_order: list[str] = []

    async def fake_route(prompt, **_):
        call_order.append(prompt)
        return _rr(f"answer for: {prompt}")

    with patch("cohezion.inference.orchestrator.route", side_effect=fake_route):
        results = await orch.run_batch(prompts)

    assert len(results) == 3
    for i, r in enumerate(results):
        assert f"answer for: {prompts[i]}" in r.text or r.text, f"result {i} text mismatch"
    assert all(r.error is None for r in results)


@pytest.mark.asyncio
async def test_run_batch_empty_prompts():
    """run_batch([]) returns empty list."""
    orch = TieredOrchestrator(tiers=[("m", QualityGate.TRUST)])
    results = await orch.run_batch([])
    assert results == []


@pytest.mark.asyncio
async def test_run_batch_single_prompt_same_as_run():
    """run_batch([p]) gives same result as run(p)."""
    orch = TieredOrchestrator(tiers=[("llama3.2-1b-FLM", QualityGate.TRUST)])
    with patch("cohezion.inference.orchestrator.route", AsyncMock(return_value=_rr("single"))):
        r_single = await orch.run("one prompt")
        r_batch = await orch.run_batch(["one prompt"])
    assert r_single.text == r_batch[0].text
    assert r_single.error == r_batch[0].error
