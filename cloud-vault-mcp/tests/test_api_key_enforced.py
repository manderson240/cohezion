"""The MCP app must enforce MCP_API_KEY.

THE DEFECT (2026-09-21): `APIKeyAuth` existed but was never applied, so the
server answered unauthenticated and wrong-key MCP requests with 200 while
exposed through a public tunnel. Its tools include vault writes/deletes and
SurrealDB queries as root.
"""

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


def test_main_applies_protection() -> None:
    import inspect

    from mcp_server import main as m

    assert "protect_mcp_app(mcp_app" in inspect.getsource(m.main)
