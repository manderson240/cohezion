# Cohezion FLUME Package
"""
FLUME: Fluid Latent Understanding through Manifold Encoding

Treats thought as continuous fluid motion rather than discrete tokens.
Inspired by CALM (Kyutai Labs) but applied to semantic reasoning.

Implements:
- FlumeEncoder: Compress K tokens → single dense vector z (256-dim)
- TrajectoryPredictor: Predict trajectory of thought vectors over time
"""

from cohezion.flume.autoencoder import FlumeEncoder
from cohezion.flume.predictor import TrajectoryPredictor

# Backwards compatibility alias
ThoughtAutoencoder = FlumeEncoder

__all__ = ["FlumeEncoder", "TrajectoryPredictor", "ThoughtAutoencoder"]
