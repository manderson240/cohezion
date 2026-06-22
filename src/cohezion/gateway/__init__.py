"""ngrok AI Gateway integration for multi-provider LLM routing.

Provides OpenAI SDK-compatible endpoint that routes requests through ngrok AI Gateway
with automatic failover, cost optimization, and built-in response caching.

Two server options:
- mcp_server: stdio-based MCP protocol (for local use)
- mcp_http_server: HTTP endpoint for Claude.ai custom connectors
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.gateway.ngrok_adapter import NgrokAIGateway as NgrokAIGateway
    from cohezion.gateway.ngrok_adapter import NgrokMetrics as NgrokMetrics


__all__ = ["NgrokAIGateway", "NgrokMetrics"]

with contextlib.suppress(Exception):
    from cohezion.gateway.demo_gateway import DemoGateway as DemoGateway
    from cohezion.gateway.demo_gateway import DemoMetrics as DemoMetrics

with contextlib.suppress(Exception):
    from cohezion.gateway.mcp_server import GatewayManager as GatewayManager
    from cohezion.gateway.mcp_server import (
        get_gateway_manager as get_gateway_manager,
    )
