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
    from mcp_server.main import main

    main()


if __name__ == "__main__":
    run_server()
