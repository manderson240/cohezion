"""ngrok AI Gateway integration for multi-provider LLM routing.

Provides OpenAI SDK-compatible endpoint that routes requests through ngrok AI Gateway
with automatic failover, cost optimization, and built-in response caching.

Two server options:
- mcp_server: stdio-based MCP protocol (for local use)
- mcp_http_server: HTTP endpoint for Claude.ai custom connectors
"""

from cohezion.gateway.ngrok_adapter import NgrokAIGateway, NgrokMetrics


__all__ = ["NgrokAIGateway", "NgrokMetrics"]
