"""
Counterfactual History Simulation.

This simulation demonstrates Gateway 3 (World Models) capabilities by
using physics-informed prediction to simulate "what-if" scenarios.
It creates a branching thought-trajectory to explore alternative futures.

Author: Cohezion Agentic Team (Gemini 3 Pro)
Date: 2026-01-18
"""

import asyncio
import logging
import torch
import numpy as np
from pathlib import Path

from cohezion.flume.autoencoder import FlumeEncoder
from cohezion.flume.predictor import TrajectoryPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_simulation():
    logger.info("Initializing Counterfactual History Simulation...")
    
    # Initialize models
    encoder = FlumeEncoder(z_dim=256)
    predictor = TrajectoryPredictor(z_dim=256)
    
    # 1. Define Historical Context
    # "The fall of a civilization due to resource depletion"
    seed_text = "Civilization expands rapidly, consuming finite resources."
    z_start = encoder.encode(seed_text)
    
    logger.info(f"Seed Event: '{seed_text}'")
    
    # 2. Main Timeline (Business as Usual)
    logger.info("Projecting Main Timeline (No Intervention)...")
    main_timeline = predictor.predict_with_physics(z_start, steps=5, physics_weight=0.2)
    final_main = encoder.decode(main_timeline[-1])[0]
    logger.info(f"Main Outcome: {final_main}")
    
    # 3. Branching Event: "Discovery of Fusion Energy"
    logger.info("Triggering Branch Event: 'Discovery of Fusion Energy'...")
    
    # Create branch point by semantically adding "infinite energy" to the state at step 2
    z_at_branch = main_timeline[2]
    direction = encoder.semantic_direction("scarcity", "abundance")
    z_branch_start = encoder.semantic_add(z_at_branch, direction, scale=0.5)
    
    # 4. Predict Counterfactual Timeline
    logger.info("Projecting Counterfactual Timeline...")
    branch_timeline = predictor.predict_with_physics(z_branch_start, steps=5, physics_weight=0.2)
    final_branch = encoder.decode(branch_timeline[-1])[0]
    logger.info(f"Counterfactual Outcome: {final_branch}")
    
    # 5. Measure Divergence
    # Euclidean distance between final states
    divergence = torch.norm(main_timeline[-1] - branch_timeline[-1])
    logger.info(f"Timeline Divergence: {divergence.item():.4f}")
    
    # 6. Branch 2: "Global Conflict"
    logger.info("Triggering Branch 2: 'Global Conflict'...")
    direction_conflict = encoder.semantic_direction("peace", "war")
    z_branch_conflict = encoder.semantic_add(z_at_branch, direction_conflict, scale=0.8)
    
    conflict_timeline = predictor.predict_with_physics(z_branch_conflict, steps=5, physics_weight=0.2)
    final_conflict = encoder.decode(conflict_timeline[-1])[0]
    logger.info(f"Conflict Outcome: {final_conflict}")
    
    divergence_conflict = torch.norm(main_timeline[-1] - conflict_timeline[-1])
    logger.info(f"Conflict Divergence: {divergence_conflict.item():.4f}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
