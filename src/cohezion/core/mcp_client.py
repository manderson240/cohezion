"""MCP client for Cloud Vault operations.

Connects to the Cloud Vault MCP Server using streamable-http protocol
to enable compound engineering workflows with persistent knowledge storage.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_mcp_client_instance: MCPClient | None = None


def _parse_sse_response(text: str) -> dict[str, Any]:
    """Parse Server-Sent Events response to extract JSON-RPC data."""
    # SSE format: "event: message\ndata: {...json...}\n\n"
    lines = text.strip().split("\n")
    for line in lines:
        if line.startswith("data: "):
            json_str = line[6:]  # Remove "data: " prefix
            return json.loads(json_str)  # type: ignore[no-any-return]
    raise ValueError("No data found in SSE response")


@dataclass
class MCPConfig:
    """Configuration for MCP client connection."""

    server_url: str
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class MCPConnectionError(MCPClientError):
    """Connection to MCP server failed."""


class MCPAuthenticationError(MCPClientError):
    """Authentication with MCP server failed."""


class MCPToolError(MCPClientError):
    """MCP tool execution failed."""


class MCPClient:
    """Async Client for Cloud Vault MCP Server operations."""

    def __init__(self, config: MCPConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None

    async def __aenter__(self) -> MCPClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> None:
        """Establish connection to MCP server and initialize session."""
        if self._client is not None:
            return

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        self._client = httpx.AsyncClient(
            base_url=self.config.server_url,
            headers=headers,
            timeout=self.config.timeout,
        )

        # Initialize MCP session
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "cohezion-mcp-client", "version": "1.0"},
                },
            }
            response = await self._client.post("/mcp", json=payload)
            response.raise_for_status()

            # Extract session ID from response headers
            session_id = response.headers.get("mcp-session-id")
            if session_id:
                self._session_id = session_id
                logger.info(f"MCP session initialized: {session_id}")
            else:
                self._session_id = "stateless"
                logger.info("Connected to stateless MCP server")

        except httpx.HTTPStatusError as e:
            await self.close()
            if e.response.status_code in (401, 403):
                raise MCPAuthenticationError(f"Authentication failed (HTTP {e.response.status_code})") from e
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}") from e
        except httpx.RequestError as e:
            await self.close()
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}") from e
        except Exception as e:
            await self.close()
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}") from e

    async def close(self) -> None:
        """Close connection and cleanup session."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._session_id = None

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Invoke an MCP tool via the initialized session."""
        if not self._client:
            await self.connect()

        if self._client is None:
            raise MCPConnectionError("Client not connected after connect() call")

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        headers = {}
        if self._session_id and self._session_id != "stateless":
            headers["mcp-session-id"] = self._session_id

        try:
            response = await self._client.post("/mcp", json=payload, headers=headers)
            response.raise_for_status()

            result = _parse_sse_response(response.text)
            if "error" in result:
                raise MCPToolError(f"Tool '{tool_name}' failed: {result['error']}")

            # FastMCP returns {content: [{type: 'text', text: '...'}]}
            content = result.get("result", {}).get("content", [])
            if content and content[0].get("type") == "text":
                return content[0].get("text")
            return result.get("result")

        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            raise MCPToolError(f"Failed to call tool '{tool_name}': {e}") from e

    # ── Vault Operations ──────────────────────────────────────────────

    async def vault_read(self, path: str) -> str:
        return await self._call_tool("vault_read", {"path": path})

    async def vault_write(self, path: str, content: str) -> str:
        return await self._call_tool("vault_write", {"path": path, "content": content})

    async def vault_delete(self, path: str) -> str:
        return await self._call_tool("vault_delete", {"path": path})

    async def vault_log_decision(
        self,
        project: str,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        **kwargs,
    ) -> str:
        args = {
            "project": project,
            "title": title,
            "context": context,
            "decision": decision,
            "rationale": rationale,
        }
        args.update(kwargs)
        return await self._call_tool("vault_log_decision", args)

    async def vault_find_relevant_context(
        self, query: str, project: str = "cohezion", limit: int = 10
    ) -> list[dict[str, Any]]:
        raw = await self._call_tool(
            "vault_find_relevant_context",
            {"query": query, "project": project, "limit": limit},
        )
        if isinstance(raw, str):
            return json.loads(raw)
        return raw or []

    async def vault_edit(self, path: str, edits: list[dict[str, Any]]) -> None:
        await self._call_tool("vault_edit", {"path": path, "edits": edits})

    async def vault_log_experiment(
        self,
        project: str,
        hypothesis: str,
        method: str,
        result: str = "",
        learnings: str = "",
        title: str = "",
        **kwargs,
    ) -> str:
        args = {
            "project": project,
            "hypothesis": hypothesis,
            "method": method,
            "result": result,
            "learnings": learnings,
            "title": title,
        }
        args.update(kwargs)
        return await self._call_tool("vault_log_experiment", args)

    async def vault_extract_pattern(self, source_path: str, pattern_name: str, description: str, **kwargs) -> str:
        args = {
            "source_path": source_path,
            "pattern_name": pattern_name,
            "description": description,
        }
        args.update(kwargs)
        return await self._call_tool("vault_extract_pattern", args)

    def vault_search(self, query: str, limit: int = 20) -> list[dict]:
        """Search vault patterns by full-text query. Returns list of match dicts."""
        try:
            raw = self._call_tool("vault_search", {"query": query, "limit": limit})
            if isinstance(raw, list):
                return raw
            return []
        except Exception:
            return []

    def vault_search_by_operation(self, operation: str, limit: int = 20) -> list[dict]:
        """Hierarchical search by operation folder; falls back to full-text if empty."""
        try:
            results = self.vault_search(f"patterns/operations/{operation}", limit=limit)
            filtered = [r for r in results if operation in r.get("path", "")]
            if not filtered:
                filtered = self.vault_search(operation, limit=limit)
            return filtered[:limit]
        except Exception:
            return []

    def vault_search_by_domain(self, domain: str, limit: int = 20) -> list[dict]:
        """Hierarchical search: filter patterns by domain folder prefix."""
        try:
            results = self.vault_search(f"patterns/domains/{domain}", limit=limit)
            filtered = [r for r in results if domain in r.get("path", "")]
            return filtered[:limit]
        except Exception:
            return []

    def vault_search_by_skill_category(self, category: str, limit: int = 20) -> list[dict]:
        """Hierarchical search: filter patterns by skill category folder prefix."""
        try:
            results = self.vault_search(f"patterns/skills/{category}", limit=limit)
            filtered = [r for r in results if category in r.get("path", "")]
            return filtered[:limit]
        except Exception:
            return []

    def vault_search_hierarchical(
        self,
        operation_type: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Combined hierarchical search across operation, domain, and skill category."""
        parts = []
        if operation_type:
            parts.append(f"operations/{operation_type}")
        if domain:
            parts.append(f"domains/{domain}")
        if category:
            parts.append(f"skills/{category}")
        query = "/".join(parts) if parts else ""
        try:
            results = self.vault_search(query, limit=limit)
            return results[:limit]
        except Exception:
            return []


def create_mcp_client(server_url: str, api_key: str) -> MCPClient:
    return MCPClient(MCPConfig(server_url=server_url, api_key=api_key))


def get_mcp_client() -> MCPClient:
    global _mcp_client_instance
    if _mcp_client_instance is None:
        server_url = os.getenv("CLOUD_VAULT_URL", "http://localhost:8360")
        api_key = os.getenv("CLOUD_VAULT_API_KEY", "cohezion-dev-key")
        _mcp_client_instance = create_mcp_client(server_url=server_url, api_key=api_key)
    return _mcp_client_instance
