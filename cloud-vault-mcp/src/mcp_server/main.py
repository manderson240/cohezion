"""Entry point for the Cloud Vault MCP Server."""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import ServerConfig
from .health import HealthChecker
from .server import create_server
from .sse_stream import VaultEventStream
from .vault_watcher import VaultFileWatcher


# Import security modules
try:
    from cohezion.security.https_middleware import create_https_app
    from cohezion.security.tls_config import TLSConfig
except ImportError:
    TLSConfig = None
    create_https_app = None


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

    # Initialize health checker
    health_checker = None
    if config.health_check_enabled:
        health_checker = HealthChecker(
            vault_path=config.vault_path,
            surrealdb_url=config.surrealdb_url,
            ollama_url=config.ollama_url,
        )
        logger.info("Health check enabled")

    # FastMCP provides factory methods to build ASGI apps - call streamable_http_app()
    mcp_app = mcp.streamable_http_app()

    # Add TrustedHostMiddleware if not accepting all hosts
    if "*" not in config.allowed_hosts:
        mcp_app = TrustedHostMiddleware(mcp_app, allowed_hosts=config.allowed_hosts)

    # Create health endpoint handler
    async def health_endpoint(request: Request):
        """Health check endpoint."""
        if health_checker is None:
            return JSONResponse(
                {"error": "Health check not enabled"},
                status_code=503,
            )

        try:
            status = await health_checker.run_all_checks(
                timeout=int(config.health_check_timeout)
            )
            status_code = 200 if status.status == "healthy" else 503
            return JSONResponse(
                content=status.to_dict(),
                status_code=status_code,
            )
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

        # Create base Starlette app with SSE and health routes with lifespan
        sse_app = Starlette(
            routes=[
                Route("/events/vault", sse.sse_endpoint),
                Route("/health", health_endpoint),
            ],
            lifespan=lifespan,
        )

        # Wrap with MCP fallback for all other routes
        async def app(scope, receive, send):
            if scope["type"] == "http":
                if scope["path"] == "/events/vault":
                    # Route to SSE handler
                    await sse_app(scope, receive, send)
                elif scope["path"] == "/health":
                    # Route to health check
                    await sse_app(scope, receive, send)
                else:
                    # Route to MCP
                    await mcp_app(scope, receive, send)
            elif scope["type"] == "lifespan":
                # Handle lifespan through sse_app
                await sse_app(scope, receive, send)
            else:
                # WebSocket or other protocol
                await mcp_app(scope, receive, send)
    else:
        # Create Starlette app with just health endpoint (no watcher)
        health_app = Starlette(
            routes=[Route("/health", health_endpoint)],
        )

        async def app(scope, receive, send):
            if scope["type"] == "http":
                if scope["path"] == "/health":
                    # Route to health check
                    await health_app(scope, receive, send)
                else:
                    # Route to MCP
                    await mcp_app(scope, receive, send)
            else:
                # WebSocket or other protocol
                await mcp_app(scope, receive, send)

    # Apply HTTPS middleware if TLS is enabled
    if config.tls_enabled and TLSConfig and create_https_app:
        logger.info("Configuring HTTPS/TLS security")

        tls_config = TLSConfig(
            cert_path=config.tls_cert_path,
            key_path=config.tls_key_path,
            hsts_max_age=config.tls_hsts_max_age,
            allowed_origins=config.tls_allowed_origins,
        )

        if not tls_config.validate_certificate():
            logger.error(
                "TLS certificate validation failed. "
                "Proceeding with HTTP (NOT RECOMMENDED FOR PRODUCTION)"
            )
        else:
            logger.info("TLS certificate validated successfully")
            app = create_https_app(app, tls_config, allow_http_localhost=True)

    # Run with uvicorn directly to control host/port
    # Note: For HTTPS, use ssl_certfile and ssl_keyfile parameters
    ssl_certfile = None
    ssl_keyfile = None

    if config.tls_enabled and config.tls_cert_path and config.tls_key_path:
        ssl_certfile = config.tls_cert_path
        ssl_keyfile = config.tls_key_path
        logger.info("Starting HTTPS server with SSL certificates")

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )


if __name__ == "__main__":
    main()
