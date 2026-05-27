# binds 0.0.0.0 in dev/internal services
"""Template for creating new MCP servers.

This is a complete example showing how to create a new MCP server
in ~30 minutes. Copy this file and customize for your service.

Example: Weather MCP Server
- Port: Auto-allocated (8363+)
- Tools: get_weather, get_forecast, search_cities
- Resources: weather data by location
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from aiohttp import web


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Configuration - these can be overridden via env vars
MCP_PORT = int(os.getenv("MCP_PORT", "8363"))  # Will be auto-allocated by manager
API_KEY = os.getenv("WEATHER_API_KEY", "")  # Your service API key
SERVICE_NAME = os.getenv("SERVICE_NAME", "weather")


class WeatherService:
    """Your service implementation."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._cache: dict[str, Any] = {}

    async def get_weather(self, city: str, country: str = "") -> dict[str, Any]:
        """Get current weather for a location.

        This is where you'd integrate with your actual API.
        """
        # Example implementation
        return {
            "city": city,
            "country": country,
            "temperature": 22,
            "condition": "sunny",
            "humidity": 65,
            "wind_speed": 10,
            "source": f"{SERVICE_NAME}-api",
        }

    async def get_forecast(self, city: str, days: int = 7) -> dict[str, Any]:
        """Get weather forecast."""
        # Example implementation
        return {
            "city": city,
            "days": days,
            "forecast": [{"day": i + 1, "temp": 20 + i, "condition": "sunny"} for i in range(days)],
        }

    async def search_cities(self, query: str, limit: int = 10) -> list[dict]:
        """Search for cities."""
        # Example implementation
        return [
            {"name": f"{query} City {i}", "country": "US", "lat": 40.0, "lon": -74.0}
            for i in range(min(limit, 5))
        ]


# Global service instance
_service: WeatherService | None = None


def get_service() -> WeatherService:
    """Get or create service instance."""
    global _service
    if _service is None:
        _service = WeatherService(API_KEY)
    return _service


# HTTP API routes
routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check endpoint - REQUIRED for MCP Manager."""
    return web.json_response(
        {
            "status": "healthy",
            "server": SERVICE_NAME,
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": f"{SERVICE_NAME.capitalize()} MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "tools": [
                f"{SERVICE_NAME}_get_weather",
                f"{SERVICE_NAME}_get_forecast",
                f"{SERVICE_NAME}_search_cities",
            ],
        }
    )


# =============================================================================
# TOOLS - Add your service's capabilities here
# =============================================================================


@routes.post(f"/tools/{SERVICE_NAME}_get_weather")
async def tool_get_weather(request: web.Request) -> web.Response:
    """Get current weather for a city."""
    try:
        data = await request.json()
        city = data.get("city", "")
        country = data.get("country", "")

        if not city:
            return web.json_response({"error": "City is required"}, status=400)

        service = get_service()
        result = await service.get_weather(city, country)

        return web.json_response(
            {
                "tool": f"{SERVICE_NAME}_get_weather",
                "result": result,
            }
        )
    except Exception as e:
        logger.exception("Error getting weather")
        return web.json_response({"error": str(e)}, status=500)


@routes.post(f"/tools/{SERVICE_NAME}_get_forecast")
async def tool_get_forecast(request: web.Request) -> web.Response:
    """Get weather forecast."""
    try:
        data = await request.json()
        city = data.get("city", "")
        days = data.get("days", 7)

        if not city:
            return web.json_response({"error": "City is required"}, status=400)

        service = get_service()
        result = await service.get_forecast(city, days)

        return web.json_response(
            {
                "tool": f"{SERVICE_NAME}_get_forecast",
                "result": result,
            }
        )
    except Exception as e:
        logger.exception("Error getting forecast")
        return web.json_response({"error": str(e)}, status=500)


@routes.post(f"/tools/{SERVICE_NAME}_search_cities")
async def tool_search_cities(request: web.Request) -> web.Response:
    """Search for cities."""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 10)

        if not query:
            return web.json_response({"error": "Query is required"}, status=400)

        service = get_service()
        results = await service.search_cities(query, limit)

        return web.json_response(
            {
                "tool": f"{SERVICE_NAME}_search_cities",
                "count": len(results),
                "cities": results,
            }
        )
    except Exception as e:
        logger.exception("Error searching cities")
        return web.json_response({"error": str(e)}, status=500)


# =============================================================================
# RESOURCES - Optional: Add resource endpoints for data access
# =============================================================================


@routes.get(f"/resources/{SERVICE_NAME}/cities/{{city}}")
async def resource_city(request: web.Request) -> web.Response:
    """Get weather resource for a specific city."""
    city = request.match_info["city"]

    try:
        service = get_service()
        result = await service.get_weather(city)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# =============================================================================
# MAIN - Server startup
# =============================================================================


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the MCP server."""
    # Initialize service
    get_service()

    # Run the server
    logger.info(f"Starting {SERVICE_NAME.capitalize()} MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ {SERVICE_NAME.capitalize()} MCP Server running on http://localhost:{MCP_PORT}")
    logger.info(f"   Health check: http://localhost:{MCP_PORT}/health")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"{SERVICE_NAME.capitalize()} MCP Server stopped")
