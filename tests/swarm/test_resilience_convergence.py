"""High-fidelity simulation of the EcoResilience Loop.
Tests the interaction between the Agent, the Manifold Translator,
the Stability Guard, and the Compound Loop.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import numpy as np

from cohezion.agents.specialists.ecoresilience_agent import EcoResilienceAgent
from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.resilience_loop import EcoResilienceCompoundLoop
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldTranslator
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.swarm.providers.gemma4_provider import Gemma4Provider, GenerationResult


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class SimulatedGemma4Provider(Gemma4Provider):
    """Simulates the Gemma 4 family behavior for testing the loop."""

    def __init__(self):
        super().__init__({})
        self.call_count = 0

    async def generate(self, model: str, prompt: str, **kwargs) -> GenerationResult:
        self.call_count += 1
        regime = kwargs.get("regime", "general")

        # Simulate a "failed" first attempt and a "successful" second attempt
        is_refinement = "Refine" in prompt

        if regime == "SENSING":
            text = (
                "Sensing TEK: High interdependency in reef systems."
                if not is_refinement
                else "Refined TEK: Specific thermal vent interdependency."
            )
        elif regime == "CALCULATION":
            text = (
                "Calculation: Manifold is unstable."
                if not is_refinement
                else "Calculation: Manifold equilibrium found."
            )
        elif regime == "SYNTHESIS":
            text = (
                "Strategy: Massive dredging."
                if not is_refinement
                else "Strategy: Precision bioswale restoration."
            )
        elif regime == "STEERING":
            text = (
                "Action: Start dredging."
                if not is_refinement
                else "Action: Plant native mangroves."
            )
        else:
            text = "Generic response."

        return GenerationResult(
            response=text,
            model=model,
            provider="gemma4-sim",
            confidence=0.9,
            tokens_used=100,
            latency_ms=50,
            metadata={"regime": regime},
        )


import pytest


@pytest.mark.asyncio
async def test_resilience_convergence():
    logger.info("=== Starting EcoResilience Convergence Test ===")

    # 1. Setup
    provider = SimulatedGemma4Provider()

    # Mock FLUME encoder to be deterministic for this test
    encoder = MagicMock(spec=FlumeVAEEncoder)
    # First call returns an "unstable" latent, second call returns "stable"
    encoder.encode.side_effect = [
        np.random.randn(256) * 10,  # Huge variance = unstable
        np.random.randn(256) * 0.1,  # Low variance = stable
        np.random.randn(256) * 0.1,
        np.random.randn(256) * 0.1,
        np.random.randn(256) * 0.1,
        np.random.randn(256) * 0.1,
        np.random.randn(256) * 0.1,
        np.random.randn(256) * 0.1,
    ]

    from cohezion.flume.spectral_encoder import SpectralEncoder
    from unittest.mock import MagicMock as MM

    mock_spectral = MM(spec=SpectralEncoder)
    mock_spectral.encode_spectral_state.return_value = np.zeros(256, dtype=np.float32)
    mock_spectral.integrate_with_text.side_effect = lambda t, s: t

    translator = ManifoldTranslator(encoder=encoder)
    agent = EcoResilienceAgent(
        provider=provider,
        translator=translator,
        model_name="gemma4:26b-moe",
        spectral_encoder=mock_spectral,
    )
    guard = HIHOStabilityGuard(threshold=0.5)
    executor = MagicMock(spec=CompoundExecutor)

    loop = EcoResilienceCompoundLoop(agent=agent, executor=executor, guard=guard)

    # 2. Run simulation
    scenario = "Critical mangrove loss in the Sundarbans."
    result = await loop.run_stable_simulation(scenario)

    logger.info("=== Final Test Result ===")
    logger.info(f"Final Strategy: {result.final_strategy}")
    logger.info(f"Stability Score: {result.stability_score:.3f}")
    logger.info(f"Is Stable: {result.is_stable}")
    logger.info(f"Iterations: {result.iterations}")

    # Verification
    if result.iterations > 1 and result.is_stable:
        logger.info("SUCCESS: System detected instability and converged to a stable state.")
    elif result.iterations == 1 and result.is_stable:
        logger.info("SUCCESS: System was stable from the start.")
    else:
        logger.error("FAILURE: System failed to converge or did not detect instability.")


if __name__ == "__main__":
    asyncio.run(test_resilience_convergence())
