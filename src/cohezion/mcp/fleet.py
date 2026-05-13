"""MCP Fleet Manager - Single entry point for all Cohezion MCP servers.

Optimized for: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S
Methodology: FLUME trajectory tracking & HIHO coherence alignment.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


# Hardware-specific optimizations
os.environ["TORCH_ROCM_ARCH"] = "gfx1100"  # Radeon 8060S (approximate for RDNA3+)
os.environ["PYTORCH_ROCM_ARCH"] = "gfx1100"
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp-fleet")

SERVER_MAP = {
    "bmad": "cohezion.mcp.bmad_server",
    "coherence": "cohezion.mcp.coherence_server",
    "skills": "cohezion.mcp.skills_server_mcp",
    "research": "cohezion.mcp.research_server_mcp",
    "surreal": "cohezion.mcp.surreal_server_mcp",
    "swarm": "cohezion.mcp.swarm_server_mcp",
    "knowledge": "cohezion.mcp.knowledge_server_mcp",
    "compound": "cohezion.mcp.compound_server",
    "rewards": "cohezion.mcp.servers.rewards.server",
    "vault": "cohezion.mcp.servers.vault",
    "security": "cohezion.mcp.servers.security.server",
    "journey": "cohezion.mcp.servers.journey.server",
    "github": "cohezion.mcp.servers.github.server",
    "huggingface": "cohezion.mcp.servers.huggingface.server",
}


def run_server_sync(name: str, transport: str = "stdio", port: int | None = None):
    """Run a specific MCP server synchronously."""
    if name not in SERVER_MAP:
        logger.error(f"Unknown server: {name}")
        return

    module_name = SERVER_MAP[name]
    logger.info(f"Starting {name} fleet member ({module_name}) on {transport}...")

    if port:
        os.environ["MCP_PORT"] = str(port)

    os.environ["MCP_TRANSPORT"] = transport

    import importlib

    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "main"):
            # If it's the old-style main that might be async, we need to handle it
            import asyncio

            if asyncio.iscoroutinefunction(module.main):
                asyncio.run(module.main())
            else:
                module.main()
        elif hasattr(module, "app"):
            # FastMCP app.run() will start its own loop
            if transport == "http" and port:
                module.app.run(transport=transport, host="0.0.0.0", port=port)
            else:
                module.app.run(transport=transport)
    except Exception:
        logger.exception(f"Failed to start {name}")


def main():
    parser = argparse.ArgumentParser(description="Cohezion MCP Fleet Manager")
    parser.add_argument("server", choices=list(SERVER_MAP.keys()) + ["all"], help="Server to start")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio", help="Transport protocol")
    parser.add_argument("--port", type=int, help="Port for HTTP transport")

    args = parser.parse_args()

    if args.server == "all":
        print("Error: 'all' mode not yet implemented. Use start-mcp-servers.sh")
        sys.exit(1)

    run_server_sync(args.server, args.transport, args.port)


if __name__ == "__main__":
    main()
