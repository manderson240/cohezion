"""extend_claude consumes EscalationProbe as its quality gate (item 139, 2026-06-07).

`inference.lynx_gate.EscalationProbe` was wired only by an __init__ re-export with no production
caller. It is a genuinely distinct signal — a learned (length / vocab-diversity / completeness)
escalation classifier that falls back to a min_chars=200 gate when untrained — richer than
extend_claude's raw len>=40 heuristic. This gives it a REAL consumer: the extend_claude gate.

Discriminating: a 50-char local result PASSES the old len>=40 heuristic but the probe's
min_chars=200 fallback REJECTS it. With the probe → escalate; without it → accept local. A wrong
impl that ignores the probe accepts the 50-char text → test_probe_escalates_where_heuristic_accepts
fails.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.inference.lynx_gate import EscalationProbe


_FIFTY = "x" * 50  # passes len>=40 heuristic, fails the probe's min_chars=200 fallback


@pytest.mark.asyncio
async def test_probe_escalates_where_heuristic_accepts() -> None:
    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(text=_FIFTY, model="local", lane="npu", latency_ms=1.0)

    with patch("cohezion.inference.fleet.route", side_effect=fake_route):
        from cohezion.inference.fleet import extend_claude

        # untrained probe → min_chars=200 fallback → 50 chars is insufficient → escalate
        result = await extend_claude(
            "solve x", escalation_probe=EscalationProbe(), max_local_attempts=1
        )
    assert result.escalated_to_cloud is True


@pytest.mark.asyncio
async def test_no_probe_accepts_via_length_heuristic() -> None:
    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(text=_FIFTY, model="local", lane="npu", latency_ms=1.0)

    with patch("cohezion.inference.fleet.route", side_effect=fake_route):
        from cohezion.inference.fleet import extend_claude

        # no probe → len>=40 heuristic accepts the 50-char local result (no escalation)
        result = await extend_claude("solve x", max_local_attempts=1)
    assert result.escalated_to_cloud is False
    assert result.text == _FIFTY


@pytest.mark.asyncio
async def test_probe_accepts_long_local_output() -> None:
    long_text = "y" * 250  # passes the probe's min_chars=200 fallback

    async def fake_route(prompt, **kwargs):
        from cohezion.inference.fleet import RouteResult

        return RouteResult(text=long_text, model="local", lane="npu", latency_ms=1.0)

    with patch("cohezion.inference.fleet.route", side_effect=fake_route):
        from cohezion.inference.fleet import extend_claude

        result = await extend_claude(
            "solve x", escalation_probe=EscalationProbe(), max_local_attempts=1
        )
    assert result.escalated_to_cloud is False
    assert result.text == long_text
