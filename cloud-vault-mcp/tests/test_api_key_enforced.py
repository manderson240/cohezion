"""The MCP app must enforce MCP_API_KEY.

THE DEFECT (2026-09-21): `APIKeyAuth` existed but was never applied, so the
server answered unauthenticated and wrong-key MCP requests with 200 while
exposed through a public tunnel. Its tools include vault writes/deletes and
SurrealDB queries as root.
"""

import asyncio
import contextlib

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.main import protect_mcp_app


def _inner() -> Starlette:
    async def ok(request):
        return PlainTextResponse("tool")

    return Starlette(routes=[Route("/mcp", ok, methods=["GET", "POST"])])


def test_missing_and_wrong_key_are_refused() -> None:
    client = TestClient(protect_mcp_app(_inner(), api_key="s3cret"))
    assert client.post("/mcp").status_code == 401
    assert (
        client.post("/mcp", headers={"Authorization": "Bearer wrong"}).status_code
        == 403
    )
    assert (
        client.post("/mcp", headers={"Authorization": "Bearer s3cret"}).status_code
        == 200
    )


def test_no_key_configured_leaves_app_unwrapped_but_is_explicit() -> None:
    inner = _inner()
    assert protect_mcp_app(inner, api_key="") is inner


def _served_app(tmp_path, watcher: bool, api_key: str = "s3cret"):
    from mcp_server.config import ServerConfig
    from mcp_server.main import build_app

    config = ServerConfig(
        vault_path=str(tmp_path),
        api_key=api_key,
        watcher_enabled=watcher,
        allowed_hosts=["*"],
        tls_enabled=False,
    )
    return build_app(config, _inner())


@pytest.mark.parametrize("watcher", [True, False])
def test_served_app_requires_the_key_on_every_route_but_health(
    tmp_path, watcher
) -> None:
    """Behavioural (replaces a source grep): the COMPOSED app main() serves."""
    client = TestClient(_served_app(tmp_path, watcher))
    assert client.post("/mcp").status_code == 401
    assert (
        client.post("/mcp", headers={"Authorization": "Bearer wrong"}).status_code
        == 403
    )
    assert (
        client.post("/mcp", headers={"Authorization": "Bearer s3cret"}).status_code
        == 200
    )
    assert client.get("/health").status_code not in (401, 403)


def _response_status(
    app, path: str, headers: dict[str, str] | None = None
) -> int | None:
    """Status of the first response start; never reads the (endless) SSE body."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "scheme": "http",
        "http_version": "1.1",
        "server": ("test", 80),
        "client": ("test", 1),
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
    }
    sent: list[int] = []

    async def receive():
        await asyncio.sleep(0 if not sent else 3600)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            sent.append(message["status"])

    async def run():
        task = asyncio.ensure_future(app(scope, receive, send))
        for _ in range(1000):  # the SSE body never ends: stop once the status is known
            if sent or task.done():
                break
            await asyncio.sleep(0.01)
        task.cancel()

    # A fresh loop closed WITHOUT draining: the SSE generator swallows cancellation, so
    # waiting for it (as asyncio.run does) would hang exactly when the route is open.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        with contextlib.suppress(Exception):
            loop.close()
    return sent[0] if sent else None


def test_vault_event_stream_is_not_routed_around_the_key(tmp_path) -> None:
    """M2 (2026-09-22): /events/vault went to the SSE app before the key check."""
    app = _served_app(tmp_path, watcher=True)
    assert _response_status(app, "/events/vault") == 401
    assert (
        _response_status(app, "/events/vault", {"Authorization": "Bearer wrong"}) == 403
    )


@pytest.mark.parametrize(
    ("host", "optout", "starts"),
    [
        ("0.0.0.0", "1", False),  # noqa: S104  # never unauthenticated off-loopback
        ("127.0.0.1", "", False),  # loopback alone is not enough: tunnels hit localhost
        ("127.0.0.1", "1", True),  # explicit local-dev opt-out
    ],
)
def test_empty_key_refuses_to_start(monkeypatch, host, optout, starts) -> None:
    """M3 (2026-09-22): an empty MCP_API_KEY served every tool unauthenticated."""
    from mcp_server.config import ServerConfig
    from mcp_server.main import check_auth_config

    monkeypatch.setenv("MCP_ALLOW_NO_AUTH", optout)
    config = ServerConfig(api_key="", host=host)
    if starts:
        check_auth_config(config)
    else:
        with pytest.raises(SystemExit):
            check_auth_config(config)


def test_configured_key_always_starts() -> None:
    from mcp_server.config import ServerConfig
    from mcp_server.main import check_auth_config

    check_auth_config(ServerConfig(api_key="k", host="0.0.0.0"))  # noqa: S104
