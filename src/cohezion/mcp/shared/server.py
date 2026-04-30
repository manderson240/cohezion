"""Shared MCP server utilities."""

from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)


async def run_server(
    app_factory: Callable[[], web.Application] | web.Application,
    default_port: int,
    server_name: str,
):
    """Run an MCP server with UDS and TCP support."""
    port = int(os.getenv("MCP_PORT", str(default_port)))
    uds_path = os.getenv("MCP_UDS_PATH")

    app = app_factory() if callable(app_factory) else app_factory

    runner = web.AppRunner(app)
    await runner.setup()

    if uds_path:
        logger.info(f"Starting {server_name} on UDS: {uds_path}")
        site = web.UnixSite(runner, uds_path)
    else:
        logger.info(f"Starting {server_name} on port {port}")
        site = web.TCPSite(runner, "0.0.0.0", port)

    await site.start()

    if uds_path:
        logger.info(f"{server_name} running on UDS: {uds_path}")
    else:
        logger.info(f"{server_name} running on http://localhost:{port}")

    # Graceful shutdown handler
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info(f"Shutting down {server_name}...")
    finally:
        await runner.cleanup()
