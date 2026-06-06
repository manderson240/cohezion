"""Tests that the Telegram bot chat routes through the lemonade $0 local fleet.

The main chat interface must prefer the always-up lemonade router (:13305,
OpenAI-compatible) and only fall back to Ollama (:11434) when the router is
unreachable/empty. These tests mock ``httpx`` at the module level (no live
calls) and are discriminating: a wrong implementation that keeps hitting Ollama
or parses the wrong response shape will fail.
"""

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.integrations.telegram_bot import ModelSelection, TelegramCommunicationHub


@pytest.fixture
def mock_env():
    """Patches environment variables for the Telegram bot config."""
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "TELEGRAM_CHAT_ID": "8344971611",
        },
    ):
        yield


def _ok_response(payload: dict) -> MagicMock:
    """Build a 200 httpx-style response whose .json() is synchronous."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.text = ""
    return resp


def _err_response(status: int = 503) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {}
    resp.text = "service unavailable"
    return resp


class _RecordingClient:
    """Async-context-manager httpx stub that records every GET/POST URL.

    ``get_router`` / ``post_router`` map a URL substring to a response (or to a
    callable raising an exception), so each test can route by URL and later
    assert which endpoints were actually hit.
    """

    def __init__(self, get_router, post_router=None):
        self._get_router = get_router
        self._post_router = post_router or {}
        self.get_urls: list[str] = []
        self.post_urls: list[str] = []
        self.post_bodies: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @staticmethod
    def _resolve(result):
        # Plain functions (not MagicMock) are factories, e.g. raising/erroring.
        if isinstance(result, types.FunctionType):
            return result()
        return result

    async def get(self, url, *args, **kwargs):
        self.get_urls.append(url)
        for needle, result in self._get_router.items():
            if needle in url:
                return self._resolve(result)
        return _err_response(404)

    async def post(self, url, *args, **kwargs):
        self.post_urls.append(url)
        self.post_bodies.append(kwargs.get("json", {}))
        for needle, result in self._post_router.items():
            if needle in url:
                return self._resolve(result)
        return _err_response(404)


@pytest.mark.asyncio
async def test_select_model_prefers_lemonade_router_granite(mock_env):
    """_select_model hits the :13305 router and returns Granite when listed."""
    hub = TelegramCommunicationHub()

    router_models = _ok_response(
        {
            "data": [
                {"id": "Gemma-4-E4B-it-GGUF"},
                {"id": "Granite-4.1-8B-GGUF"},
                {"id": "nomic-embed-text-GGUF"},
            ]
        }
    )
    client = _RecordingClient(get_router={"/v1/models": router_models})

    with patch("cohezion.integrations.telegram_bot.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = client
        model, backend = await hub._select_model()

    assert model == "Granite-4.1-8B-GGUF"
    assert backend == "lemonade"
    # Discriminating: a wrong impl hitting :11434 would record no 13305 URL.
    assert any("13305" in u and "/v1/models" in u for u in client.get_urls), client.get_urls
    assert not any("11434" in u for u in client.get_urls)


@pytest.mark.asyncio
async def test_select_model_falls_back_to_ollama_when_router_down(mock_env):
    """When the router errors/empties, _select_model falls back to Ollama."""
    hub = TelegramCommunicationHub()

    def _router_unavailable():
        return _err_response(503)

    client = _RecordingClient(
        get_router={
            "/v1/models": _router_unavailable,  # lemonade router 503
            "/api/tags": _ok_response({"models": [{"name": "phi4:latest"}]}),  # ollama 200
        }
    )

    with patch("cohezion.integrations.telegram_bot.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = client
        model, backend = await hub._select_model()

    # Proves non-destructive fallback: Ollama path still works.
    assert backend == "ollama"
    assert model == "phi4:latest"
    assert any("13305" in u and "/v1/models" in u for u in client.get_urls)
    assert any("11434" in u and "/api/tags" in u for u in client.get_urls)


@pytest.mark.asyncio
async def test_select_model_falls_back_when_router_empty(mock_env):
    """An empty router listing also triggers the Ollama fallback."""
    hub = TelegramCommunicationHub()

    client = _RecordingClient(
        get_router={
            "/v1/models": _ok_response({"data": []}),  # router up but empty
            "/api/tags": _ok_response({"models": [{"name": "mistral:7b"}]}),
        }
    )

    with patch("cohezion.integrations.telegram_bot.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = client
        model, backend = await hub._select_model()

    assert backend == "ollama"
    assert model == "mistral:7b"


@pytest.mark.asyncio
async def test_handle_chat_lemonade_posts_openai_endpoint(mock_env):
    """_handle_chat with a lemonade model POSTs OpenAI format and parses choices."""
    hub = TelegramCommunicationHub()

    sentinel = "HIHO equilibrium is at 0.5 coherence."
    # Purely OpenAI-shaped body: NO top-level "message" key. A wrong impl
    # reading r.json()["message"]["content"] would KeyError / get empty.
    chat_resp = _ok_response({"choices": [{"message": {"content": sentinel}}]})

    sent: list[str] = []

    async def _capture(text, parse_mode=None):
        sent.append(text)

    hub._send_msg = _capture  # type: ignore[assignment]
    hub._select_model = AsyncMock(return_value=ModelSelection("Granite-4.1-8B-GGUF", "lemonade"))

    client = _RecordingClient(
        get_router={},
        post_router={"/v1/chat/completions": chat_resp},
    )

    with patch("cohezion.integrations.telegram_bot.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = client
        await hub._handle_chat("What is HIHO?")

    # Posted to the lemonade router OpenAI endpoint, not Ollama's /api/chat.
    assert any("13305" in u and "/v1/chat/completions" in u for u in client.post_urls), (
        client.post_urls
    )
    assert not any("/api/chat" in u for u in client.post_urls)
    # Body carries OpenAI fields with the required max_tokens floor.
    assert client.post_bodies, "no POST body recorded"
    body = client.post_bodies[0]
    assert body.get("model") == "Granite-4.1-8B-GGUF"
    assert body.get("max_tokens", 0) >= 512
    assert body.get("stream") is False
    # The sentinel from choices[].message.content reached the user.
    assert any(sentinel in m for m in sent), sent


@pytest.mark.asyncio
async def test_handle_chat_ollama_fallback_uses_api_chat(mock_env):
    """When the selected model came from Ollama, _handle_chat keeps /api/chat."""
    hub = TelegramCommunicationHub()

    reply = "Fallback answer from Ollama."
    chat_resp = _ok_response({"message": {"content": reply}})

    sent: list[str] = []

    async def _capture(text, parse_mode=None):
        sent.append(text)

    hub._send_msg = _capture  # type: ignore[assignment]
    hub._select_model = AsyncMock(return_value=ModelSelection("phi4:latest", "ollama"))

    client = _RecordingClient(
        get_router={},
        post_router={"/api/chat": chat_resp},
    )

    with patch("cohezion.integrations.telegram_bot.httpx") as mock_httpx:
        mock_httpx.AsyncClient.return_value = client
        await hub._handle_chat("hello")

    assert any("/api/chat" in u for u in client.post_urls), client.post_urls
    assert not any("/v1/chat/completions" in u for u in client.post_urls)
    assert any(reply in m for m in sent), sent
