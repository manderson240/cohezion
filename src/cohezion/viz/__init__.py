# Cohezion Visualization Package
"""
Visualization engines for the Universe Simulation.

- ManimRenderer: 3D animated visualization using Manim
- HyperToolsRenderer: Interactive high-dimensional data visualization
"""

from cohezion.viz.hypertools_renderer import HyperToolsViz
from cohezion.viz.manim_renderer import ManimRenderer

__all__ = ["ManimRenderer", "HyperToolsViz"]
