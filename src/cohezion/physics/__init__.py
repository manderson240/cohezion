# Cohezion Physics Package
"""
Physics modules for the Universe Simulation and Genesis Engine.

Includes dimensionality extraction, Hamiltonian dynamics, and
SU(2) spinor algebra for grounded SPIN coherence.
"""

import contextlib


# Wiring-sweep 2026-06-06: flier_routing was a genuine import-graph orphan. Guarded re-export
# makes its router part of the physics surface + statically reachable (cycle-safe).
with contextlib.suppress(Exception):
    from cohezion.physics.flier_routing import (
        FLIERRouter as FLIERRouter,
    )
    from cohezion.physics.flier_routing import (
        QubitNode as QubitNode,
    )

# Wiring-sweep 2026-06-06: mhd_mereon was a genuine import-graph orphan (cycle-safe).
with contextlib.suppress(Exception):
    from cohezion.physics.mhd_mereon import (
        MHDMereonOperator as MHDMereonOperator,
    )
    from cohezion.physics.mhd_mereon import (
        MHDState as MHDState,
    )

# Wiring-sweep 2026-06-06: mereon_data was a genuine import-graph orphan (functions only).
with contextlib.suppress(Exception):
    from cohezion.physics.mereon_data import (
        get_m120p_vertices as get_m120p_vertices,
    )
    from cohezion.physics.mereon_data import (
        get_m144p_vertices as get_m144p_vertices,
    )

from cohezion.physics.bioelectric_model import BioelectricNetwork
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
