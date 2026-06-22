"""Mass Simulation System - FLUME + Quadrature Nexus Swarm Orchestration.

Captures agentic journeys across unique universe configurations using
the Rust-optimized FlumePhysics engine with rayon parallelism.

Usage:
    from cohezion.mass_sim import MassSimOrchestrator, SimulationConfig, SCALE_TIERS

    config = SimulationConfig(scale=SCALE_TIERS["demo"])
    orchestrator = MassSimOrchestrator(config)
    report = await orchestrator.run()
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.mass_sim.config import SCALE_TIERS as SCALE_TIERS
    from cohezion.mass_sim.config import ScaleTier as ScaleTier
    from cohezion.mass_sim.config import SimulationConfig as SimulationConfig

with contextlib.suppress(Exception):
    from cohezion.mass_sim.orchestrator import MassSimOrchestrator as MassSimOrchestrator


# Wiring-sweep 2026-06-22: agent_factory.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.agent_factory import AgentFactory as AgentFactory

# Wiring-sweep 2026-06-22: analysis.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.analysis import SimulationAnalyzer as SimulationAnalyzer

# Wiring-sweep 2026-06-22: artifacts.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.artifacts import ArtifactGenerator as ArtifactGenerator

# Wiring-sweep 2026-06-22: batch_runner.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.batch_runner import (
        BatchSimulationRunner as BatchSimulationRunner,
    )

# Wiring-sweep 2026-06-22: exporter.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.exporter import CheckpointExporter as CheckpointExporter

# Wiring-sweep 2026-06-22: flume_physics_py.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.flume_physics_py import FlumePhysicsPy as FlumePhysicsPy

# Wiring-sweep 2026-06-22: persistence.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.persistence import (
        SimulationPersistence as SimulationPersistence,
    )

# Wiring-sweep 2026-06-22: system_monitor.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.system_monitor import (
        MemoryGuard as MemoryGuard,
    )
    from cohezion.mass_sim.system_monitor import (
        SystemVitals as SystemVitals,
    )

# Wiring-sweep 2026-06-22: universe_factory.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.mass_sim.universe_factory import UniverseFactory as UniverseFactory


__all__ = [
    "SCALE_TIERS",
    "AgentFactory",
    "ArtifactGenerator",
    "BatchSimulationRunner",
    "CheckpointExporter",
    "FlumePhysicsPy",
    "MassSimOrchestrator",
    "MemoryGuard",
    "ScaleTier",
    "SimulationAnalyzer",
    "SimulationConfig",
    "SimulationPersistence",
    "SystemVitals",
    "UniverseFactory",
]
