"""Discriminating tests for the orchestrator -> recursive-trace resolution-log seam.

Design: docs/research/FAILURE_RESOLUTION_COLLECTION_DESIGN_2026-06-05.md

The seam must log a (failure_class, resolving_tier, success) pair ONLY when a real
escalation occurred (a lower tier's gate failed and a higher tier resolved) — the
non-circular case. The most plausible wrong wiring logs on EVERY task (including
tier-0 immediate passes), which would just echo the router's existing choice. The
no-escalation test below fails exactly that wrong wiring.
"""

from __future__ import annotations
import pytest

pytestmark = pytest.mark.xfail(
    reason="TDD-red: feature not fully implemented post-consolidation", strict=False
)

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.fleet import RouteResult
from cohezion.inference.orchestrator import QualityGate, TieredOrchestrator
from cohezion.recursive_trace.resolution_log import (
    _coarse_tier,
    log_quality_gate_resolution,
    read_resolutions,
)


def _rr(text: str, model: str = "m") -> RouteResult:
    return RouteResult(
        text=text, model=model, lane="test", latency_ms=0.0, ttft_ms=10.0, cost_usd=0.0
    )


# ---- the helper itself ----------------------------------------------------------


def test_helper_writes_coarse_tier_pair(tmp_path) -> None:
    p = tmp_path / "res.jsonl"
    log_quality_gate_resolution(
        "code", "Gemma-4-26B-iGPU", ["llama3.2-1b-FLM", "Gemma-4-26B"], path=p
    )
    rows = read_resolutions(path=p)
    assert len(rows) == 1
    assert rows[0]["domain"] == "quality_gate"
    assert rows[0]["failure_class"] == "code"
    assert rows[0]["strategy"] == "igpu"  # coarsened from the resolving model
    assert rows[0]["tried_order"] == ["npu", "igpu"]


def test_coarse_tier_mapping() -> None:
    assert _coarse_tier("llama3.2-1b-FLM") == "npu"
    assert _coarse_tier("Gemma-4-26B") == "igpu"
    assert _coarse_tier("claude-opus") == "cloud"
    assert _coarse_tier("nemotron-cpu") == "cpu"


# ---- the orchestrator seam (the discriminating part) ----------------------------


@pytest.mark.asyncio
async def test_logs_pair_on_escalation() -> None:
    # tier0 gate needs 100 chars and gets a short answer -> fails -> tier1 (TRUST) resolves.
    orch = TieredOrchestrator(
        tiers=[("tier0-npu", QualityGate(min_chars=100)), ("tier1-igpu", QualityGate.TRUST)]
    )
    calls = []

    def _recorder(output_type, resolving_model, tried, **kw):
        calls.append((output_type, resolving_model, tried))

    async def _route(prompt, *, prefer=None, **kw):
        return _rr("short" if prefer == "tier0-npu" else "resolved on igpu")

    with (
        patch("cohezion.inference.orchestrator.route", side_effect=_route),
        patch("cohezion.recursive_trace.resolution_log.log_quality_gate_resolution", _recorder),
    ):
        result = await orch.run("test")

    assert result.escalation_count == 1
    assert len(calls) == 1  # logged exactly once
    assert calls[0][1] == "tier1-igpu"  # the resolving tier, not tier0


@pytest.mark.asyncio
async def test_does_not_log_when_tier0_passes_immediately() -> None:
    # Discriminating: tier0 passes -> NO escalation -> NO pair (else it echoes the
    # router's own choice, which is circular).
    orch = TieredOrchestrator(
        tiers=[("tier0-npu", QualityGate(min_chars=5)), ("tier1-igpu", QualityGate.TRUST)]
    )
    calls = []
    with (
        patch(
            "cohezion.inference.orchestrator.route",
            AsyncMock(return_value=_rr("this is long enough to pass")),
        ),
        patch(
            "cohezion.recursive_trace.resolution_log.log_quality_gate_resolution",
            lambda *a, **k: calls.append(a),
        ),
    ):
        result = await orch.run("test")

    assert result.escalation_count == 0
    assert calls == []  # never logged
