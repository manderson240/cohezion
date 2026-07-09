"""Tests for the Telegram bot communication hub integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.integrations.telegram_bot import TelegramCommunicationHub


@pytest.fixture
def clean_env():
    """Provides a patched environment for Telegram config."""
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "TELEGRAM_CHAT_ID": "8344971611",
        },
    ):
        yield


def test_is_configured_true(clean_env):
    """Test that hub is configured when env variables exist."""
    hub = TelegramCommunicationHub()
    assert hub.is_configured() is True
    assert hub.token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert hub.allowed_chat_id == "8344971611"
    assert hub.base_url == "https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def test_is_configured_false():
    """Test that hub is not configured when env variables are empty or missing."""
    with patch.dict("os.environ", {}, clear=True):
        hub = TelegramCommunicationHub()
        assert hub.is_configured() is False


@pytest.mark.asyncio
async def test_process_message_unauthorized(clean_env):
    """Verify that messages from unauthorized chat IDs are ignored."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 999999999},  # Unauthorized chat ID
        "text": "/status",
    }

    with patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send:
        await hub._process_message(message)
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_process_message_help(clean_env):
    """Verify that /help sends the help message."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 8344971611},
        "text": "/help",
    }

    with patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send:
        await hub._process_message(message)
        mock_send.assert_called_once()
        assert "Cohezion Telemetry Hub Commands" in mock_send.call_args[0][0]


@pytest.mark.asyncio
async def test_process_message_status(clean_env):
    """Verify that /status queries silicon vitals and replies."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 8344971611},
        "text": "/status",
    }

    # Mock psutil
    mock_mem = MagicMock()
    mock_mem.total = 128 * (1024**3)
    mock_mem.available = 64 * (1024**3)
    mock_mem.percent = 50.0

    # Mock nvidia-smi subprocess
    mock_sub = MagicMock()
    mock_sub.returncode = 0
    mock_sub.stdout = "25, 2048, 12288\n"

    # Mock Ollama tags API call via httpx
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "deepseek-r1:70b"}, {"name": "qwen3-coder:30b"}]
    }

    with (
        patch("psutil.virtual_memory", return_value=mock_mem),
        patch("psutil.cpu_percent", return_value=12.5),
        patch("subprocess.run", return_value=mock_sub),
        patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp),
        patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send,
    ):
        await hub._process_message(message)

        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert "Silicon Vitals" in sent_text
        assert "12.5%" in sent_text
        assert "64.0GB / 128.0GB" in sent_text
        assert "Util: 25%, VRAM: 2048MB / 12288MB" in sent_text
        assert "deepseek-r1:70b, qwen3-coder:30b" in sent_text


@pytest.mark.asyncio
async def test_process_message_list_sessions(clean_env):
    """Verify that /list gets tmux sessions."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 8344971611},
        "text": "/list",
    }

    mock_sub = MagicMock()
    mock_sub.returncode = 0
    mock_sub.stdout = (
        "session1: 1 windows (created Wed Jun  3 10:00:00 2026)\nsession2: 2 windows\n"
    )

    with (
        patch("subprocess.run", return_value=mock_sub),
        patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send,
    ):
        await hub._process_message(message)

        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert "Active Sessions" in sent_text
        assert "session1" in sent_text
        assert "session2" in sent_text


@pytest.mark.asyncio
async def test_process_message_read_logs(clean_env):
    """Verify that /read retrieves pane logs and escapes html tags."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 8344971611},
        "text": "/read session1",
    }

    mock_sub = MagicMock()
    mock_sub.returncode = 0
    mock_sub.stdout = "some normal log line\n<error> some tags inside </error>\nanother line"

    with (
        patch("subprocess.run", return_value=mock_sub),
        patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send,
    ):
        await hub._process_message(message)

        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert "Log Tail: session1" in sent_text
        # Check html tags replacement
        assert "&lt;error&gt;" in sent_text
        assert "&lt;/error&gt;" in sent_text
        assert "some normal log line" in sent_text


@pytest.mark.asyncio
async def test_process_message_send_keys(clean_env):
    """Verify that /send sends keys to tmux session."""
    hub = TelegramCommunicationHub()

    message = {
        "chat": {"id": 8344971611},
        "text": "/send session1 make test",
    }

    mock_sub = MagicMock()
    mock_sub.returncode = 0

    with (
        patch("subprocess.run", return_value=mock_sub) as mock_run,
        patch.object(hub, "_send_msg", new_callable=AsyncMock) as mock_send,
    ):
        await hub._process_message(message)

        mock_run.assert_called_once_with(
            ["tmux", "send-keys", "-t", "session1", "make test", "C-m"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        mock_send.assert_called_once()
        assert "Sent input to <code>session1</code>" in mock_send.call_args[0][0]
