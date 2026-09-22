"""Entry point for the Cloud Vault MCP Server."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .auth import APIKeyAuth
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


def protect_mcp_app(mcp_app, api_key: str):
    """Wrap *mcp_app* with bearer-key auth when a key is configured.

    `APIKeyAuth` existed but was never applied, so the server answered unauthenticated
    requests while exposed through a public tunnel (2026-09-21). An empty key leaves the
    app unwrapped; `main` already warns loudly in that case.
    """
    if not api_key:
        return mcp_app
    return APIKeyAuth(mcp_app, api_key=api_key)


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOW_NO_AUTH_ENV = "MCP_ALLOW_NO_AUTH"


def check_auth_config(config: ServerConfig) -> None:
    """Refuse to serve without MCP_API_KEY (security finding M3, 2026-09-22).

    An empty key used to mean "no auth" with only a log warning, on default host
    0.0.0.0, exposing vault writes and root SurrealDB tools. Now an empty key is
    refused unless the host is loopback AND ``MCP_ALLOW_NO_AUTH=1`` (local dev).
    Loopback alone is not enough: the public tunnel connects to localhost.
    """
    if config.api_key:
        return
    if config.host in _LOOPBACK_HOSTS and os.environ.get(ALLOW_NO_AUTH_ENV) == "1":
        logger.warning(
            "MCP_API_KEY unset: serving UNAUTHENTICATED on %s (%s=1)",
            config.host,
            ALLOW_NO_AUTH_ENV,
        )
        return
    raise SystemExit(
        f"MCP_API_KEY is not set; refusing to start on {config.host}. Set "
        f"MCP_API_KEY, or for local dev bind MCP_HOST=127.0.0.1 and set "
        f"{ALLOW_NO_AUTH_ENV}=1."
    )


def main():
    """Run the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = ServerConfig.from_env()
    check_auth_config(config)

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
    app = build_app(config, mcp.streamable_http_app(), health_checker)
    serve(app, config)


def build_app(config: ServerConfig, mcp_app, health_checker=None):
    """Compose the served ASGI app: MCP, /health, and /events/vault (watcher on).

    MCP_API_KEY is enforced on the COMPOSED app (security finding M2, 2026-09-22):
    the key was applied to the MCP sub-app only, so /events/vault -- which streams
    vault paths and renames -- was routed around it. /health stays open
    (APIKeyAuth.EXCLUDED_PATHS).
    """
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

    app = protect_mcp_app(app, config.api_key)

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

    return app


def serve(app, config: ServerConfig) -> None:
    """Run *app* with uvicorn on the configured host/port (TLS when configured)."""
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
