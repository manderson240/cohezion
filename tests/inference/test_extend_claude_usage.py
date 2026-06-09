"""extend_claude is the second (direct, paid) dispatch root — its cloud escalation must
be metered. The orchestrator logs in run(); extend_claude never routes through run(), so
this is non-overlapping coverage, and it is the F1 paid path the monitor most needs to see.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.inference import fleet
from cohezion.inference.fleet import RouteResult, extend_claude


def _short_local() -> RouteResult:
    return RouteResult(text="", model="llama3.2-1b-FLM", lane="npu", latency_ms=1.0, error=None)


def _cloud_answer() -> RouteResult:
    return RouteResult(
        text="a thorough cloud answer that clears the gate",
        model="claude-sonnet-4-6",
        lane="cloud",
        latency_ms=500.0,
        cost_usd=0.0091,
    )


@pytest.mark.asyncio
async def test_extend_claude_cloud_escalation_is_metered():
    """DISCRIMINATING: local attempts fail the gate → escalate to Claude. The paid
    escalation must persist a usage record tagged source='extend_claude' carrying the
    cloud cost. An impl that only meters the orchestrator path records nothing here."""
    calls = {"n": 0}

    async def _route(prompt, **kwargs):
        # budget_usd=0 → local attempt (return empty, fails gate); prefer=claude → cloud.
        if kwargs.get("prefer"):
            return _cloud_answer()
        calls["n"] += 1
        return _short_local()

    with (
        patch.object(fleet, "route", side_effect=_route),
        patch("cohezion.inference.usage_log.record_dispatch") as rd,
    ):
        result = await extend_claude("a hard reasoning prompt", claude_model="claude-sonnet-4-6")

    assert result.escalated_to_cloud is True
    assert rd.call_count == 1
    kw = rd.call_args.kwargs
    assert kw["source"] == "extend_claude"
    assert kw["model"] == "claude-sonnet-4-6"
    assert kw["cost_usd"] == 0.0091
