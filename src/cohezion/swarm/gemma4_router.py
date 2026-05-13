"""Gemma 4 specific routing logic.

Optimizes token efficiency by aggressively routing lightweight tasks to E2B/E4B
and reserving 31B/26B models for deep reasoning and complex simulations.
"""

import logging
from dataclasses import dataclass

from cohezion.swarm.providers.model_provider import GenerationResult, get_model_provider


logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Decision from the Gemma 4 router."""

    model_id: str
    reason: str
    estimated_tokens: int


class Gemma4Router:
    """Routes tasks to the optimal Gemma 4 model based on complexity."""

    def __init__(self):
        self.provider = get_model_provider("gemma4")
        self.models = {
            "light": "gemma4:2b",
            "medium": "gemma4:4b",
            "complex": "gemma4:26b",
            "simulation": "gemma4:31b",
        }

    def _analyze_complexity(self, prompt: str, **kwargs) -> str:
        """Analyze prompt to determine complexity tier."""
        # Simple heuristics for demonstration
        if "simulate" in prompt.lower() or "12d manifold" in prompt.lower() or "physics" in prompt.lower():
            return "simulation"
        if "reason" in prompt.lower() or "explain" in prompt.lower() or len(prompt) > 1000:
            return "complex"
        if "summarize" in prompt.lower() or len(prompt) > 200:
            return "medium"
        return "light"

    def route(self, prompt: str, **kwargs) -> RoutingDecision:
        """Route a prompt to the appropriate Gemma 4 model."""
        complexity = self._analyze_complexity(prompt, **kwargs)
        model_id = self.models[complexity]

        # Estimate tokens (very rough approximation)
        estimated_tokens = len(prompt) // 4

        return RoutingDecision(
            model_id=model_id,
            reason=f"Selected {model_id} based on {complexity} complexity analysis.",
            estimated_tokens=estimated_tokens,
        )

    async def execute(self, prompt: str, **kwargs) -> GenerationResult:
        """Route and execute the prompt."""
        decision = self.route(prompt, **kwargs)
        logger.info(f"Routing to {decision.model_id}: {decision.reason}")
        return await self.provider.generate(model=decision.model_id, prompt=prompt, **kwargs)
