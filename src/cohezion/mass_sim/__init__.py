"""Mass Simulation System - FLUME + Quadrature Nexus Swarm Orchestration.

Captures agentic journeys across unique universe configurations using
the Rust-optimized FlumePhysics engine with rayon parallelism.

Usage:
    from cohezion.mass_sim import MassSimOrchestrator, SimulationConfig, SCALE_TIERS

    config = SimulationConfig(scale=SCALE_TIERS["demo"])
    orchestrator = MassSimOrchestrator(config)
    report = await orchestrator.run()
"""

from cohezion.mass_sim.config import SCALE_TIERS, ScaleTier, SimulationConfig
from cohezion.mass_sim.orchestrator import MassSimOrchestrator


__all__ = [
    "SCALE_TIERS",
    "MassSimOrchestrator",
    "ScaleTier",
    "SimulationConfig",
]
