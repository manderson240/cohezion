"""ngrok AI Gateway integration for multi-provider LLM routing.

Provides OpenAI SDK-compatible endpoint that routes requests through ngrok AI Gateway
with automatic failover, cost optimization, and built-in response caching.
"""

from cohezion.gateway.ngrok_adapter import NgrokAIGateway, NgrokMetrics

__all__ = ["NgrokAIGateway", "NgrokMetrics"]
