"""Every Cohezion MCP server that listens on HTTP checks MCP_API_KEY.

Before 2026-11-06, 11 servers had no auth at all. These tests check the app each
server actually serves, so they fail if a server drops the middleware.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from cohezion.mcp.shared import auth


KEY = "test-key-not-a-secret"
MCP_SRC = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "mcp"


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.setattr(auth, "get_api_key", lambda: KEY)


@pytest.fixture
def without_key(monkeypatch):
    monkeypatch.setattr(auth, "get_api_key", lambda: None)


def _client():
    starlette = pytest.importorskip("starlette")
    del starlette
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def ok(request):
        return PlainTextResponse("ok")

    inner = Starlette(routes=[Route("/health", ok), Route("/mcp", ok, methods=["POST"])])
    return TestClient(auth.BearerAuthASGI(inner))


class TestBearerAuthASGI:
    def test_missing_key_is_rejected(self, with_key):
        assert _client().post("/mcp").status_code == 401

    def test_wrong_key_is_rejected(self, with_key):
        resp = _client().post("/mcp", headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401

    def test_right_key_is_accepted(self, with_key):
        resp = _client().post("/mcp", headers={"Authorization": f"Bearer {KEY}"})
        assert resp.status_code == 200

    def test_server_without_a_key_refuses_everything(self, without_key):
        resp = _client().post("/mcp", headers={"Authorization": "Bearer anything"})
        assert resp.status_code == 500

    def test_health_is_open(self, without_key):
        assert _client().get("/health").status_code == 200


class TestServeFastmcpHttp:
    def test_runs_behind_the_key_check(self, monkeypatch):
        monkeypatch.delenv("MCP_HOST", raising=False)
        captured = {}

        class FakeApp:
            def run(self, **kwargs):
                captured.update(kwargs)

        auth.serve_fastmcp_http(FakeApp(), 9999)
        assert captured["host"] == "127.0.0.1"
        assert [m.cls for m in captured["middleware"]] == [auth.BearerAuthASGI]


def test_auth_headers_carry_the_key(with_key):
    assert auth.auth_headers() == {"Authorization": f"Bearer {KEY}"}


@pytest.mark.parametrize(
    "module",
    [
        "cohezion.mcp.knowledge_server",
        "cohezion.mcp.research_server",
        "cohezion.mcp.swarm_server",
    ],
)
def test_aiohttp_servers_use_the_middleware(module):
    try:
        mod = importlib.import_module(module)
    except ImportError as err:
        pytest.skip(f"{module} needs an optional dependency: {err}")
    assert auth.api_key_middleware in mod.create_app().middlewares


def test_webmcp_bridge_uses_the_middleware():
    try:
        from cohezion.mcp.webmcp_bridge import WebMCPBridge
    except ImportError as err:
        pytest.skip(f"webmcp_bridge needs an optional dependency: {err}")
    assert auth.api_key_middleware in WebMCPBridge().app.middlewares


def test_no_server_runs_fastmcp_over_http_directly():
    """Consumption: any ``.run(..., host=...)`` bypasses the key check. Only
    ``serve_fastmcp_http`` may pass a host."""
    offenders = []
    for path in MCP_SRC.rglob("*.py"):
        if path.name == "auth.py" and path.parent.name == "shared":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and any(kw.arg == "host" for kw in node.keywords)
            ):
                offenders.append(f"{path.relative_to(MCP_SRC).as_posix()}:{node.lineno}")
    assert not offenders, f"Use cohezion.mcp.shared.auth.serve_fastmcp_http: {offenders}"
