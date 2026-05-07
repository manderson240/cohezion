# ruff: noqa: S104  # binds 0.0.0.0 in dev/internal services
"""
Swarm MCP Server - Access to debate workflow.

Provides tools:
- run_debate: Execute full debate workflow on a query
- get_perspectives: Get available analyst perspectives
- synthesize: Quick synthesis without full debate
"""

import asyncio
import logging
import os
from typing import Any

from aiohttp import web

from cohezion.swarm.swarm_types import Perspective, SwarmConfig
from cohezion.swarm.workflows import DebateWorkflow


logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8372"))


class SwarmMCP:
    """
    MCP server for swarm debate workflow.

    Provides structured access to the SLM swarm.
    """

    def __init__(self, config: SwarmConfig | None = None):
        self.config = config or SwarmConfig()
        self._workflow: DebateWorkflow | None = None

    def _get_workflow(self) -> DebateWorkflow:
        """Lazy-load debate workflow."""
        if self._workflow is None:
            self._workflow = DebateWorkflow(config=self.config)
        return self._workflow

    async def run_debate(
        self,
        query: str,
        perspectives: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute full debate workflow.

        Args:
            query: The question to debate
            perspectives: Optional list of perspective names

        Returns:
            Synthesized response with metadata
        """
        workflow = self._get_workflow()

        # Parse perspectives
        if perspectives:
            persp_enums = [
                Perspective[p.upper()] for p in perspectives if p.upper() in Perspective.__members__
            ]
            workflow = DebateWorkflow(
                config=self.config,
                perspectives=persp_enums,
            )

        # Run async workflow
        result = await workflow.execute(query)
        return {
            "content": result.content,
            "confidence": result.confidence,
            "model_chain": result.model_chain,
            "processing_time_ms": result.processing_time_ms,
            "resolved_contradictions": result.resolved_contradictions,
        }

    def get_perspectives(self) -> list[dict[str, str]]:
        """Get available analyst perspectives."""
        return [{"name": p.name, "value": p.value} for p in Perspective]

    def get_metrics(self) -> dict[str, Any]:
        """Get workflow metrics."""
        workflow = self._get_workflow()
        return workflow.get_metrics()


# Singleton
_server: SwarmMCP | None = None


def get_server() -> SwarmMCP:
    global _server
    if _server is None:
        _server = SwarmMCP()
    return _server


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "server": "swarm"})


@routes.post("/tools/run_debate")
async def tool_run_debate(request: web.Request) -> web.Response:
    data = await request.json()
    query = data.get("query", "")
    perspectives = data.get("perspectives")
    server = get_server()
    result = await server.run_debate(query, perspectives)
    return web.json_response(result)


@routes.post("/tools/get_perspectives")
async def tool_get_perspectives(request: web.Request) -> web.Response:
    server = get_server()
    return web.json_response(server.get_perspectives())


def create_app() -> web.Application:
    app = web.Application()
    app.add_routes(routes)
    return app


app = create_app()


async def main():
    get_server()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()
    logger.info(f"Swarm MCP Server running on port {MCP_PORT}")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
