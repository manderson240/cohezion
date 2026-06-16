"""Cohezion MCP tool bridge — the qualifying MCP integration for Slack Agent Builder Challenge.

Wraps Cohezion's compound AI as MCP-compatible tools that the Slack agent can call.
The MCP server (mcp_server.py) exposes these tools over HTTP; this client calls them.

MCP Tool Registry:
  cohezion_ask          — Q&A via compound loop (NPU→iGPU→CPU routing)
  cohezion_code_review  — 3-agent code review pipeline
  cohezion_search       — FLUME VAE 256D semantic search
  cohezion_get_status   — AMD silicon health check
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests


class CohezionMCPClient:
    """Bridges Cohezion compound AI to MCP tool protocol.

    Two modes:
    - Live: calls the MCP server at MCP_SERVER_URL (default localhost:8765)
    - Direct: calls Cohezion handlers directly (for local dev without MCP server)
    """

    TOOLS = [
        {
            "name": "cohezion_ask",
            "description": "Answer a question using Cohezion's compound AI (NPU→iGPU→CPU routing, $0/query on AMD silicon)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to answer"},
                    "tier": {"type": "string", "enum": ["auto", "npu", "igpu", "cpu"], "default": "auto"},
                },
                "required": ["question"],
            },
        },
        {
            "name": "cohezion_code_review",
            "description": "Run a 3-agent code review pipeline (Orchestrator → Analyst → Engineer)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Code review task description"},
                },
                "required": ["task"],
            },
        },
        {
            "name": "cohezion_search",
            "description": "Semantic search via FLUME VAE 256D embeddings across Cohezion knowledge vault",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "default": 3, "description": "Number of results"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "cohezion_get_status",
            "description": "Check AMD silicon inference tiers (NPU/iGPU/CPU) and cache health",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]

    def __init__(self):
        self._mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8765")
        self._use_direct = not self._mcp_server_reachable()

    def _mcp_server_reachable(self) -> bool:
        try:
            resp = requests.get(f"{self._mcp_url}/health", timeout=1)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def list_tools(self) -> list[dict]:
        """Return the MCP tool manifest."""
        if not self._use_direct:
            try:
                resp = requests.post(
                    f"{self._mcp_url}/mcp/tools/list",
                    json={},
                    timeout=5,
                )
                if resp.status_code == 200:
                    return resp.json().get("tools", self.TOOLS)
            except requests.RequestException:
                pass
        return self.TOOLS

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a Cohezion MCP tool and return the result.

        Routes through the MCP server if available, falls back to direct call.
        """
        if not self._use_direct:
            try:
                resp = requests.post(
                    f"{self._mcp_url}/mcp/tools/call",
                    json={"name": tool_name, "arguments": arguments},
                    timeout=60,
                )
                if resp.status_code == 200:
                    return resp.json()
            except requests.RequestException:
                self._use_direct = True

        # Direct dispatch (no MCP server)
        return self._direct_dispatch(tool_name, arguments)

    def _direct_dispatch(self, tool_name: str, arguments: dict) -> dict:
        """Call Cohezion handlers directly without MCP server."""
        if tool_name == "cohezion_ask":
            from handlers.ask_handler import handle_ask  # noqa: PLC0415
            result = handle_ask(
                question=arguments["question"],
                tier=arguments.get("tier", "auto"),
            )
            return {"content": [{"type": "text", "text": result["answer"]}], "meta": result}

        if tool_name == "cohezion_code_review":
            from handlers.review_handler import handle_review  # noqa: PLC0415
            result = handle_review(task=arguments["task"])
            return {"content": [{"type": "text", "text": result["summary"]}], "meta": result}

        if tool_name == "cohezion_search":
            from handlers.search_handler import handle_search  # noqa: PLC0415
            result = handle_search(
                query=arguments["query"],
                top_k=arguments.get("top_k", 3),
            )
            return {"content": [{"type": "text", "text": result["formatted"]}], "meta": result}

        if tool_name == "cohezion_get_status":
            from handlers.status_handler import handle_status  # noqa: PLC0415
            result = handle_status()
            return {"content": [{"type": "text", "text": result["text"]}], "meta": result}

        return {"error": f"Unknown tool: {tool_name}"}
