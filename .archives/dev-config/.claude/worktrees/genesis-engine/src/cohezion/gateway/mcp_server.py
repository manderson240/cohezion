"""MCP (Model Context Protocol) server for ngrok AI Gateway.

This server exposes the ngrok AI Gateway as tools that Claude can use via
the Model Context Protocol, enabling Claude.ai to route requests through
ngrok AI Gateway with multi-provider support.

Uses stdio-based MCP protocol (standard for Claude integrations).

Usage with Claude.ai Custom Connector:
    1. Add custom connector in Claude.ai settings:
       - Name: ngrok AI Gateway
       - Command: uv run python -m cohezion.gateway.mcp_server
    2. Environment variables (in Claude.ai or shell):
       - NGROK_ENDPOINT: Your ngrok gateway URL
       - NGROK_API_KEY: Your ngrok API key
    3. Use the exposed tools in Claude conversations

Tools exposed:
    - generate: Generate response via ngrok gateway with multi-provider routing
    - get_metrics: Get performance and cost metrics
    - configure_gateway: Configure gateway settings
    - get_providers: List available providers and models
    - cost_estimate: Estimate request costs
"""

import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cohezion.gateway.demo_gateway import DemoGateway
from cohezion.security.credentials import get_credentials


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

# Initialize server
server = Server("ngrok-ai-gateway")


class GatewayManager:
    """Manages demo gateway instances (uses local Ollama, no API keys needed)."""

    def __init__(self):
        """Initialize gateway manager."""
        self.gateways: dict[str, DemoGateway] = {}
        self.default_gateway_id = "default"
        self._initialize_default()

    def _initialize_default(self) -> None:
        """Initialize default demo gateway with local Ollama."""
        # Primary: Vault Warden, Fallback: Environment
        ollama_url = (
            get_credentials().get_secret("COHEZION_OLLAMA_URL", env_var="OLLAMA_BASE_URL") or "http://localhost:11434"
        )

        self.gateways[self.default_gateway_id] = DemoGateway(
            ollama_url=ollama_url,
        )
        logger.info(f"Demo gateway initialized (Ollama: {ollama_url})")
        logger.info("Note: This is a DEMO gateway using local Ollama models")

    def get_gateway(self, gateway_id: str = "default") -> DemoGateway | None:
        """Get gateway by ID."""
        return self.gateways.get(gateway_id)

    def create_gateway(
        self,
        gateway_id: str,
        ollama_url: str = "http://localhost:11434",
    ) -> DemoGateway:
        """Create and register a new gateway."""
        gateway = DemoGateway(ollama_url=ollama_url)
        self.gateways[gateway_id] = gateway
        logger.info(f"Created demo gateway: {gateway_id}")
        return gateway


# Global gateway manager
_gateway_manager: GatewayManager | None = None


def get_gateway_manager() -> GatewayManager:
    """Get or create gateway manager."""
    global _gateway_manager
    if _gateway_manager is None:
        _gateway_manager = GatewayManager()
    return _gateway_manager


# Register tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="generate",
            description="Generate response via ngrok AI Gateway with multi-provider routing",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "User prompt"},
                    "model": {
                        "type": "string",
                        "description": "Model name (gpt-4o, claude-3.5-sonnet, etc.)",
                        "default": "gpt-4o",
                    },
                    "system": {"type": "string", "description": "System prompt"},
                    "gateway_id": {
                        "type": "string",
                        "description": "Gateway instance ID",
                        "default": "default",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="get_metrics",
            description="Get performance and cost metrics for a gateway",
            inputSchema={
                "type": "object",
                "properties": {
                    "gateway_id": {
                        "type": "string",
                        "description": "Gateway instance ID",
                        "default": "default",
                    },
                },
            },
        ),
        Tool(
            name="get_providers",
            description="Get available providers and models",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="configure_gateway",
            description="Create a new demo gateway instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "gateway_id": {"type": "string", "description": "Gateway ID"},
                    "ollama_url": {
                        "type": "string",
                        "description": "Local Ollama URL",
                        "default": "http://localhost:11434",
                    },
                },
                "required": ["gateway_id"],
            },
        ),
        Tool(
            name="cost_estimate",
            description="Estimate cost for a request",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model name"},
                    "input_tokens": {"type": "integer", "description": "Input tokens"},
                    "output_tokens": {
                        "type": "integer",
                        "description": "Output tokens",
                    },
                },
                "required": ["model", "input_tokens", "output_tokens"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "generate":
            manager = get_gateway_manager()
            gateway = manager.get_gateway(arguments.get("gateway_id", "default"))

            if not gateway:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Gateway '{arguments.get('gateway_id')}' not found",
                                "available_gateways": list(manager.gateways.keys()),
                            }
                        ),
                    )
                ]

            response, tokens = await gateway.generate(
                prompt=arguments["prompt"],
                model=arguments.get("model", "gpt-4o"),
                system=arguments.get("system", ""),
            )

            metrics = gateway.get_metrics()

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "response": response,
                            "tokens": tokens,
                            "cost": round(
                                metrics.get("total_cost", 0.0) / max(metrics.get("total_requests", 1), 1),
                                6,
                            ),
                        }
                    ),
                )
            ]

        elif name == "get_metrics":
            manager = get_gateway_manager()
            gateway = manager.get_gateway(arguments.get("gateway_id", "default"))

            if not gateway:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Gateway '{arguments.get('gateway_id')}' not found"}),
                    )
                ]

            return [TextContent(type="text", text=json.dumps(gateway.get_metrics()))]

        elif name == "get_providers":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "providers": {
                                "openai": {
                                    "name": "OpenAI",
                                    "models": [
                                        {
                                            "name": "gpt-4o",
                                            "cost": {"input": 5.0, "output": 15.0},
                                        },
                                        {
                                            "name": "gpt-3.5-turbo",
                                            "cost": {"input": 0.5, "output": 1.5},
                                        },
                                    ],
                                },
                                "anthropic": {
                                    "name": "Anthropic",
                                    "models": [
                                        {
                                            "name": "claude-3.5-sonnet",
                                            "cost": {"input": 3.0, "output": 15.0},
                                        },
                                        {
                                            "name": "claude-3-haiku",
                                            "cost": {"input": 0.25, "output": 1.25},
                                        },
                                    ],
                                },
                                "google": {
                                    "name": "Google",
                                    "models": [
                                        {
                                            "name": "gemini-pro",
                                            "cost": {"input": 0.5, "output": 1.5},
                                        },
                                    ],
                                },
                            }
                        }
                    ),
                )
            ]

        elif name == "configure_gateway":
            manager = get_gateway_manager()
            try:
                gateway = manager.create_gateway(
                    gateway_id=arguments["gateway_id"],
                    ollama_url=arguments.get("ollama_url", "http://localhost:11434"),
                )

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "gateway_id": arguments["gateway_id"],
                                "message": "Demo gateway created successfully (uses local Ollama)",
                            }
                        ),
                    )
                ]

            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": str(e)}),
                    )
                ]

        elif name == "cost_estimate":
            manager = get_gateway_manager()
            gateway = manager.get_gateway("default")

            if not gateway:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "Default gateway not configured"}),
                    )
                ]

            estimate = gateway.cost_estimate(
                arguments["model"],
                arguments["input_tokens"],
                arguments["output_tokens"],
            )

            return [
                TextContent(
                    type="text",
                    text=json.dumps(estimate),
                )
            ]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main() -> None:
    """Run the MCP server using stdio protocol."""
    logger.info("Starting ngrok AI Gateway MCP server...")
    logger.info("Listening on stdio for MCP protocol")
    async with stdio_server(server):
        logger.info("MCP server ready")
        await asyncio.sleep(float("inf"))


if __name__ == "__main__":
    asyncio.run(main())
