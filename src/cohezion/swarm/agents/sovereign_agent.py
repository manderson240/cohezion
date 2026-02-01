import logging

from cohezion.core.local_registry import get_local_registry
from cohezion.swarm.agents.base import AgentResponse
from cohezion.swarm.agents.cosmic_agent import CosmicAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class SovereignAgent(CosmicAgent):
    """
    Sovereign Agent (Phase 17).

    Gateway 28: Sovereign Computation.

    Enforces local-only execution using the LocalRegistry.
    Prevents external API calls and ensures model availability.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.registry = get_local_registry()
        # Verify our own model is available
        if not self.registry.is_available(self.model_name):
            fallback = self.registry.get_best_available_local(
                ["mistral:7b", "phi3:mini"]
            )
            logger.warning(
                f"SovereignAgent model {self.model_name} missing. Downgrading to {fallback}."
            )
            self.model_name = fallback

    async def _call_ollama(self, prompt: str, **kwargs):
        """
        Override to enforce registry check before call.
        """
        target_model = kwargs.get("model", self.model_name)

        # 1. Sovereignty Check
        if not self.registry.is_available(target_model):
            # Dynamic fallback
            fallback = self.registry.get_best_available_local(
                ["mistral:7b", "phi3:mini"]
            )
            logger.info(
                f"🏰 Sovereignty Check: {target_model} is missing/cloud-based. Switching to local {fallback}."
            )
            kwargs["model"] = fallback

        # 2. Storage Safety Check (optional, mostly for generation that saves files)
        if not self.registry.check_capacity(
            min_gb=2.0
        ):  # 2GB buffer for inference logs
            logger.warning("Low disk space! Operations may be constrained.")

        # 3. Proceed with standard call
        base_resp = await super()._call_ollama(prompt, **kwargs)

        # Ensure we return a proper AgentResponse with all metadata preserved
        return AgentResponse(
            base_resp,
            embedding=getattr(base_resp, "embedding", None),
            persistence_id=getattr(base_resp, "persistence_id", None),
            frequency=getattr(base_resp, "frequency", 1),
            phi_score=getattr(base_resp, "phi_score", 0.0),
            confidence=getattr(base_resp, "confidence", 1.0),
            security_level=getattr(base_resp, "security_level", "safe"),
            narration=getattr(base_resp, "narration", None),
            alignment_score=getattr(base_resp, "alignment_score", 1.0),
        )

    async def close(self):
        await super().close()
