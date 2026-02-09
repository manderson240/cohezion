"""MCP (Model Context Protocol) server for ngrok AI Gateway.

This server exposes the ngrok AI Gateway as tools that Claude can use via
the Model Context Protocol, enabling Claude.ai to route requests through
ngrok AI Gateway with multi-provider support.

Installation:
    pip install fastmcp

Usage with Claude.ai Custom Connector:
    1. Start this server: python -m cohezion.gateway.mcp_server
    2. Get the server URL (default: http://localhost:5000/sse)
    3. Add custom connector in Claude.ai:
       - Name: ngrok AI Gateway
       - Remote MCP server URL: http://localhost:5000/sse
    4. Use the exposed tools in Claude conversations

Tools exposed:
    - generate: Generate response via ngrok gateway with multi-provider routing
    - get_metrics: Get performance and cost metrics
    - configure_gateway: Configure gateway settings
    - get_providers: List available providers and models
"""

import asyncio
import json
import logging
import os
from typing import Any

from fastmcp import Server, Tool

from cohezion.gateway import NgrokAIGateway
from cohezion.swarm.token_client import TokenEfficientClient

logger = logging.getLogger(__name__)

# Initialize server
app = Server("ngrok-ai-gateway")


class GatewayManager:
    """Manages ngrok gateway instances."""

    def __init__(self):
        """Initialize gateway manager."""
        self.gateways: dict[str, NgrokAIGateway] = {}
        self.clients: dict[str, TokenEfficientClient] = {}
        self.default_gateway_id = "default"
        self._initialize_default()

    def _initialize_default(self) -> None:
        """Initialize default gateway from environment variables."""
        ngrok_endpoint = os.getenv("NGROK_ENDPOINT")
        ngrok_api_key = os.getenv("NGROK_API_KEY")

        if ngrok_endpoint:
            self.gateways[self.default_gateway_id] = NgrokAIGateway(
                ngrok_endpoint=ngrok_endpoint,
                ngrok_api_key=ngrok_api_key,
                enable_failover=True,
            )
            logger.info(f"Default gateway initialized: {ngrok_endpoint}")
        else:
            logger.warning("NGROK_ENDPOINT not set, gateway not initialized")

    def get_gateway(self, gateway_id: str = "default") -> NgrokAIGateway | None:
        """Get gateway by ID."""
        return self.gateways.get(gateway_id)

    def create_gateway(
        self,
        gateway_id: str,
        ngrok_endpoint: str,
        ngrok_api_key: str | None = None,
        fallback_ollama_url: str = "http://localhost:11434",
        enable_failover: bool = True,
    ) -> NgrokAIGateway:
        """Create and register a new gateway."""
        gateway = NgrokAIGateway(
            ngrok_endpoint=ngrok_endpoint,
            ngrok_api_key=ngrok_api_key,
            fallback_ollama_url=fallback_ollama_url,
            enable_failover=enable_failover,
        )
        self.gateways[gateway_id] = gateway
        logger.info(f"Created gateway: {gateway_id}")
        return gateway


# Global gateway manager
_gateway_manager: GatewayManager | None = None


def get_gateway_manager() -> GatewayManager:
    """Get or create gateway manager."""
    global _gateway_manager
    if _gateway_manager is None:
        _gateway_manager = GatewayManager()
    return _gateway_manager


# Define tools
@app.tool()
async def generate(
    prompt: str,
    model: str = "gpt-4o",
    system: str = "",
    gateway_id: str = "default",
) -> dict[str, Any]:
    """Generate response via ngrok AI Gateway.

    Args:
        prompt: User prompt
        model: Model name (gpt-4o, claude-3.5-sonnet, gemini-pro, etc.)
        system: System prompt
        gateway_id: Gateway instance ID

    Returns:
        Dict with response, tokens, and cost
    """
    manager = get_gateway_manager()
    gateway = manager.get_gateway(gateway_id)

    if not gateway:
        return {
            "error": f"Gateway '{gateway_id}' not found",
            "available_gateways": list(manager.gateways.keys()),
        }

    try:
        response, tokens = await gateway.generate(
            prompt=prompt,
            model=model,
            system=system,
        )

        metrics = gateway.get_metrics()

        return {
            "success": True,
            "response": response,
            "tokens": tokens,
            "cost": round(
                metrics.get("total_cost", 0.0) / metrics.get("total_requests", 1), 6
            ),
            "provider_used": "ngrok",
            "fallback_used": metrics.get("fallback_requests", 0) > 0,
        }

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {
            "error": str(e),
            "success": False,
        }


@app.tool()
def get_metrics(gateway_id: str = "default") -> dict[str, Any]:
    """Get performance and cost metrics for a gateway.

    Args:
        gateway_id: Gateway instance ID

    Returns:
        Dict with comprehensive metrics
    """
    manager = get_gateway_manager()
    gateway = manager.get_gateway(gateway_id)

    if not gateway:
        return {
            "error": f"Gateway '{gateway_id}' not found",
            "available_gateways": list(manager.gateways.keys()),
        }

    return gateway.get_metrics()


@app.tool()
def get_providers() -> dict[str, Any]:
    """Get available providers and models.

    Returns:
        Dict with provider information and model mappings
    """
    return {
        "providers": {
            "openai": {
                "name": "OpenAI",
                "models": [
                    {
                        "name": "gpt-4o",
                        "cost_per_1m_tokens": {"input": 5.0, "output": 15.0},
                        "description": "Latest GPT-4 with vision",
                    },
                    {
                        "name": "gpt-3.5-turbo",
                        "cost_per_1m_tokens": {"input": 0.5, "output": 1.5},
                        "description": "Fast and cost-effective",
                    },
                ],
            },
            "anthropic": {
                "name": "Anthropic",
                "models": [
                    {
                        "name": "claude-3.5-sonnet",
                        "cost_per_1m_tokens": {"input": 3.0, "output": 15.0},
                        "description": "Balanced performance",
                    },
                    {
                        "name": "claude-3-opus",
                        "cost_per_1m_tokens": {"input": 15.0, "output": 75.0},
                        "description": "Most capable",
                    },
                    {
                        "name": "claude-3-haiku",
                        "cost_per_1m_tokens": {"input": 0.25, "output": 1.25},
                        "description": "Fast and cheap",
                    },
                ],
            },
            "google": {
                "name": "Google",
                "models": [
                    {
                        "name": "gemini-pro",
                        "cost_per_1m_tokens": {"input": 0.5, "output": 1.5},
                        "description": "Efficient language model",
                    },
                ],
            },
            "ollama": {
                "name": "Ollama (Self-hosted)",
                "models": [
                    {
                        "name": "qwen3-coder:30b",
                        "cost_per_1m_tokens": {"input": 0.0, "output": 0.0},
                        "description": "Local, free",
                    },
                    {
                        "name": "deepseek-r1:70b",
                        "cost_per_1m_tokens": {"input": 0.0, "output": 0.0},
                        "description": "Local, free",
                    },
                ],
            },
        },
        "note": "Use any model name in the 'generate' tool. ngrok routes to the appropriate provider.",
    }


@app.tool()
def configure_gateway(
    gateway_id: str,
    ngrok_endpoint: str,
    ngrok_api_key: str | None = None,
    fallback_ollama_url: str = "http://localhost:11434",
    enable_failover: bool = True,
) -> dict[str, Any]:
    """Create or update a gateway configuration.

    Args:
        gateway_id: Unique identifier for this gateway
        ngrok_endpoint: ngrok gateway endpoint URL
        ngrok_api_key: ngrok API key
        fallback_ollama_url: Ollama fallback URL
        enable_failover: Enable automatic failover

    Returns:
        Confirmation with gateway details
    """
    manager = get_gateway_manager()

    try:
        gateway = manager.create_gateway(
            gateway_id=gateway_id,
            ngrok_endpoint=ngrok_endpoint,
            ngrok_api_key=ngrok_api_key,
            fallback_ollama_url=fallback_ollama_url,
            enable_failover=enable_failover,
        )

        return {
            "success": True,
            "gateway_id": gateway_id,
            "ngrok_endpoint": ngrok_endpoint,
            "fallback_ollama_url": fallback_ollama_url,
            "failover_enabled": enable_failover,
            "message": f"Gateway '{gateway_id}' configured successfully",
        }

    except Exception as e:
        logger.error(f"Configuration failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.tool()
def cost_estimate(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    """Estimate cost for a request.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost estimate in USD
    """
    manager = get_gateway_manager()
    gateway = manager.get_gateway("default")

    if not gateway:
        return {
            "error": "Default gateway not configured",
        }

    cost = gateway._calculate_cost(model, input_tokens, output_tokens)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(cost, 6),
        "cost_per_1m_tokens": {
            "input": round(cost / input_tokens * 1e6, 6) if input_tokens > 0 else 0,
            "output": round(cost / output_tokens * 1e6, 6) if output_tokens > 0 else 0,
        },
    }


async def main() -> None:
    """Run the MCP server."""
    import uvicorn

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
