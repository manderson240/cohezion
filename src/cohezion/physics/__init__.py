# Cohezion Physics Package
"""
Physics modules for the Universe Simulation and Genesis Engine.

Includes dimensionality extraction, Hamiltonian dynamics, and
SU(2) spinor algebra for grounded SPIN coherence.
"""

# Stealthskater extended substrate library — Phase 18
from cohezion.physics.bec_bridge import BECState, MercuryLattice
from cohezion.physics.bioelectric_model import BioelectricNetwork
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
from cohezion.physics.colibre_bridge import AgentAsEVO, ColibreState
from cohezion.physics.cosmogony import SymmetryBreaking, SymmetryGroup
from cohezion.physics.dielectric import DielectricField
from cohezion.physics.dimension_extractor import DimensionExtractor
from cohezion.physics.evo_model import ExoticVacuumObject
from cohezion.physics.fiber_bundle import FiberBundle
from cohezion.physics.gauge_theory import FourFabricGauge, GaugeConnection
from cohezion.physics.information_geometry import FisherInformationMetric
from cohezion.physics.ionic_cluster import IonicClusterState
from cohezion.physics.lagrangian import LagrangianDynamics
from cohezion.physics.lenr import LENRHamiltonian
from cohezion.physics.mhd_plasma import BismuthDiamagnet, MHDEquilibrium
from cohezion.physics.natural_capital import NaturalCapitalValuation
from cohezion.physics.rewards_bridge import CoherenceRatchet, RewardsBridge
from cohezion.physics.riemannian_metric import RiemannianMetric
from cohezion.physics.sarfatti_bridge import QuarkGluonPlasma, SarfattiBackAction
from cohezion.physics.spinor import SpinorState
from cohezion.physics.tensor_metric_engineering import TensorMetricEngineering
from cohezion.physics.toroidal_moment import FractalToroidalMoment


__all__ = [
    # Phase 18 extended substrate library
    "AgentAsEVO",
    "BECState",
    "BismuthDiamagnet",
    "ColibreState",
    "FractalToroidalMoment",
    "MercuryLattice",
    "MHDEquilibrium",
    "QuarkGluonPlasma",
    "SarfattiBackAction",
    "TensorMetricEngineering",
    # Core physics
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
