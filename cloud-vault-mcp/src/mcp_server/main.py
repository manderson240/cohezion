"""Entry point for the Cloud Vault MCP Server."""

import logging

import uvicorn

from .auth import APIKeyAuth
from .config import ServerConfig
from .server import create_server


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

    # Build the ASGI app from FastMCP
    app = mcp.streamable_http_app()

    # Apply API key authentication middleware when MCP_API_KEY is configured
    if config.api_key:
        app = APIKeyAuth(app, api_key=config.api_key)
        logger.info("API key authentication enabled")

    uvicorn.run(app, host=config.host, port=config.port, log_level=config.log_level)


if __name__ == "__main__":
    main()
