"""Vault MCP client auth: no hardcoded key, and a rejected key fails loudly once (ops C1).

2026-09-22 ops review: ``get_mcp_client`` defaulted CLOUD_VAULT_API_KEY to the literal
"cohezion-dev-key". No unit sets that variable; the vault server enforces MCP_API_KEY. So
after a vault restart every in-repo caller got 403, ``_call_tool`` rewrapped it as a
generic MCPToolError, and most callers swallowed that at DEBUG -- silent, while /health
(auth-exempt) stayed green.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest

from cohezion.core import mcp_client as mc


SECRET = "s3cr3t-value-that-must-never-be-logged"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in ("CLOUD_VAULT_API_KEY", "MCP_API_KEY", "CLOUD_VAULT_API_KEY_FILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(mc, "_mcp_client_instance", None)


def _fake_server(monkeypatch, *, init_status=200, tool_status=200):
    """Route every httpx.AsyncClient through an in-process fake; returns the request log."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = request.read().decode()
        status = init_status if '"initialize"' in body else tool_status
        if status != 200:
            return httpx.Response(status, json={"error": "Invalid API key"})
        text = 'data: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"ok"}]}}\n'
        return httpx.Response(200, text=text)

    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(mc.httpx, "AsyncClient", factory)
    return seen


def test_no_hardcoded_default_key(monkeypatch):
    assert mc.get_mcp_client().config.api_key == ""


def test_key_resolution_order(monkeypatch, tmp_path):
    key_file = tmp_path / "key"
    key_file.write_text(SECRET + "\n")
    monkeypatch.setenv("CLOUD_VAULT_API_KEY_FILE", str(key_file))
    assert mc.resolve_api_key() == SECRET
    monkeypatch.setenv("MCP_API_KEY", "server-var")
    assert mc.resolve_api_key() == "server-var"
    monkeypatch.setenv("CLOUD_VAULT_API_KEY", "client-var")
    assert mc.resolve_api_key() == "client-var"


def test_rejected_key_raises_auth_error_once_and_never_logs_the_key(monkeypatch, caplog):
    seen = _fake_server(monkeypatch, init_status=403)
    client = mc.MCPClient(mc.MCPConfig(server_url="http://vault", api_key=SECRET))
    caplog.set_level(logging.DEBUG, logger=mc.__name__)
    with pytest.raises(mc.MCPAuthenticationError, match="CLOUD_VAULT_API_KEY"):
        asyncio.run(client.vault_read("a.md"))
    n = len(seen)
    for _ in range(3):  # no retry loop: later calls fail fast without a request
        with pytest.raises(mc.MCPAuthenticationError):
            asyncio.run(client.vault_read("a.md"))
    assert len(seen) == n
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1 and "403" in errors[0].getMessage()
    assert SECRET not in caplog.text


def test_rejection_on_a_tool_call_is_an_auth_error_too(monkeypatch):
    _fake_server(monkeypatch, tool_status=401)
    client = mc.MCPClient(mc.MCPConfig(server_url="http://vault", api_key="k"))
    with pytest.raises(mc.MCPAuthenticationError):
        asyncio.run(client.vault_read("a.md"))


def test_best_effort_wrappers_still_surface_auth_at_error(monkeypatch, caplog):
    _fake_server(monkeypatch, init_status=403)
    client = mc.MCPClient(mc.MCPConfig(server_url="http://vault", api_key="k"))
    caplog.set_level(logging.DEBUG, logger=mc.__name__)
    assert client.vault_read_sync("a.md") == ""
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_empty_key_sends_no_bearer_header(monkeypatch):
    seen = _fake_server(monkeypatch)
    client = mc.MCPClient(mc.MCPConfig(server_url="http://vault", api_key=""))
    assert asyncio.run(client.vault_read("a.md")) == "ok"
    assert "authorization" not in seen[0].headers
