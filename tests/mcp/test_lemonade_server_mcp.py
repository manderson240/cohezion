"""Tests for the Lemonade MCP server.

All real Lemonade HTTP calls are mocked; tests verify tool schema, request
shaping, and response parsing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from cohezion.mcp import lemonade_server_mcp as server


class _FakeResponse:
    def __init__(self, status_code: int = 200, json_data: Any = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._json = json_data
        self.content = content

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses
        self.post = AsyncMock(side_effect=self._post)
        self.get = AsyncMock(side_effect=self._get)

    async def _post(self, url: str, **kwargs: Any) -> _FakeResponse:
        return self._responses.get(url, _FakeResponse(200, {}))

    async def _get(self, url: str, **kwargs: Any) -> _FakeResponse:
        return self._responses.get(url, _FakeResponse(200, {}))

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the module's httpx client factory so all HTTP calls are faked."""
    responses: dict[str, Any] = {}

    def factory() -> _FakeClient:
        return _FakeClient(responses)

    monkeypatch.setattr(server, "_httpx_client", factory)
    return responses


@pytest.mark.anyio
async def test_lemonade_list_models(fake_client: dict[str, Any]) -> None:
    fake_client["http://localhost:13305/v1/models"] = _FakeResponse(
        200, {"data": [{"id": "Gemma-4-E4B-it-GGUF", "object": "model"}]}
    )
    result = await server.lemonade_list_models()
    assert result["count"] == 1
    assert result["models"][0]["id"] == "Gemma-4-E4B-it-GGUF"


@pytest.mark.anyio
async def test_lemonade_load_model_bounds_ctx_size(fake_client: dict[str, Any]) -> None:
    calls: list[dict[str, Any]] = []

    def factory() -> _FakeClient:
        client = _FakeClient({})

        async def post(url: str, **kwargs: Any) -> _FakeResponse:
            calls.append({"url": url, "json": kwargs.get("json")})
            return _FakeResponse(200, {"status": "loaded"})

        client.post = AsyncMock(side_effect=post)
        client.get = AsyncMock(return_value=_FakeResponse(200, {}))
        return client

    import cohezion.mcp.lemonade_server_mcp as s

    original = s._httpx_client
    s._httpx_client = factory
    try:
        result = await server.lemonade_load_model("Gemma-4-E4B-it-GGUF", ctx_size=999999)
        assert result["status"] == "loaded"
        assert calls[0]["json"]["ctx_size"] == 32768
        assert calls[0]["json"]["save_options"] is True
        assert calls[0]["json"]["llamacpp_backend"] == "rocm"
    finally:
        s._httpx_client = original


@pytest.mark.anyio
async def test_lemonade_chat_parses_choice(fake_client: dict[str, Any]) -> None:
    fake_client["http://localhost:13305/v1/chat/completions"] = _FakeResponse(
        200,
        {
            "model": "Gemma-4-E4B-it-GGUF",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello from local Lemonade",
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        },
    )
    result = await server.lemonade_chat([{"role": "user", "content": "hi"}])
    assert result["content"] == "Hello from local Lemonade"
    assert result["usage"]["completion_tokens"] == 5


@pytest.mark.anyio
async def test_lemonade_server_status(fake_client: dict[str, Any]) -> None:
    fake_client["http://localhost:13305/api/v1/status"] = _FakeResponse(200, {"status": "ok"})
    fake_client["http://localhost:13305/v1/models"] = _FakeResponse(200, {"data": []})
    result = await server.lemonade_server_status()
    assert result["status"]["status"] == "ok"
    assert result["base_url"] == "http://localhost:13305"
