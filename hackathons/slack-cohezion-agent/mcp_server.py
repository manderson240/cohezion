#!/usr/bin/env python3
"""MCP server exposing Cohezion compound AI tools to Slack.

Runs as a standalone HTTP server that Slack connects to for MCP integration.
Start: python mcp_server.py

Endpoints:
  GET  /health              → health check
  POST /mcp/tools/list      → list available tools
  POST /mcp/tools/call      → call a tool
"""

import json
import os
import sys
from typing import Any


_REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _REPO)

from handlers.ask_handler import handle_ask
from handlers.review_handler import handle_review
from handlers.search_handler import handle_search
from handlers.status_handler import handle_status
from shared.cohezion_mcp_client import CohezionMCPClient


try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = None  # type: ignore[misc,assignment]

_MCP_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))

# ── Tool dispatch ─────────────────────────────────────────────────────────────

def _dispatch_tool(name: str, arguments: dict) -> dict:
    """Route a tool call to the appropriate handler."""
    if name == "cohezion_ask":
        result = handle_ask(
            question=arguments.get("question", ""),
            tier=arguments.get("tier", "auto"),
        )
        return {
            "content": [{"type": "text", "text": result["answer"]}],
            "meta": {k: v for k, v in result.items() if k != "answer"},
        }

    if name == "cohezion_code_review":
        result = handle_review(task=arguments.get("task", ""))
        return {
            "content": [{"type": "text", "text": result["summary"]}],
            "meta": {"patches": len(result["implementation"].get("code_patches", []))},
        }

    if name == "cohezion_search":
        result = handle_search(
            query=arguments.get("query", ""),
            top_k=arguments.get("top_k", 3),
        )
        return {
            "content": [{"type": "text", "text": result["formatted"]}],
            "meta": {"result_count": len(result["results"])},
        }

    if name == "cohezion_get_status":
        result = handle_status()
        return {
            "content": [{"type": "text", "text": result["text"]}],
            "meta": result["tiers"],
        }

    raise ValueError(f"Unknown tool: {name}")


# ── FastAPI app ───────────────────────────────────────────────────────────────

def create_app():
    if not HAS_FASTAPI:
        raise RuntimeError("fastapi not installed. Run: uv pip install fastapi uvicorn")

    app = FastAPI(title="Cohezion MCP Server", version="1.0.0")
    _mcp_client = CohezionMCPClient()

    @app.get("/health")
    async def health():
        return {"status": "ok", "server": "cohezion-mcp", "version": "1.0.0"}

    @app.post("/mcp/tools/list")
    async def tools_list():
        return {"tools": _mcp_client.TOOLS}

    @app.post("/mcp/tools/call")
    async def tools_call(request: Request):
        body = await request.json()
        tool_name = body.get("name", "")
        arguments = body.get("arguments", {})
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing tool name")
        try:
            result = _dispatch_tool(tool_name, arguments)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Tool error: {e}")

    return app


# ── Fallback HTTP server (no FastAPI) ────────────────────────────────────────

def _run_simple_server() -> None:
    """Run a minimal HTTP server using only stdlib."""
    import http.server

    _mcp_client = CohezionMCPClient()

    class MCPHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[MCP] {fmt % args}")

        def _send_json(self, data: dict, status: int = 200) -> None:
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json({"status": "ok", "server": "cohezion-mcp"})
            else:
                self._send_json({"error": "Not found"}, 404)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")

            if self.path == "/mcp/tools/list":
                self._send_json({"tools": _mcp_client.TOOLS})
            elif self.path == "/mcp/tools/call":
                try:
                    result = _dispatch_tool(body.get("name", ""), body.get("arguments", {}))
                    self._send_json(result)
                except ValueError as e:
                    self._send_json({"error": str(e)}, 404)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)
            else:
                self._send_json({"error": "Not found"}, 404)

    server = http.server.HTTPServer(("0.0.0.0", _MCP_PORT), MCPHandler)
    print(f"[Cohezion MCP] Listening on http://0.0.0.0:{_MCP_PORT}")
    print("[Cohezion MCP] Tools: cohezion_ask, cohezion_code_review, cohezion_search, cohezion_get_status")
    server.serve_forever()


if __name__ == "__main__":
    print(f"[Cohezion MCP Server] Starting on port {_MCP_PORT}")
    if HAS_FASTAPI:
        import uvicorn
        uvicorn.run(create_app(), host="0.0.0.0", port=_MCP_PORT, log_level="info")
    else:
        print("[Cohezion MCP] FastAPI not available, using stdlib HTTP server")
        _run_simple_server()
