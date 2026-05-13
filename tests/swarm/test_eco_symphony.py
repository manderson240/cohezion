"""Simulation of the Compound EcoSymphony.
Tests the reflexive convergence of TEK, Physics, and Reviewer perspectives
into a final stable resilience strategy.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import numpy as np

from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.eco_symphony import EcoResilienceCompoundEngine
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldTranslator
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.swarm.providers.gemma4_provider import Gemma4Provider, GenerationResult


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MockRegimeProvider(Gemma4Provider):
    """Simulates Gemma 4 responses that evolve toward stability."""

    def __init__(self):
        super().__init__({})
        self.call_count = 0

    async def generate(self, model: str, prompt: str, **kwargs) -> GenerationResult:
        self.call_count += 1
        regime = kwargs.get("regime", "general")

        # Simulate convergence: The first 2 calls to generate are "noisy", thereafter they stabilize
        is_stable = self.call_count > 10

        if regime == "SENSING":
            text = "Sensing TEK: Mangrove-SabuSabu symbiosis."
        elif regime == "CALCULATION":
            text = "Calculation: 12D unstable." if not is_stable else "Calculation: 12D stable equilibrium."
        elif regime == "SYNTHESIS":
            text = "Strategy: Dredge everything." if not is_stable else "Strategy: Precision bio-mimetic restoration."
        elif regime == "STEERING":
            text = "Action: Start machine." if not is_stable else "Action: Execute biological seeding."
        else:
            text = "General response."

        return GenerationResult(
            response=text,
            model=model,
            provider="gemma4-mock",
            confidence=0.9,
            tokens_used=100,
            latency_ms=50,
            metadata={"regime": regime},
        )


async def run_symphony_test():
    logger.info("🚀 STARTING COMPOUND ECOSYMPHONY TEST")
    logger.info("=" * 60)

    # 1. Infrastructure
    provider = MockRegimeProvider()
    encoder = MagicMock(spec=FlumeVAEEncoder)

    # Dynamic stability: first few calls return low coherence, then increase
    def dynamic_encode(text):
        # Mocking the latent noise reduction as the system 'learns'
        noise = 10.0 if provider.call_count < 10 else 0.1
        return np.random.randn(256) * noise

    encoder.encode.side_effect = dynamic_encode
    translator = ManifoldTranslator(encoder=encoder)

    agent = EcoResilienceAgent(provider=provider, translator=translator, model_name="gemma4:26b-moe")
    guard = HIHOStabilityGuard(threshold=0.5)
    executor = MagicMock(spec=CompoundExecutor)
    loop = EcoResilienceCompoundLoop(agent=agent, executor=executor, guard=guard)

    # The Compound Engine
    engine = EcoResilienceCompoundEngine(agent=agent, loop=loop, guard=guard)

    # 2. Scenario
    scenario = "Emergency: Salinity spike in Sundarbans mangrove core."

    try:
        symphony = await engine.compound_synthesize(scenario)

        print("\n" + "═" * 60)
        print("🎻 COMPOUND ECOSYMPHONY RESULT")
        print("═" * 60)
        print(f"Final Strategy: {symphony.final_strategy}")
        print(f"Stability Score: {symphony.stability_score:.3f}")
        print(f"Consensus Score: {symphony.review_consensus:.3f}")
        print(f"Convergence Iterations: {symphony.iterations}")
        print(f"Refinement History: {len(symphony.refinement_history)} corrections applied.")
        print("═" * 60)

    except Exception as e:
        logger.exception(f"Symphony failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_symphony_test())
