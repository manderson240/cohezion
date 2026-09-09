# binds 0.0.0.0 in dev/internal services
"""WebMCP Bridge - Routes browser tool calls to real MCP server handlers.

Connects the browser-based AG-UI to the MCP fleet by looking up servers
in the registry and dispatching tool calls to their Python handlers.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from typing import Any

import httpx
from aiohttp import web

from cohezion.mcp.registry import get_registry


logger = logging.getLogger(__name__)

# Allowed name pattern: alphanumeric, hyphens, underscores; max 64 chars
_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")

# SSRF guard: MCP server URLs must be localhost HTTPS/HTTP endpoints. The
# registry is populated from local config, but the bridge is reachable from the
# browser (AG-UI), so every outbound URL is re-validated here before httpx is
# invoked. Non-http(s) schemes and non-local hosts are rejected (fail closed).
_ALLOWED_URL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _validate_server_url(url: str) -> bool:
    """Return True only for http(s) URLs pointing at an allowlisted local host."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.hostname is None:
        return False
    return parsed.hostname.lower() in _ALLOWED_URL_HOSTS


class WebMCPBridge:
    """Routes browser MCP tool calls to real server handlers."""

    def __init__(self, port: int = 8380) -> None:
        self.port = port
        self.registry = get_registry()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.add_routes(
            [
                web.get("/.well-known/model-context.json", self.handle_context),
                web.get("/mcp/list_servers", self.handle_list_servers),
                web.post("/mcp/call_tool", self.handle_call_tool),
            ]
        )

    @staticmethod
    def _validate_name(name: str) -> bool:
        """Validate server/tool names to prevent injection attacks."""
        if not name:
            return False
        return bool(_NAME_RE.match(name))

    async def handle_context(self, request: web.Request) -> web.Response:
        """Returns the model-context.json for MCP discovery."""
        servers = self.registry.list_servers()

        # Robust port mapping matching defaults.py and fleet.py
        port_map = {
            "vault": 8360,
            "cloud-vault-mcp": 8360,
            "bmad": 8361,
            "cohezion-bmad": 8361,
            "skills": 8362,
            "cohezion-skills": 8362,
            "doc-retriever": 8364,
            "huggingface": 8365,
            "cohezion-huggingface": 8365,
            "huggingface-skills": 8365,
            "memory": 8366,
            "cohezion-memory": 8366,
            "sequential-thinking": 8367,
            "git-context": 8368,
            "security": 8369,
            "cohezion-security": 8369,
            "knowledge": 8371,
            "cohezion-knowledge": 8371,
            "swarm": 8372,
            "cohezion-swarm": 8372,
            "research": 8373,
            "cohezion-research": 8373,
            "coherence": 8374,
            "cohezion-coherence": 8374,
            "surreal": 8375,
            "cohezion-surreal": 8375,
            "journey": 8376,
            "cohezion-journey": 8376,
            "github": 8377,
            "cohezion-github": 8377,
            "agentskills": 8378,
            "cohezion-agentskills": 8378,
            "compound": 8379,
            "cohezion-compound": 8379,
        }

        context = {
            "mcpServers": {
                s.name: {
                    "url": s.url
                    if s.url and s.url != "local"
                    else f"http://localhost:{port_map.get(s.name, 8360 + servers.index(s))}",
                    "description": s.description,
                }
                for s in servers
                if s.status == "available" or s.url or s.name in port_map
            }
        }
        return web.json_response(context)

    async def handle_list_servers(self, request: web.Request) -> web.Response:
        servers = self.registry.list_servers()
        return web.json_response([s.to_dict() for s in servers])

    async def handle_call_tool(self, request: web.Request) -> web.Response:
        """Route a tool call to the actual MCP server handler."""
        server_name = ""
        try:
            data = await request.json()
            server_name = str(data.get("server", ""))
            tool_name = str(data.get("tool", ""))
            arguments: dict[str, Any] = data.get("arguments", {})

            # Validate names
            if not self._validate_name(server_name):
                return web.json_response(
                    {"success": False, "error": f"Invalid server name: {server_name!r}"},
                    status=400,
                )
            if not self._validate_name(tool_name):
                return web.json_response(
                    {"success": False, "error": f"Invalid tool name: {tool_name!r}"},
                    status=400,
                )

            logger.info("WebMCP Call: %s.%s(%s)", server_name, tool_name, arguments)

            # Look up server in registry
            server = self.registry.get_server(server_name)
            if server is None:
                return web.json_response(
                    {"success": False, "error": f"Server not found: {server_name}"},
                    status=404,
                )

            # Route to the server's HTTP endpoint if it has a URL. The URL is
            # registry-provided but browser-reachable, so re-validate the
            # destination against the local-host allowlist BEFORE any httpx
            # call (SSRF guard; fail closed with a 400).
            if server.url:
                if not _validate_server_url(server.url):
                    logger.warning(
                        "Blocked WebMCP call to non-allowlisted server URL: %s",
                        server_name,
                    )
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Server URL not allowed: {server_name}",
                        },
                        status=400,
                    )
                result = await self._call_http_server(server.url, tool_name, arguments)
            else:
                # Internal server without URL — call via local module dispatch
                result = await self._call_internal_server(server_name, tool_name, arguments)

            return web.json_response({"success": True, "result": result, "server": server_name})

        except httpx.ConnectError:
            return web.json_response(
                {"success": False, "error": f"Server {server_name} is offline"},
                status=503,
            )
        except Exception as e:
            logger.exception("WebMCP call failed")
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _call_http_server(
        self, base_url: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Call an HTTP-based MCP server.

        The destination is re-validated here (defense-in-depth): non-allowlisted
        hosts raise before httpx is ever invoked.
        """
        if not _validate_server_url(base_url):
            raise ValueError(f"Refusing to call non-allowlisted MCP server URL: {base_url!r}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base_url}/tools/{tool_name}",
                json=arguments,
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_internal_server(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Dispatch to a local Python MCP server handler."""
        # Lazy-import server modules to avoid circular imports
        handler = self._resolve_internal_handler(server_name, tool_name)
        if handler is None:
            return {"error": f"No handler for {server_name}.{tool_name}"}

        if asyncio.iscoroutinefunction(handler):
            return await handler(**arguments)
        return handler(**arguments)

    def _resolve_internal_handler(self, server_name: str, tool_name: str) -> Any | None:
        """Resolve a Python handler function for an internal MCP tool."""
        # Map server names to their handler modules
        try:
            if server_name == "knowledge":
                from cohezion.mcp.knowledge_server import get_server

                srv = get_server()
                return getattr(srv, tool_name, None)
            if server_name == "swarm":
                from cohezion.mcp.swarm_server import get_server

                srv = get_server()
                return getattr(srv, tool_name, None)
        except Exception:
            logger.warning("Failed to resolve handler for %s.%s", server_name, tool_name)
        return None

    async def start(self) -> None:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        logger.info("WebMCP Bridge started on port %d", self.port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bridge = WebMCPBridge()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bridge.start())
    loop.run_forever()
