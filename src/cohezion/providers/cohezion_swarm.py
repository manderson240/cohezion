"""
Cohezion Swarm Provider - Drop-in replacement for Open Notebook's LLM.

This provider routes requests not to a single LLM but to a coordinated
Swarm of local SLMs running on the 128GB Framework Desktop.
"""

import asyncio
import logging
from typing import Any

from cohezion.swarm.types import Perspective, SwarmConfig
from cohezion.swarm.workflows import DebateWorkflow

logger = logging.getLogger(__name__)


class CohezionSwarmProvider:
    """
    A custom provider that routes prompts not to a single LLM,
    but to a configured Swarm of local SLMs.
    
    Compatible with Open Notebook's BaseLLMProvider interface.
    """
    
    def __init__(
        self,
        swarm_config: SwarmConfig | None = None,
        perspectives: list[Perspective] | None = None,
    ):
        """
        Initialize the Swarm Provider.
        
        Args:
            swarm_config: Configuration for models and timeouts
            perspectives: Which analyst perspectives to use
        """
        self.config = swarm_config or SwarmConfig()
        self.perspectives = perspectives or [
            Perspective.TECHNICAL,
            Perspective.ETHICAL,
            Perspective.HISTORICAL,
        ]
        
        self._workflow: DebateWorkflow | None = None
        self._lock = asyncio.Lock()
    
    async def _get_workflow(self) -> DebateWorkflow:
        """Lazy-initialize the workflow."""
        if self._workflow is None:
            async with self._lock:
                if self._workflow is None:
                    self._workflow = DebateWorkflow(
                        config=self.config,
                        perspectives=self.perspectives,
                    )
        return self._workflow
    
    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Process a chat completion request through the Swarm.
        
        This is the main interface compatible with Open Notebook.
        
        Args:
            messages: List of message dicts with "role" and "content"
            tools: Optional tool definitions (not yet supported)
            **kwargs: Additional options
            
        Returns:
            A response dict with "content" and metadata
        """
        # Extract the latest user message as the query
        query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                query = msg.get("content", "")
                break
        
        if not query:
            return {
                "content": "No user query found in messages.",
                "role": "assistant",
                "error": True,
            }
        
        workflow = await self._get_workflow()
        
        try:
            response = await workflow.execute(query)
            
            return {
                "content": response.content,
                "role": "assistant",
                "confidence": response.confidence,
                "processing_time_ms": response.processing_time_ms,
                "model_chain": response.model_chain,
                "had_contradictions": response.source_critique.has_issues,
            }
            
        except Exception as e:
            logger.error(f"Swarm execution failed: {e}")
            return {
                "content": f"Swarm processing failed: {str(e)}",
                "role": "assistant",
                "error": True,
            }
    
    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """
        Simple generation interface.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional options
            
        Returns:
            The generated text
        """
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_complete(messages, **kwargs)
        return result.get("content", "")
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._workflow:
            await self._workflow.close()
            self._workflow = None
    
    def get_metrics(self) -> dict[str, Any]:
        """Return provider metrics."""
        if self._workflow:
            return {
                "provider": "CohezionSwarmProvider",
                "workflow": self._workflow.get_metrics(),
            }
        return {"provider": "CohezionSwarmProvider", "status": "not_initialized"}
    
    def __repr__(self) -> str:
        perspectives = ", ".join(p.value for p in self.perspectives)
        return f"CohezionSwarmProvider(perspectives=[{perspectives}])"


# Sync wrapper for non-async contexts
class CohezionSwarmProviderSync:
    """Synchronous wrapper for CohezionSwarmProvider."""
    
    def __init__(self, *args: Any, **kwargs: Any):
        self._async_provider = CohezionSwarmProvider(*args, **kwargs)
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def chat_complete(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Synchronous chat completion."""
        return self._get_loop().run_until_complete(
            self._async_provider.chat_complete(messages, **kwargs)
        )
    
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Synchronous generation."""
        return self._get_loop().run_until_complete(
            self._async_provider.generate(prompt, **kwargs)
        )
    
    def close(self) -> None:
        """Clean up resources."""
        self._get_loop().run_until_complete(self._async_provider.close())
