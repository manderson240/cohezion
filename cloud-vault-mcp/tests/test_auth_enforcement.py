"""The API key is enforced, and the server refuses to start without one.

Before this test existed, ``APIKeyAuth`` was defined in ``auth.py`` and used nowhere:
setting ``MCP_API_KEY`` changed nothing, and every tool was open to anyone who could
reach the port or the tunnel. These tests check the assembled app that ``main()``
hands to uvicorn, so they fail if the wrapper is dropped from ``main.py``.
"""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server import main as main_module
from mcp_server.auth import AuthConfigError, check_auth_config, require_bearer


KEY = "test-key-not-a-secret"


def _app():
    async def ok(request):
        return PlainTextResponse("ok")

    return Starlette(
        routes=[Route("/health", ok), Route("/mcp", ok, methods=["GET", "POST"])]
    )


class TestRequireBearer:
    def test_missing_key_is_rejected(self):
        client = TestClient(require_bearer(_app(), KEY))
        assert client.get("/mcp").status_code == 401

    def test_wrong_key_is_rejected(self):
        client = TestClient(require_bearer(_app(), KEY))
        assert (
            client.get("/mcp", headers={"Authorization": "Bearer nope"}).status_code
            == 401
        )

    def test_right_key_is_accepted(self):
        client = TestClient(require_bearer(_app(), KEY))
        resp = client.get("/mcp", headers={"Authorization": f"Bearer {KEY}"})
        assert resp.status_code == 200 and resp.text == "ok"

    def test_health_stays_open_for_monitoring(self):
        client = TestClient(require_bearer(_app(), KEY))
        assert client.get("/health").status_code == 200


class TestCheckAuthConfig:
    def test_no_key_refuses_to_start(self):
        with pytest.raises(AuthConfigError):
            check_auth_config("", "127.0.0.1", allow_no_auth=False)

    def test_opt_out_is_refused_beyond_loopback(self):
        with pytest.raises(AuthConfigError):
            check_auth_config("", "0.0.0.0", allow_no_auth=True)  # noqa: S104

    def test_opt_out_on_loopback_is_allowed(self):
        check_auth_config("", "127.0.0.1", allow_no_auth=True)

    def test_key_is_enough(self):
        check_auth_config(KEY, "0.0.0.0", allow_no_auth=False)  # noqa: S104


class TestMainWiring:
    """Consumption: the app main() gives uvicorn must enforce the key."""

    def _served_app(self, monkeypatch, tmp_path, key):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path))
        monkeypatch.setenv("MCP_API_KEY", key)
        monkeypatch.setenv("MCP_HOST", "127.0.0.1")
        monkeypatch.setenv("WATCHER_ENABLED", "false")
        monkeypatch.setenv("SHEETS_ENABLED", "false")
        monkeypatch.setenv("SURREALDB_ENABLED", "false")
        monkeypatch.setenv("TLS_ENABLED", "false")
        served = {}
        monkeypatch.setattr(
            main_module.uvicorn, "run", lambda app, **kw: served.update(app=app, **kw)
        )
        main_module.main()
        return served

    def test_served_app_rejects_requests_without_the_key(self, monkeypatch, tmp_path):
        served = self._served_app(monkeypatch, tmp_path, KEY)
        assert served["host"] == "127.0.0.1"
        client = TestClient(served["app"])
        assert client.post("/mcp", json={}).status_code == 401

    def test_main_refuses_to_start_without_a_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("MCP_ALLOW_NO_AUTH", raising=False)
        with pytest.raises(SystemExit):
            self._served_app(monkeypatch, tmp_path, "")

    def test_default_host_is_loopback(self, monkeypatch):
        monkeypatch.delenv("MCP_HOST", raising=False)
        assert main_module.ServerConfig.from_env().host == "127.0.0.1"
