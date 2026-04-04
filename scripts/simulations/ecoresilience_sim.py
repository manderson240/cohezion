#!/usr/bin/env python3
"""Ecosystem Resilience Simulation using Gemma 4."""

import asyncio
import logging
import uuid
from cohezion.agents.ecoresilience_agent import EcoResilienceAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_simulation():
    """Execute the EcoResilience prototype simulation."""
    logger.info("Initializing EcoResilience Agent...")
    try:
        agent = EcoResilienceAgent(model_name="gemma4")
    except Exception as e:
        logger.error(f"Failed to initialize agent (expected during testing if backend unavailable): {e}")
        return

    scenario = (
        "A prolonged drought in a temperate forest ecosystem is reducing canopy cover, "
        "affecting local hydrology and disrupting migratory bird patterns. How can we model "
        "interventions to stabilize the ecosystem using TEK principles of 'seasonal balance' "
        "mapped to HIHO stability metrics?"
    )
    
    trajectory_id = f"sim-{uuid.uuid4()}"
    logger.info(f"Running simulation scenario (Trajectory ID: {trajectory_id}):\n{scenario}\n")
    
    try:
        # Note: In YOLO/testing mode without Ollama running, this will fail gracefully.
        response = await agent.analyze_ecosystem(scenario, trajectory_id)
        logger.info(f"Agent Response:\n{response}")
        logger.info(f"--- Le-WM Metrics ---")
        logger.info(f"Coherence Shift: {response['coherence_shift']:.4f}")
        logger.info(f"Temporal Curvature: {response['temporal_curvature']:.4f}")
        logger.info(f"Path Straightening Achieved: {response['straightening_achieved']}")
    except Exception as e:
        logger.warning(f"Simulation execution failed (expected if Ollama/Gemma 4 is not active): {e}")
        
    logger.info("Simulation run complete. Trajectory and regression tests grown via Mycelium (ShadowScripter).")

if __name__ == "__main__":
    asyncio.run(run_simulation())
