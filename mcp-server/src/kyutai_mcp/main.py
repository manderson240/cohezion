"""Entry point for Kyutai MCP Server."""

import asyncio
import logging
import sys
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import KyutaiMCPConfig
from .server import create_server

logger = logging.getLogger("kyutai-mcp")


def setup_logging(log_level: str = "info"):
    """Configure logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.setLevel(level)


async def health_endpoint(request):
    """Health check endpoint."""
    mcp = getattr(request.app, "_mcp_server", None)
    if not mcp:
        return JSONResponse({"status": "error", "error": "MCP not initialized"}, status_code=503)

    health_monitor = getattr(mcp, "_health_monitor", None)
    if not health_monitor:
        return JSONResponse({"status": "error", "error": "Health monitor not initialized"}, status_code=503)

    try:
        status = await health_monitor.check_all()
        status_code = 200 if status["overall_status"] == "healthy" else 503
        return JSONResponse(content=status, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": None,
            },
            status_code=503,
        )


async def models_endpoint(request):
    """List available models endpoint."""
    mcp = getattr(request.app, "_mcp_server", None)
    if not mcp:
        return JSONResponse({"status": "error", "error": "MCP not initialized"}, status_code=503)

    try:
        # Call list_models tool
        tools = mcp._mcp__tools
        list_models_tool = next((t for t in tools if t.name == "list_models"), None)
        if not list_models_tool:
            return JSONResponse({"status": "error", "error": "list_models tool not found"}, status_code=500)

        result = list_models_tool.fn()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Models endpoint failed: {e}")
        return JSONResponse(
            {"status": "error", "error": str(e)},
            status_code=500,
        )


def main():
    """Run the Kyutai MCP Server."""
    import argparse

    parser = argparse.ArgumentParser(description="Kyutai MCP Server")
    parser.add_argument(
        "--config",
        default="~/.kyutai-mcp/config.yaml",
        help="Configuration file path",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8361,
        help="Server port",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    logger.info("Starting Kyutai MCP Server")

    # Load configuration
    config = KyutaiMCPConfig.load_or_create(args.config)

    # Override with command line args if provided
    if args.host != "127.0.0.1":
        config.host = args.host
    if args.port != 8361:
        config.port = args.port
    if args.log_level != "info":
        config.log_level = args.log_level

    logger.info(f"Configuration loaded from {args.config}")
    logger.info(f"Listening on {config.host}:{config.port}")
    logger.info(f"Log level: {config.log_level}")

    # Create MCP server
    mcp = create_server(config)

    # Create ASGI app from MCP
    mcp_app = mcp.streamable_http_app()

    # Create wrapper Starlette app for additional routes
    async def startup():
        logger.info("Server starting up")

    async def shutdown():
        logger.info("Server shutting down")

    routes = [
        Route("/health", health_endpoint),
        Route("/models", models_endpoint),
    ]

    app = Starlette(
        routes=routes,
        on_startup=[startup],
        on_shutdown=[shutdown],
    )

    # Add CORS middleware
    app = CORSMiddleware(
        app,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount MCP app
    from starlette.routing import Mount

    app = Starlette(
        routes=[
            Mount("/", app=mcp_app),
            Route("/health", health_endpoint),
            Route("/models", models_endpoint),
        ]
    )

    app = CORSMiddleware(
        app,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store MCP reference in app
    app._mcp_server = mcp

    # Run server
    logger.info("MCP server initialized, starting HTTP server")
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )


if __name__ == "__main__":
    main()
