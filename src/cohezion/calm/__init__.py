# Cohezion CALM Package
"""
Continuous Autoregressive Language Models - treating thought as fluid motion.

Implements the CALM abstraction from the vision document:
- Autoencoder: Compress K tokens → single dense vector z
- Predictor: Predict trajectory of thought vectors over time
"""

from cohezion.calm.autoencoder import ThoughtAutoencoder
from cohezion.calm.predictor import TrajectoryPredictor

__all__ = ["ThoughtAutoencoder", "TrajectoryPredictor"]
