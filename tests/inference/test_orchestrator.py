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


@pytest.mark.asyncio
async def test_min_tier_index_skips_cheaper_tiers():
    """Discriminating (difficulty-based cascade entry): min_tier_index=2 starts at tier 2, skipping
    tiers 0 and 1. A wrong impl that ignores min_tier_index runs tier 0 first (prefer='tier0')."""
    orch = TieredOrchestrator(
        tiers=[
            ("tier0", QualityGate.TRUST),
            ("tier1", QualityGate.TRUST),
            ("tier2", QualityGate.TRUST),
        ]
    )
    with patch(
        "cohezion.inference.orchestrator.route", AsyncMock(return_value=_rr("ok"))
    ) as m:
        await orch.run("test", min_tier_index=2)
    assert m.await_count == 1  # only one tier ran
    assert m.call_args.kwargs["prefer"] == "tier2"  # it was tier 2, NOT tier 0


@pytest.mark.asyncio
async def test_min_tier_index_default_starts_at_tier0():
    """Default min_tier_index=0 is backward-compatible (cheapest tier first)."""
    orch = TieredOrchestrator(
        tiers=[("tier0", QualityGate.TRUST), ("tier1", QualityGate.TRUST)]
    )
    with patch(
        "cohezion.inference.orchestrator.route", AsyncMock(return_value=_rr("ok"))
    ) as m:
        await orch.run("test")
    assert m.call_args.kwargs["prefer"] == "tier0"


@pytest.mark.asyncio
async def test_min_tier_index_clamped_never_skips_all():
    """Out-of-range min_tier_index clamps to the last tier (never empties the cascade)."""
    orch = TieredOrchestrator(
        tiers=[("tier0", QualityGate.TRUST), ("tier1", QualityGate.TRUST)]
    )
    with patch(
        "cohezion.inference.orchestrator.route", AsyncMock(return_value=_rr("ok"))
    ) as m:
        await orch.run("test", min_tier_index=99)
    assert m.await_count == 1
    assert m.call_args.kwargs["prefer"] == "tier1"  # clamped to last tier


@pytest.mark.asyncio
async def test_lever1_task_gate_overrides_fixed_tier_gate():
    """Lever 1: a categorical task (gate_chars=0) passes a SHORT correct answer at tier 0 instead of
    needlessly escalating because it's < the fixed min_chars=500. A wrong impl that ignores
    gate_chars escalates in BOTH cases and fails the gate_chars=0 assertion."""
    orch = TieredOrchestrator(
        tiers=[("npu", QualityGate(min_chars=500)), ("cpu", QualityGate.TRUST)]
    )
    with patch(
        "cohezion.inference.orchestrator.route",
        AsyncMock(return_value=_rr("POSITIVE")),
    ):
        esc_default = (await orch.run("classify the sentiment")).escalation_count
        esc_categorical = (await orch.run("classify the sentiment", gate_chars=0)).escalation_count
    assert esc_default == 1      # short answer fails fixed min_chars=500 → escalates (the degenerate path)
    assert esc_categorical == 0  # Lever 1: gate_chars=0 → "POSITIVE" passes at NPU, no escalation
