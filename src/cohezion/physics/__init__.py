# Cohezion Physics Package
"""
Physics modules for the Universe Simulation and Genesis Engine.

Includes dimensionality extraction, Hamiltonian dynamics, and
SU(2) spinor algebra for grounded SPIN coherence.
"""

from cohezion.physics.cosmogony import SymmetryBreaking, SymmetryGroup
from cohezion.physics.dimension_extractor import DimensionExtractor
from cohezion.physics.fiber_bundle import FiberBundle
from cohezion.physics.gauge_theory import FourFabricGauge, GaugeConnection
from cohezion.physics.information_geometry import FisherInformationMetric
from cohezion.physics.lagrangian import LagrangianDynamics
from cohezion.physics.riemannian_metric import RiemannianMetric
from cohezion.physics.spinor import SpinorState


__all__ = [
    "DimensionExtractor",
    "FiberBundle",
    "FisherInformationMetric",
    "FourFabricGauge",
    "GaugeConnection",
    "LagrangianDynamics",
    "RiemannianMetric",
    "SpinorState",
    "SymmetryBreaking",
    "SymmetryGroup",
]
