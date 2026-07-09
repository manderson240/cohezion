"""Unit tests for TelegramHub and TelegramOOMGuard.

All httpx network calls are mocked so these tests run offline without
any real Telegram credentials or Lemonade router.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.compound.telegram_hub import TelegramHub, TelegramOOMGuard


# ---------------------------------------------------------------------------
# TelegramOOMGuard
# ---------------------------------------------------------------------------


def test_oom_guard_safe_model_passes_through():
    """A model in SAFE_MODELS is returned unchanged."""
    assert TelegramOOMGuard.guard("llama3.2-1b-FLM") == "llama3.2-1b-FLM"
    assert TelegramOOMGuard.guard("Gemma-4-E2B-it-GGUF") == "Gemma-4-E2B-it-GGUF"
    assert TelegramOOMGuard.guard("Mellum-4b") == "Mellum-4b"


def test_oom_guard_heavy_model_remapped():
    """A large model not on the allowlist is remapped to the safe fallback."""
    assert TelegramOOMGuard.guard("Qwen3.6-35B-A3B-GGUF") == "llama3.2-1b-FLM"
    assert TelegramOOMGuard.guard("Gemma-4-31B-it-GGUF") == "llama3.2-1b-FLM"
    assert TelegramOOMGuard.guard("unknown-model-100B") == "llama3.2-1b-FLM"


# ---------------------------------------------------------------------------
# TelegramHub: importable without credentials
# ---------------------------------------------------------------------------


def test_telegram_hub_importable_without_env():
    """TelegramHub can be constructed with no env vars set (no-op mode)."""
    env = {
        k: v for k, v in os.environ.items() if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    }
    with patch.dict(os.environ, env, clear=True):
        hub = TelegramHub()
    assert not hub.is_configured()


# ---------------------------------------------------------------------------
# TelegramHub.ask_local: OOM-safe model routing — key contract test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_local_sends_safe_model_when_heavy_requested():
    """ask_local must forward the SAFE model to the OmniRouter, not the requested heavy one.

    This is the core OOM-safety contract: even if the caller passes a large model
    name, the POST body must contain the guarded (safe) model name.
    """
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": {"content": "pong"}}]}

    mock_client = AsyncMock()
    mock_client.post.return_value = resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("cohezion.compound.telegram_hub.httpx.AsyncClient", return_value=mock_client):
        hub = TelegramHub()
        result = await hub.ask_local("hello", model="Qwen3.6-35B-A3B-GGUF")

    assert result == "pong"
    _, kwargs = mock_client.post.call_args
    sent_model = kwargs["json"]["model"]
    assert sent_model == "llama3.2-1b-FLM", (
        f"Expected safe fallback 'llama3.2-1b-FLM' in POST body, got {sent_model!r}"
    )


# ---------------------------------------------------------------------------
# TelegramHub.ask_local: error path returns "" and never raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_local_returns_empty_on_error():
    """ask_local must return '' and not raise when the network call fails."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("connection refused")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("cohezion.compound.telegram_hub.httpx.AsyncClient", return_value=mock_client):
        hub = TelegramHub()
        result = await hub.ask_local("hello")

    assert result == ""


# ---------------------------------------------------------------------------
# TelegramHub.notify: no-op when unconfigured, sends when configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_noop_when_unconfigured():
    """notify must not make any HTTP call when credentials are absent."""
    env = {
        k: v for k, v in os.environ.items() if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
    }
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch.dict(os.environ, env, clear=True),
        patch("cohezion.compound.telegram_hub.httpx.AsyncClient", return_value=mock_client),
    ):
        hub = TelegramHub()
        await hub.notify("test message", session_id="s1")

    mock_client.post.assert_not_called()
