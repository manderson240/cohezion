# binds 0.0.0.0 in dev/internal services
"""HTTP MCP server for ngrok AI Gateway (for Claude.ai custom connectors).

This runs the MCP server as an HTTP endpoint that Claude.ai can connect to.

Usage:
    uv run python -m cohezion.gateway.mcp_http_server

Then add to Claude.ai:
    - Name: ngrok AI Gateway
    - URL: http://localhost:5000/sse (or https://xxxxx.ngrok.app/sse)
    - OAuth ID: (leave blank)
    - OAuth Secret: (leave blank)
"""

import asyncio
import json
import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.responses import StreamingResponse
from starlette.routing import Route

from cohezion.gateway.mcp_server import server as mcp_server


logger = logging.getLogger(__name__)


async def sse_endpoint(request):
    """SSE endpoint for MCP protocol (Claude.ai compatible)."""

    async def event_generator():
        try:
            # Send initial connection message
            yield b"data: " + json.dumps({"type": "server_ready"}).encode() + b"\n\n"

            # Stream MCP server responses
            # In a real implementation, this would proxy stdio to SSE
            while True:
                await asyncio.sleep(30)
                yield b": heartbeat\n\n"

        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield b"data: " + json.dumps({"error": str(e)}).encode() + b"\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def health(request):
    """Health check endpoint."""
    return StreamingResponse(
        iter([b"OK"]),
        media_type="text/plain",
    )


async def tools(request):
    """List available tools."""
    tools_list = await mcp_server.list_tools()
    return StreamingResponse(
        iter(
            [
                b"data: "
                + json.dumps(
                    {
                        "type": "tools",
                        "tools": [
                            {
                                "name": t.name,
                                "description": t.description,
                                "inputSchema": t.inputSchema,
                            }
                            for t in tools_list
                        ],
                    }
                ).encode()
                + b"\n\n"
            ]
        ),
        media_type="text/event-stream",
    )


# Create Starlette app
app = Starlette(
    routes=[
        Route("/sse", sse_endpoint),
        Route("/health", health),
        Route("/tools", tools),
    ],
)


def main():
    """Run the HTTP MCP server."""
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "5000"))

    logger.info(f"Starting ngrok AI Gateway MCP HTTP server on {host}:{port}")
    logger.info(f"Connect Claude.ai to: http://localhost:{port}/sse")
    logger.info("")
    logger.info("To add to Claude.ai:")
    logger.info("  Settings → Custom Connectors → Add Custom Connector")
    logger.info("  Name: ngrok AI Gateway")
    logger.info(f"  URL: http://localhost:{port}/sse")
    logger.info("  OAuth ID: (leave blank)")
    logger.info("  OAuth Secret: (leave blank)")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    main()
