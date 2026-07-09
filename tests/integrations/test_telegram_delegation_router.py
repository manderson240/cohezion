"""Tests for the intent-based delegation router in TelegramCommunicationHub.

Structural: _classify_delegation_intent exists and returns one of the 4 valid labels.
Behavioural discriminating:
  - The router correctly calls the right handler, NOT just _chat_omnirouter, for
    STATUS/LIST/AGENT intents — a wrong implementation that skips classification
    and always calls _chat_omnirouter would FAIL these tests.
  - _select_lemonade_model prefers fleet models (Bonsai-8B-gguf) over the
    previously-preferred Granite-4.1-8B-GGUF which is NOT in the live fleet.
  - _handle_agent no longer calls git-worktree or tmux — those reliably fail.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Guard: if telegram_bot can't be imported (missing httpx) skip entire module
pytest.importorskip("httpx", reason="httpx required for telegram_bot")

from cohezion.integrations.telegram_bot import TelegramCommunicationHub


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_hub() -> TelegramCommunicationHub:
    """Create a hub with test env vars — constructor reads from environment."""
    import os

    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "TEST_TOKEN")
    os.environ.setdefault("TELEGRAM_CHAT_ID", "12345")
    return TelegramCommunicationHub()


# ── Structural: method exists and returns valid label ─────────────────────────


def test_classify_delegation_intent_method_exists():
    hub = _make_hub()
    assert hasattr(hub, "_classify_delegation_intent")
    assert callable(hub._classify_delegation_intent)


@pytest.mark.asyncio
async def test_classify_delegation_intent_returns_valid_label():
    """Must return one of the four valid intent strings, never raise."""
    hub = _make_hub()
    valid = {"STATUS", "LIST", "AGENT", "CHAT"}
    # Patch _chat_omnirouter to return a known intent word
    hub._chat_omnirouter = AsyncMock(return_value=("STATUS", {}))
    result = await hub._classify_delegation_intent("cpu load?")
    assert result in valid


@pytest.mark.asyncio
async def test_classify_delegation_intent_defaults_to_chat_on_empty_response():
    """Empty classifier response → fall back to CHAT, never crash."""
    hub = _make_hub()
    hub._chat_omnirouter = AsyncMock(return_value=("", {}))
    result = await hub._classify_delegation_intent("something vague")
    assert result == "CHAT"


@pytest.mark.asyncio
async def test_classify_delegation_intent_defaults_to_chat_on_exception():
    """Classifier call raising → fail open to CHAT."""
    hub = _make_hub()
    hub._chat_omnirouter = AsyncMock(side_effect=ConnectionError("lemonade down"))
    result = await hub._classify_delegation_intent("hello")
    assert result == "CHAT"


@pytest.mark.asyncio
async def test_classify_delegation_intent_ignores_unknown_label():
    """Unknown label from model (e.g. 'GREET') → CHAT, not crash."""
    hub = _make_hub()
    hub._chat_omnirouter = AsyncMock(return_value=("GREET", {}))
    result = await hub._classify_delegation_intent("hello there!")
    assert result == "CHAT"


# ── Behavioural discriminating: router calls the right handler ─────────────────


@pytest.mark.asyncio
async def test_handle_chat_routes_status_intent_to_handle_status():
    """When classifier returns STATUS, _handle_status must be called.

    Discriminating: wrong implementation that always calls _chat_omnirouter
    for plain text would NEVER call _handle_status, failing this assertion.
    """
    hub = _make_hub()
    hub._classify_delegation_intent = AsyncMock(return_value="STATUS")
    hub._handle_status = AsyncMock()
    hub._chat_omnirouter = AsyncMock()

    await hub._handle_chat("what's the cpu load?")

    hub._handle_status.assert_called_once()
    hub._chat_omnirouter.assert_not_called()


@pytest.mark.asyncio
async def test_handle_chat_routes_list_intent_to_handle_list():
    """When classifier returns LIST, _handle_list must be called."""
    hub = _make_hub()
    hub._classify_delegation_intent = AsyncMock(return_value="LIST")
    hub._handle_list = AsyncMock()
    hub._chat_omnirouter = AsyncMock()

    await hub._handle_chat("what sessions are running?")

    hub._handle_list.assert_called_once()
    hub._chat_omnirouter.assert_not_called()


@pytest.mark.asyncio
async def test_handle_chat_routes_chat_intent_to_omni_router():
    """CHAT intent must reach _chat_omnirouter (the normal LLM path)."""
    hub = _make_hub()
    hub._classify_delegation_intent = AsyncMock(return_value="CHAT")
    hub._chat_omnirouter = AsyncMock(return_value=("Hello!", {}))
    hub._send_msg = AsyncMock()
    hub._record_telemetry = AsyncMock()

    await hub._handle_chat("explain HIHO stability")

    hub._chat_omnirouter.assert_called()


@pytest.mark.asyncio
async def test_handle_chat_agent_intent_calls_verify_and_handle_agent():
    """AGENT intent: verify inference health, then call _handle_agent."""
    hub = _make_hub()
    hub._classify_delegation_intent = AsyncMock(return_value="AGENT")
    hub._verify_inference_health = AsyncMock(return_value=True)
    hub._handle_agent = AsyncMock()

    await hub._handle_chat("run the compound daemon for me")

    hub._handle_agent.assert_called_once_with("run the compound daemon for me")


@pytest.mark.asyncio
async def test_handle_chat_agent_intent_blocked_when_inference_offline():
    """AGENT intent with inference down → send error, do NOT call _handle_agent."""
    hub = _make_hub()
    hub._classify_delegation_intent = AsyncMock(return_value="AGENT")
    hub._verify_inference_health = AsyncMock(return_value=False)
    hub._handle_agent = AsyncMock()
    hub._send_msg = AsyncMock()

    await hub._handle_chat("build me a new model")

    hub._handle_agent.assert_not_called()
    hub._send_msg.assert_called_once()
    # Error message must mention :13305 or blocking
    call_args = hub._send_msg.call_args[0][0]
    assert "13305" in call_args or "blocked" in call_args.lower() or "🔴" in call_args


# ── Behavioural: _handle_agent no longer uses git-worktree / tmux ─────────────


@pytest.mark.asyncio
async def test_handle_agent_does_not_call_git_worktree():
    """_handle_agent must NOT spawn git worktree — that was the primary failure mode.

    Discriminating: old implementation called _run_cmd with git worktree add.
    A correct implementation never calls _run_cmd for git at all.
    """
    hub = _make_hub()
    hub._chat_omnirouter = AsyncMock(return_value=("Here is my analysis.", {}))
    hub._send_msg = AsyncMock()
    hub._record_telemetry = AsyncMock()

    # If _run_cmd is called, the test fails (old worktree path still present)
    hub._run_cmd = AsyncMock(
        side_effect=AssertionError(
            "_handle_agent must not call _run_cmd (git worktree / tmux removed)"
        )
    )

    await hub._handle_agent("analyze the compound loop performance")

    hub._send_msg.assert_called_once_with("Here is my analysis.", parse_mode=None)


@pytest.mark.asyncio
async def test_handle_agent_sends_error_when_omnirouter_unavailable():
    """When OmniRouter returns empty, bot must send an actionable error message."""
    hub = _make_hub()
    hub._chat_omnirouter = AsyncMock(return_value=("", {}))
    hub._send_msg = AsyncMock()

    await hub._handle_agent("do something complex")

    hub._send_msg.assert_called_once()
    call_args = hub._send_msg.call_args[0][0]
    assert "unavailable" in call_args.lower() or "⚠️" in call_args


# ── Behavioural: _select_lemonade_model prefers actual fleet models ───────────


@pytest.mark.asyncio
async def test_select_lemonade_model_prefers_bonsai_over_granite():
    """Bonsai-8B-gguf (in fleet) must be preferred over Granite-4.1-8B-GGUF (not in fleet).

    Discriminating: old implementation returned Granite-4.1-8B-GGUF when it
    was listed — but that model is NOT in the live fleet, so health checks
    would fail. A correct implementation prefers Bonsai-8B-gguf instead.
    """
    hub = _make_hub()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "Bonsai-8B-gguf"},
            {"id": "Granite-4.1-8B-GGUF"},
            {"id": "llama3.2-1b-FLM"},
        ]
    }

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await hub._select_lemonade_model()

    assert result == "Bonsai-8B-gguf"


@pytest.mark.asyncio
async def test_select_lemonade_model_falls_back_when_preferred_absent():
    """When Bonsai/Gemma-4-E4B aren't served, pick the first non-embed model."""
    hub = _make_hub()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "nomic-embed-text-v2"},  # skip: embed
            {"id": "some-cloud-model"},  # skip: cloud
            {"id": "Qwen3.6-35B-A3B-NoThinking"},  # first non-embed, non-cloud
        ]
    }

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        result = await hub._select_lemonade_model()

    assert result == "Qwen3.6-35B-A3B-NoThinking"


@pytest.mark.asyncio
async def test_select_lemonade_model_returns_none_when_router_down():
    """Returns None on connection error — never raises."""
    hub = _make_hub()

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=ConnectionError("refused")
        )
        result = await hub._select_lemonade_model()

    assert result is None
