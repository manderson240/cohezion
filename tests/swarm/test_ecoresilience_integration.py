from __future__ import annotations

import asyncio
import logging
import numpy as np
from unittest.mock import AsyncMock, MagicMock

from cohezion.swarm.providers.gemma4_provider import Gemma4Provider, GenerationResult
from cohezion.flume.manifolds.translator import ManifoldTranslator
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.executor import CompoundExecutor

# Necessary to fix the import in the test file if it was mangled
from cohezion.swarm.providers.model_provider import GenerationResult as GenResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_integration_test():
    logger.info("Starting EcoResilience Distributed Swarm Integration Test...")

    # 1. Setup Infrastructure
    provider = Gemma4Provider({"timeout": 10})
    provider.generate = AsyncMock()

    # Setup FLUME and Manifold Translation
    encoder = MagicMock(spec=FlumeVAEEncoder)
    encoder.encode.return_value = np.random.randn(256)
    translator = ManifoldTranslator(encoder=encoder)

    # 2. Setup Agent and Loop
    agent = EcoResilienceAgent(
        provider=provider, translator=translator, model_name="gemma4:26b-moe"
    )
    guard = HIHOStabilityGuard(threshold=0.5)
    executor = MagicMock(spec=CompoundExecutor)

    loop = EcoResilienceCompoundLoop(agent=agent, executor=executor, guard=guard)

    # Mock the provider's responses for the 4-regime cycle
    # Sensing -> Calculation -> Synthesis -> Steering
    # Use a loop to provide infinite responses for the test to avoid StopIteration
    provider.generate = AsyncMock()

    def mock_generate(model, prompt, **kwargs):
        # This allows the test to run indefinitely and simulate the refinement loop
        if "Refine" in prompt:
            return GenerationResult(
                response="SENSING: Refined TEK insights...",
                model="gemma4:2b",
                provider="gemma4",
                confidence=0.9,
                tokens_used=100,
                latency_ms=200,
                metadata={},
            )
        # Just return a generic valid result to avoid StopIteration
        return GenerationResult(
            response="Generic stable response",
            model=model,
            provider="gemma4",
            confidence=0.9,
            tokens_used=100,
            latency_ms=200,
            metadata={},
        )

    provider.generate.side_effect = mock_generate

    # 3. Run the simulation
    input_text = "Observations from the Sundarbans: Mangrove degradation impacting tiger habitats."
    logger.info(f"Input Scenario: {input_text}")

    try:
        result = await loop.run_stable_simulation(input_text)

        logger.info("--- Integration Result ---")
        logger.info(f"Final Strategy: {result.final_strategy}")
        logger.info(f"Stability Score: {result.stability_score:.3f}")
        logger.info(f"Is Stable: {result.is_stable}")
        logger.info(f"Iterations: {result.iterations}")

        assert result.final_strategy == "Final Action: Deploy seed-pods at tide-line."
        assert result.iterations == 1

        logger.info("Integration Test: PASSED")
    except Exception as e:
        logger.exception("Integration Test: FAILED")
        raise e


if __name__ == "__main__":
    asyncio.run(run_integration_test())
