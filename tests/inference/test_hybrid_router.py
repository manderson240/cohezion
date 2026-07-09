"""Hybrid local-first / cloud-supplement routing (item 137, 2026-06-07).

User directive: "leverage hybrid local-first inference supplemented with cloud." Composes the
session's three signals — resource_aware_route capacity (122/131), usage_guard quota (134), and
the extend_claude quality gate — into ONE decision, and wires it into extend_claude so the cloud
escalation is QUOTA-AWARE (never run out of Claude — doctrine bullet 5).

Discriminating: an impl that escalates to cloud while the Claude quota is "halt" fails
test_extend_claude_stays_local_when_quota_halt — local-first must win when the quota is exhausted.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.hybrid_router import hybrid_route_decision


def test_local_when_healthy_and_quality_ok() -> None:
    assert (
        hybrid_route_decision(
            local_capacity="route", claude_quota="proceed", local_quality=0.9, quality_threshold=0.8
        )
        == "local"
    )


def test_cloud_when_local_saturated_and_quota_proceeds() -> None:
    assert (
        hybrid_route_decision(
            local_capacity="defer", claude_quota="proceed", local_quality=0.9, quality_threshold=0.8
        )
        == "cloud"
    )


def test_cloud_when_low_quality_and_quota_proceeds() -> None:
    assert (
        hybrid_route_decision(
            local_capacity="route", claude_quota="proceed", local_quality=0.5, quality_threshold=0.8
        )
        == "cloud"
    )


def test_stay_local_when_low_quality_but_quota_halt() -> None:
    # never run out of Claude: accept lower-quality LOCAL rather than spend the exhausted quota
    assert (
        hybrid_route_decision(
            local_capacity="route", claude_quota="halt", local_quality=0.5, quality_threshold=0.8
        )
        == "local"
    )


def test_defer_when_local_cannot_serve_and_quota_halt() -> None:
    assert (
        hybrid_route_decision(
            local_capacity="defer", claude_quota="halt", local_quality=0.9, quality_threshold=0.8
        )
        == "defer"
    )


def test_throttle_does_not_escalate_to_cloud() -> None:
    # throttle conserves Claude just like halt for the cloud-escalation decision
    assert (
        hybrid_route_decision(
            local_capacity="route",
            claude_quota="throttle",
            local_quality=0.5,
            quality_threshold=0.8,
        )
        == "local"
    )


# --- the real consumer: extend_claude escalation is quota-gated ---


@pytest.mark.asyncio
async def test_extend_claude_stays_local_when_quota_halt() -> None:
    # local route always returns a short (gate-failing) result → local "insufficient"
    short = AsyncMock(return_value=None)

    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        # a local attempt: short text fails the length gate; a cloud attempt would set prefer=
        return RouteResult(text="hi", model="local", lane="npu", latency_ms=1.0)

    with patch("cohezion.inference.fleet.route", side_effect=fake_route) as mock_route:
        from cohezion.inference.fleet import extend_claude

        result = await extend_claude("solve x", claude_quota="halt", max_local_attempts=1)

    # quota halt → NO cloud escalation; every route() call was local-only (no prefer=claude_model)
    assert result.escalated_to_cloud is False
    assert all(kw.kwargs.get("prefer") is None for kw in mock_route.call_args_list)
    _ = short


@pytest.mark.asyncio
async def test_extend_claude_escalates_when_quota_proceeds() -> None:
    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(text="hi", model="m", lane="npu", latency_ms=1.0)

    with patch("cohezion.inference.fleet.route", side_effect=fake_route) as mock_route:
        from cohezion.inference.fleet import extend_claude

        result = await extend_claude("solve x", claude_quota="proceed", max_local_attempts=1)

    assert result.escalated_to_cloud is True
    # a cloud escalation route() call carries prefer=claude_model
    assert any(kw.kwargs.get("prefer") for kw in mock_route.call_args_list)
