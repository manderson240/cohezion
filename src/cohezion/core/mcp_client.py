"""MCP client for Cloud Vault operations.

Connects to the Cloud Vault MCP Server using streamable-http protocol
to enable compound engineering workflows with persistent knowledge storage.
"""

from __future__ import annotations

import asyncio
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
                raise MCPAuthenticationError(
                    f"Authentication failed (HTTP {e.response.status_code})"
                ) from e
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

        except MCPToolError:
            raise
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

    async def vault_extract_pattern(
        self, source_path: str, pattern_name: str, description: str, **kwargs
    ) -> str:
        args = {
            "source_path": source_path,
            "pattern_name": pattern_name,
            "description": description,
        }
        args.update(kwargs)
        return await self._call_tool("vault_extract_pattern", args)

    # ── Hierarchical Vault Search (synchronous wrappers) ──────────────
    #
    # Synchronous companions to the async vault operations above. Blocking
    # callers like ``cohezion.cache.semantic_cache`` dispatch them via
    # ``loop.run_in_executor`` and ``request_cache`` / ``batch_sizer`` use
    # them as plain callables. Tests stub them with ``patch.object``.

    def vault_write_sync(self, path: str, content: str) -> None:
        """Synchronous fire-and-forget wrapper for vault_write.

        Safe to call from synchronous code. Best-effort — errors never raise.
        If an event loop is already running the coroutine is scheduled as a
        background task; otherwise ``asyncio.run`` is used.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running — safe to use asyncio.run
            try:
                asyncio.run(self.vault_write(path, content))
            except Exception as e:
                logger.debug("vault_write_sync failed: %s", e)
            return

        # Inside a running loop — schedule fire-and-forget
        loop.create_task(self.vault_write(path, content))

    def vault_read_sync(self, path: str) -> str:
        """Synchronous wrapper for vault_read.

        Safe to call from synchronous code. Best-effort — errors return empty
        string. If an event loop is already running the call is **dropped** and
        an empty string is returned (blocking the loop would deadlock).
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running — safe to use asyncio.run
            try:
                return asyncio.run(self.vault_read(path))
            except Exception as e:
                logger.debug("vault_read_sync failed: %s", e)
                return ""

        # Inside a running loop — cannot block; return default
        logger.debug("vault_read_sync called inside running loop — dropped")
        return ""

    def vault_delete_sync(self, path: str) -> None:
        """Synchronous fire-and-forget wrapper for vault_delete.

        Safe to call from synchronous code. Best-effort — errors never raise.
        If an event loop is already running the coroutine is scheduled as a
        background task; otherwise ``asyncio.run`` is used.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running — safe to use asyncio.run
            try:
                asyncio.run(self.vault_delete(path))
            except Exception as e:
                logger.debug("vault_delete_sync failed: %s", e)
            return

        # Inside a running loop — schedule fire-and-forget
        loop.create_task(self.vault_delete(path))

    def vault_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Synchronously search the vault for content matching ``query``.

        Thin sync wrapper around :meth:`vault_find_relevant_context` so the
        method is patchable and dispatchable via ``run_in_executor``. Errors
        are swallowed and returned as an empty list — search is best-effort
        and must never crash the caller.
        """
        coro = self.vault_find_relevant_context(query, limit=limit)
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # Loop already running (e.g. pytest-asyncio) — cannot block.
            # Callers in async contexts should await
            # :meth:`vault_find_relevant_context` directly.
            return []
        except Exception as exc:
            logger.debug("vault_search failed: %s", exc)
            return []

    def vault_search_by_operation(
        self, operation: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Hierarchical search for patterns under ``operations/<operation>``.

        Tries the folder-scoped lookup first; if it returns no rows, falls
        back to a flat full-text query for the same term. Returns at most
        ``limit`` rows.
        """
        try:
            results = self.vault_search(f"operations/{operation}", limit=limit)
            if not results:
                results = self.vault_search(operation, limit=limit)
            return list(results)[:limit]
        except Exception as exc:
            logger.debug("vault_search_by_operation failed: %s", exc)
            return []

    def vault_search_by_domain(
        self, domain: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Hierarchical search for patterns under ``domains/<domain>``."""
        try:
            results = self.vault_search(f"domains/{domain}", limit=limit)
            if not results:
                results = self.vault_search(domain, limit=limit)
            return list(results)[:limit]
        except Exception as exc:
            logger.debug("vault_search_by_domain failed: %s", exc)
            return []

    def vault_search_by_skill_category(
        self, category: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Hierarchical search for patterns under ``skills/<category>``."""
        try:
            results = self.vault_search(f"skills/{category}", limit=limit)
            if not results:
                results = self.vault_search(category, limit=limit)
            return list(results)[:limit]
        except Exception as exc:
            logger.debug("vault_search_by_skill_category failed: %s", exc)
            return []

    def vault_search_hierarchical(
        self,
        operation_type: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Combined hierarchical search across operation/domain/category.

        Builds a single folder-scoped query of the form
        ``operations/<op>/domains/<dom>/skills/<cat>`` and issues one
        :meth:`vault_search` call. Returns at most ``limit`` rows; missing
        criteria are simply omitted from the path.
        """
        parts: list[str] = []
        if operation_type:
            parts.append(f"operations/{operation_type}")
        if domain:
            parts.append(f"domains/{domain}")
        if category:
            parts.append(f"skills/{category}")
        query = "/".join(parts) if parts else ""
        try:
            return list(self.vault_search(query, limit=limit))[:limit]
        except Exception as exc:
            logger.debug("vault_search_hierarchical failed: %s", exc)
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
