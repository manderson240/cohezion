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


# Wiring-sweep 2026-06-22: anomaly_gate.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.anomaly_gate import AnomalyGate as AnomalyGate
    from cohezion.physics.anomaly_gate import AnomalyVerdict as AnomalyVerdict
    from cohezion.physics.anomaly_gate import InvariantKind as InvariantKind
    from cohezion.physics.anomaly_gate import LocalSkeptic as LocalSkeptic

# Wiring-sweep 2026-06-22: anomaly_quarantine.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.anomaly_quarantine import AnomalyQuarantine as AnomalyQuarantine
    from cohezion.physics.anomaly_quarantine import QuarantineRecord as QuarantineRecord

# Wiring-sweep 2026-06-22: conservation_filter.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.conservation_filter import ConservationFilter as ConservationFilter
    from cohezion.physics.conservation_filter import ConservationResult as ConservationResult
    from cohezion.physics.conservation_filter import Verdict as Verdict

# Wiring-sweep 2026-06-22: hamiltonian.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.hamiltonian import HamiltonianDynamics as HamiltonianDynamics
    from cohezion.physics.hamiltonian import PotentialType as PotentialType

# Wiring-sweep 2026-06-22: invariant_checker.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.invariant_checker import InvariantChecker as InvariantChecker
    from cohezion.physics.invariant_checker import InvariantReport as InvariantReport
    from cohezion.physics.invariant_checker import ObligationStatus as ObligationStatus

# Wiring-sweep 2026-06-22: manifold_utils.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.manifold_utils import SemanticLagrangeFinder as SemanticLagrangeFinder

# Wiring-sweep 2026-06-22: mereon_projector.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.mereon_projector import MereonProjector as MereonProjector
    from cohezion.physics.mereon_projector import ProjectionResult as ProjectionResult

# Wiring-sweep 2026-06-22: observer_patch.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.observer_patch import ConsistencyResult as ConsistencyResult
    from cohezion.physics.observer_patch import ObserverPatch as ObserverPatch
    from cohezion.physics.observer_patch import overlap_fraction as overlap_fraction

# Wiring-sweep 2026-06-22: ouroboros_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.ouroboros_bridge import HealingPhase as HealingPhase
    from cohezion.physics.ouroboros_bridge import OuroborosBridge as OuroborosBridge
    from cohezion.physics.ouroboros_bridge import PhysicsAnomaly as PhysicsAnomaly

# Wiring-sweep 2026-06-22: usd_simulator.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.usd_simulator import ItonicCluster as ItonicCluster
    from cohezion.physics.usd_simulator import USDSimulator as USDSimulator

# Wiring-sweep 2026-06-22: vliw_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.physics.vliw_bridge import VLIWBridge as VLIWBridge
    from cohezion.physics.vliw_bridge import VLIWBridgeState as VLIWBridgeState
