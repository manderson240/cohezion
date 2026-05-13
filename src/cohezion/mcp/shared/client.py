"""Generic MCP Client for thin CLI integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from cohezion.mcp.manager.auth import get_current_token


logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with local MCP servers."""

    def __init__(self, base_url: str | None = None, uds_path: str | None = None):
        self.base_url = base_url
        self.uds_path = uds_path
        self._session: aiohttp.ClientSession | None = None
        self._token = get_current_token()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            connector = None
            if self.uds_path:
                connector = aiohttp.UnixConnector(path=self.uds_path)

            headers = {
                "Accept": "application/json",
                "User-Agent": "Cohezion-CLI/1.0",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            self._session = aiohttp.ClientSession(
                connector=connector,
                headers=headers,
            )
        return self._session

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        session = await self._get_session()

        # In our simplified HTTP MCP implementation, tool calls are POST to /tools/{name}
        url = f"{self.base_url}/tools/{tool_name}" if self.base_url else f"http://localhost/tools/{tool_name}"

        try:
            async with session.post(
                url,
                json=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 401:
                    return {"error": "Unauthorized: Invalid or missing token"}

                data = await response.json()
                if response.status != 200:
                    return {"error": data.get("error", f"HTTP {response.status}")}

                return data
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}

    async def get_health(self) -> dict[str, Any]:
        """Check server health."""
        session = await self._get_session()
        url = f"{self.base_url}/health" if self.base_url else "http://localhost/health"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return await response.json()
        except Exception as e:
            return {"error": str(e)}

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
