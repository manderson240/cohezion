"""
Swarm MCP Server - Access to debate workflow.

Provides tools:
- run_debate: Execute full debate workflow on a query  
- get_perspectives: Get available analyst perspectives
- synthesize: Quick synthesis without full debate
"""

import asyncio
import logging
from typing import Any

from cohezion.swarm.types import Perspective, SwarmConfig
from cohezion.swarm.workflows import DebateWorkflow

logger = logging.getLogger(__name__)


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
    
    def run_debate(
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
                Perspective[p.upper()] for p in perspectives
                if p.upper() in Perspective.__members__
            ]
            workflow = DebateWorkflow(
                config=self.config,
                perspectives=persp_enums,
            )
        
        # Run async workflow
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(workflow.execute(query))
            return {
                "content": result.content,
                "confidence": result.confidence,
                "model_chain": result.model_chain,
                "processing_time_ms": result.processing_time_ms,
                "resolved_contradictions": result.resolved_contradictions,
            }
        finally:
            loop.close()
    
    def get_perspectives(self) -> list[dict[str, str]]:
        """Get available analyst perspectives."""
        return [
            {"name": p.name, "value": p.value}
            for p in Perspective
        ]
    
    def get_metrics(self) -> dict[str, Any]:
        """Get workflow metrics."""
        workflow = self._get_workflow()
        return workflow.get_metrics()


# MCP tool definitions
TOOLS = [
    {
        "name": "run_debate",
        "description": "Execute full multi-perspective debate on a query",
        "parameters": {
            "query": {"type": "string", "required": True},
            "perspectives": {"type": "array", "items": {"type": "string"}},
        },
    },
    {
        "name": "get_perspectives",
        "description": "Get available analyst perspectives",
        "parameters": {},
    },
]


# Singleton
_server: SwarmMCP | None = None


def get_server() -> SwarmMCP:
    global _server
    if _server is None:
        _server = SwarmMCP()
    return _server
