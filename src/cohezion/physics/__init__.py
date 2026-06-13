# Cohezion Physics Package
"""
Physics modules for the Universe Simulation and Genesis Engine.

Includes dimensionality extraction, Hamiltonian dynamics, and
SU(2) spinor algebra for grounded SPIN coherence.
"""

from cohezion.physics.bioelectric_model import BioelectricNetwork
from cohezion.physics.dielectric import DielectricField
from cohezion.physics.ionic_cluster import IonicClusterState
from cohezion.physics.lenr import LENRHamiltonian
from cohezion.physics.cellular_automata import (
    CAEngine,
    CAGrid2D,
    CARule,
    CAState,
    ComplexityMetrics2D,
    CosmogonyCA,
    EVOEmergence,
    EVOPattern,
    LemonadeCAAdvisor,
    TotalisticRule2D,
    WolframClass,
    ca_rl_step,
)
from cohezion.physics.cosmogony import SymmetryBreaking, SymmetryGroup
from cohezion.physics.dimension_extractor import DimensionExtractor
from cohezion.physics.evo_model import ExoticVacuumObject
from cohezion.physics.fiber_bundle import FiberBundle
from cohezion.physics.gauge_theory import FourFabricGauge, GaugeConnection
from cohezion.physics.information_geometry import FisherInformationMetric
from cohezion.physics.lagrangian import LagrangianDynamics
from cohezion.physics.natural_capital import NaturalCapitalValuation
from cohezion.physics.rewards_bridge import CoherenceRatchet, RewardsBridge
from cohezion.physics.riemannian_metric import RiemannianMetric
from cohezion.physics.spinor import SpinorState


__all__ = [
    "BioelectricNetwork",
    "DielectricField",
    "IonicClusterState",
    "LENRHamiltonian",
    "CAEngine",
    "CAGrid2D",
    "CARule",
    "CAState",
    "ComplexityMetrics2D",
    "CosmogonyCA",
    "EVOEmergence",
    "EVOPattern",
    "LemonadeCAAdvisor",
    "TotalisticRule2D",
    "WolframClass",
    "ca_rl_step",
    "CoherenceRatchet",
    "DimensionExtractor",
    "ExoticVacuumObject",
    "FiberBundle",
    "FisherInformationMetric",
    "FourFabricGauge",
    "GaugeConnection",
    "LagrangianDynamics",
    "NaturalCapitalValuation",
    "RewardsBridge",
    "RiemannianMetric",
    "SpinorState",
    "SymmetryBreaking",
    "SymmetryGroup",
]
