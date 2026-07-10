"""extend_claude_guarded — quota-aware extend_claude activated in production (item 138, 2026-06-07).

Item 137 made extend_claude quota-aware but `claude_quota` defaults None (off). This wraps it with
the LIVE usage_guard so escalation actually conserves Claude under load. Its real consumer is
`scripts/delegate.py` (the delegate CLI). Same activation pattern as item 135 (real sizes → item 132).

Discriminating: an impl that ignores the live quota (forwards None / always escalates) fails
test_guarded_stays_local_when_live_quota_halt — under a halt quota it must NOT escalate to cloud.
"""

from __future__ import annotations
import pytest

from unittest.mock import patch


@pytest.mark.asyncio
@pytest.mark.xfail(reason="TDD-red: quota-aware extend_claude guard not wired", strict=False)
async def test_guarded_stays_local_when_live_quota_halt() -> None:
    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(
            text="hi", model="local", lane="npu", latency_ms=1.0
        )  # short → gate fails

    with (
        patch("cohezion.inference.fleet._live_claude_quota", return_value="halt"),
        patch("cohezion.inference.fleet.route", side_effect=fake_route) as mock_route,
    ):
        from cohezion.inference.fleet import extend_claude_guarded

        result = await extend_claude_guarded("solve x", max_local_attempts=1)

    assert result.escalated_to_cloud is False
    assert all(kw.kwargs.get("prefer") is None for kw in mock_route.call_args_list)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="TDD-red: quota-aware extend_claude guard not wired", strict=False)
async def test_guarded_escalates_when_live_quota_proceed() -> None:
    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(text="hi", model="m", lane="npu", latency_ms=1.0)

    with (
        patch("cohezion.inference.fleet._live_claude_quota", return_value="proceed"),
        patch("cohezion.inference.fleet.route", side_effect=fake_route) as mock_route,
    ):
        from cohezion.inference.fleet import extend_claude_guarded

        result = await extend_claude_guarded("solve x", max_local_attempts=1)

    assert result.escalated_to_cloud is True
    assert any(kw.kwargs.get("prefer") for kw in mock_route.call_args_list)
