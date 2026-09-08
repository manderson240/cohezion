"""Tests for Antigravity communication bridge in TelegramCommunicationHub."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytest.importorskip("httpx", reason="httpx required for telegram_bot")

from cohezion.integrations.telegram_bot import (
    TelegramCommunicationHub,
    clean_model_output,
)


@pytest.fixture
def clean_env():
    """Patches environment variables for the Telegram bot config."""
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "TELEGRAM_CHAT_ID": "8344971611",
            "TELEGRAM_ROUTING_MODE": "antigravity",
        },
    ):
        yield


def test_clean_model_output_strips_thinking_tags():
    raw = "<think>\nThinking about the user query...\n</think>\nHere is the answer."
    cleaned = clean_model_output(raw)
    assert cleaned == "Here is the answer."
    assert "<think>" not in cleaned


def test_clean_model_output_preserves_clean_text():
    raw = "Normal direct response without thinking."
    assert clean_model_output(raw) == raw


@pytest.mark.asyncio
async def test_process_message_agy_command(clean_env):
    """Verify that /agy routes to _handle_antigravity."""
    hub = TelegramCommunicationHub()
    message = {
        "chat": {"id": 8344971611},
        "text": "/agy What is our current sprint status?",
    }

    with patch.object(hub, "_handle_antigravity", new_callable=AsyncMock) as mock_agy:
        await hub._process_message(message)
        mock_agy.assert_called_once_with("What is our current sprint status?")


@pytest.mark.asyncio
async def test_process_message_mode_switching(clean_env):
    """Verify that /mode switches routing_mode."""
    hub = TelegramCommunicationHub()
    assert hub.routing_mode == "antigravity"

    with patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send:
        await hub._process_message({"chat": {"id": 8344971611}, "text": "/mode local"})
        assert hub.routing_mode == "local"
        assert "local" in mock_send.call_args[0][0]

        await hub._process_message({"chat": {"id": 8344971611}, "text": "/mode antigravity"})
        assert hub.routing_mode == "antigravity"
        assert "antigravity" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_process_message_plain_text_routes_to_antigravity_when_mode_antigravity(clean_env):
    """Verify plain text routes to _handle_antigravity when in antigravity mode."""
    hub = TelegramCommunicationHub()
    hub.routing_mode = "antigravity"
    message = {
        "chat": {"id": 8344971611},
        "text": "Did the Anthropic portfolio finish syncing?",
    }

    with patch.object(hub, "_handle_antigravity", new_callable=AsyncMock) as mock_agy:
        await hub._process_message(message)
        mock_agy.assert_called_once_with("Did the Anthropic portfolio finish syncing?")


@pytest.mark.asyncio
async def test_handle_antigravity_executes_cli_and_replies(clean_env):
    """Verify _handle_antigravity runs agy CLI and sends response."""
    hub = TelegramCommunicationHub()
    mock_sub = MagicMock()
    mock_sub.returncode = 0
    mock_sub.stdout = "Everything is synchronized and verified."

    with (
        patch.object(hub, "_run_cmd", new_callable=AsyncMock, return_value=mock_sub),
        patch.object(hub, "_send_chat_action", new_callable=AsyncMock) as mock_action,
        patch.object(hub, "_bridge_to_active_session", new_callable=AsyncMock) as mock_bridge,
        patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send,
    ):
        await hub._handle_antigravity("Is the portfolio ready?")

        mock_action.assert_called_with("typing")
        mock_bridge.assert_called_once_with("Is the portfolio ready?")
        mock_send.assert_called_once()
        sent = mock_send.call_args[0][0]
        assert "Antigravity" in sent
        assert "Everything is synchronized and verified." in sent


def test_markdown_to_telegram_html_formatting():
    """Verify markdown conversion to Telegram HTML."""
    from cohezion.integrations.telegram_bot import markdown_to_telegram_html

    md = (
        "# Status Report\n\n"
        "**System**: Active\n"
        "* Item 1\n"
        "- Item 2\n\n"
        "Code: `foo()`\n\n"
        "```python\n"
        "x = 10 < 20\n"
        "```"
    )
    res = markdown_to_telegram_html(md)
    assert "<b>Status Report</b>" in res
    assert "<b>System</b>: Active" in res
    assert "• Item 1" in res
    assert "• Item 2" in res
    assert "<code>foo()</code>" in res
    assert '<pre><code class="language-python">x = 10 &lt; 20</code></pre>' in res


@pytest.mark.asyncio
async def test_send_msg_chunking_and_error_fallback(clean_env):
    """Verify _send_msg handles >4000 char chunking and retries plain text on failure."""
    hub = TelegramCommunicationHub()
    long_msg = "Hello World! " * 400  # ~5200 chars

    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 400
    mock_resp_fail.text = "Bad Request: can't parse entities"

    mock_resp_ok = MagicMock()
    mock_resp_ok.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call fails (HTML error), second call succeeds (plain text fallback)
        mock_post.side_effect = [mock_resp_fail, mock_resp_ok, mock_resp_ok]
        await hub._send_msg(long_msg, parse_mode="HTML")
        assert mock_post.call_count >= 2
