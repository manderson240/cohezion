"""Tests for telegram_bot.py OmniRouter health gate (next-move #2, 2026-06-10)."""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.integrations.telegram_bot import TelegramCommunicationHub


def lemonade_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 13305), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.mark.asyncio
async def test_check_omni_health_live_returns_ok():
    """When :13305 is up, the gate returns (True, summary, hazards)."""
    if not lemonade_reachable():
        pytest.skip("lemonade :13305 not reachable")
    hub = TelegramCommunicationHub()
    ok, summary, hazards = await hub._check_omni_health()
    assert ok is True
    assert "lemonade" in summary.lower()
    assert isinstance(hazards, list)


@pytest.mark.asyncio
async def test_check_omni_health_probe_failure_returns_not_ok():
    """If probe_lemonade raises, gate returns (False, error, [])."""
    hub = TelegramCommunicationHub()
    fake_probe = AsyncMock(side_effect=ConnectionError("refused"))
    with patch("cohezion.inference.lemonade_health.probe_lemonade", fake_probe):
        ok, summary, hazards = await hub._check_omni_health()
    assert ok is False
    assert "refused" in summary
    assert hazards == []


@pytest.mark.asyncio
async def test_check_omni_health_reports_hazards_as_warnings():
    """When lemonade is up but has a ctx-hazard, hazards list is non-empty
    but ok is still True (hazards are warnings, not blockers at boot)."""
    from cohezion.inference.lemonade_health import CtxHazard, LemonadeHealth, RecipeProbe

    hub = TelegramCommunicationHub()
    fake_h = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="x",
        status="ok",
        loaded_count=1,
        recipe_probes=[RecipeProbe(recipe="llamacpp", ok=True, latency_ms=10.0, detail="HTTP 200")],
        headroom=[],
        ctx_hazards=[CtxHazard(model="BAD", recipe="llamacpp", ctx_size=0, backend_url="u", pid=1)],
    )
    fake_probe = AsyncMock(return_value=fake_h)
    with patch("cohezion.inference.lemonade_health.probe_lemonade", fake_probe):
        ok, _summary, hazards = await hub._check_omni_health()
    assert ok is True
    assert len(hazards) == 1
    assert "BAD" in hazards[0]


@pytest.mark.asyncio
async def test_start_refuses_when_require_omni_set_and_probe_fails(monkeypatch):
    """With TELEGRAM_REQUIRE_OMNI=1 and probe failure, start() should send
    an error message and NOT enter the polling loop."""
    monkeypatch.setenv("TELEGRAM_REQUIRE_OMNI", "1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    hub = TelegramCommunicationHub()
    sent = []

    async def fake_send(self, text, parse_mode=None):
        sent.append(text)
        return None

    # Bypass the actual Telegram API call
    with (
        patch.object(TelegramCommunicationHub, "_send_msg", fake_send),
        patch(
            "cohezion.inference.lemonade_health.probe_lemonade",
            AsyncMock(side_effect=ConnectionError("refused")),
        ),
    ):
        await hub.start()

    # We expect an error message that mentions "OmniRouter unreachable"
    assert any("OmniRouter" in m for m in sent)
    # And we should NOT have entered the polling loop
    assert hub._running is False
