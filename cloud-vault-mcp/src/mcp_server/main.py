"""Entry point for the Cloud Vault MCP Server."""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from .config import ServerConfig
from .server import create_server
from .sse_stream import VaultEventStream
from .vault_watcher import VaultFileWatcher


logger = logging.getLogger("cloud-vault-mcp")


def main():
    """Run the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = ServerConfig.from_env()

    if not config.api_key:
        logger.warning(
            "MCP_API_KEY is not set. The server will run without authentication. "
            "Set MCP_API_KEY environment variable for production use."
        )

    logger.info("Vault path: %s", config.vault_path)
    logger.info("Starting Cloud Vault MCP Server on %s:%d", config.host, config.port)

    mcp = create_server(config)

    # Get the streamable HTTP ASGI app from FastMCP
    mcp_app = mcp.streamable_http_app

    if config.watcher_enabled:
        # Create watcher and SSE stream
        loop = asyncio.new_event_loop()
        watcher = VaultFileWatcher(config.vault_path, loop, debounce_seconds=0.5)
        sse = VaultEventStream(watcher, heartbeat_seconds=config.sse_heartbeat_seconds)

        @asynccontextmanager
        async def lifespan(app):
            # Reassign loop to the running event loop
            nonlocal watcher
            running_loop = asyncio.get_running_loop()
            watcher = VaultFileWatcher(
                config.vault_path, running_loop, debounce_seconds=0.5
            )
            sse._watcher = watcher
            watcher.start()
            logger.info("VaultFileWatcher started")
            yield
            watcher.stop()
            logger.info("VaultFileWatcher stopped")

        # Compose Starlette app with SSE route + MCP mount
        app = Starlette(
            routes=[
                Route("/events/vault", sse.sse_endpoint),
                Mount("/", app=mcp_app),
            ],
            lifespan=lifespan,
        )
    else:
        app = mcp_app

    # Run with uvicorn directly to control host/port
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()
