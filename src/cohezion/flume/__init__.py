# Cohezion FLUME Package
"""
FLUME: Fluid Latent Understanding through Manifold Encoding

Treats thought as continuous fluid motion rather than discrete tokens.
Inspired by CALM (Kyutai Labs) but applied to semantic reasoning.

Implements:
- FlumeEncoder: Compress K tokens → single dense vector z (256-dim)
- TrajectoryPredictor: Predict trajectory of thought vectors over time
"""

from cohezion.flume.alignment import LatentAligner
from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder
from cohezion.flume.predictor import TrajectoryPredictor
from cohezion.flume.tokenizer import FlumeTokenizer

# Backwards compatibility alias
ThoughtAutoencoder = FlumeEncoder

__all__ = [
    "FlumeEncoder",
    "FlumeConfig",
    "FlumeTokenizer",
    "LatentAligner",
    "TrajectoryPredictor",
    "ThoughtAutoencoder",
]
