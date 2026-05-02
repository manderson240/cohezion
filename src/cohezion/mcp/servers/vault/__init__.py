"""Vault MCP Server wrapper.

This module provides an entry point for the MCP server manager to run
the cloud-vault-mcp server as part of the MCP fleet.
"""

import os
import sys


def run_server():
    """Entry point for the MCP server manager.

    Imports and runs the cloud-vault-mcp main function.
    The server_manager sets MCP_PORT env var before calling this.
    """
    from mcp_server.main import main as vault_main

    vault_main()


def main():
    """Alias for run_server to support fleet manager."""
    run_server()


def run_stdio_server():
    """Entry point for stdio-based MCP communication."""
    from mcp_server.config import ServerConfig
    from mcp_server.server import create_server

    config = ServerConfig.from_env()
    mcp = create_server(config)
    mcp.run()


if __name__ == "__main__":
    run_server()
