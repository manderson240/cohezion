from __future__ import annotations

"""Hierarchical Swarm Topology definitions for Cohezion."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class NodeRole(Enum):
    """Roles for swarm nodes, mapped to the Expert Domain Lattice (EDL)."""

    EXECUTIVE = "executive"  # Quadrature Nexus
    ARCHITECT = "architect"  # Conceptual Design / Coordination
    ENGINEER = "engineer"  # Physics / Hardware Simulation
    BIOLOGIST = "biologist"  # Life / Organic Modularity
    QUANTUM_HW = "quantum_hw"  # Low-level Compute / Substrate
    QUANTUM_ALGO = "quantum_algo"  # Algorithmic Innovation
    OBSERVER = "observer"  # Monitoring and Telemetry


@dataclass
class SwarmNode:
    """A node in the hierarchical swarm."""

    node_id: str = field(default_factory=lambda: f"node_{uuid4().hex[:8]}")
    role: NodeRole = NodeRole.ARCHITECT
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegionalSwarm:
    """A specialized swarm mapped to one of the 4 Quadrature Fabrics."""

    swarm_id: str = field(default_factory=lambda: f"swarm_{uuid4().hex[:8]}")
    lead: SwarmNode = field(default_factory=lambda: SwarmNode(role=NodeRole.ARCHITECT))
    workers: list[SwarmNode] = field(default_factory=list)
    fabric: str = "space"  # space, field, control, precipitation
    domain: str = "general"
    parent_swarm_id: str | None = None


@dataclass
class SwarmTopology:
    """The global hierarchical structure of the swarm."""

    topology_id: str = field(default_factory=lambda: f"top_{uuid4().hex[:8]}")
    executive: SwarmNode = field(default_factory=lambda: SwarmNode(role=NodeRole.EXECUTIVE))
    regions: dict[str, RegionalSwarm] = field(default_factory=dict)
    
    def add_region(self, region: RegionalSwarm) -> None:
        """Add a regional swarm to the topology."""
        self.regions[region.swarm_id] = region
        region.parent_swarm_id = "sovereign"

    def get_node_by_id(self, node_id: str) -> SwarmNode | None:
        """Find a node by its ID."""
        if self.executive.node_id == node_id:
            return self.executive
        for region in self.regions.values():
            if region.lead.node_id == node_id:
                return region.lead
            for worker in region.workers:
                if worker.node_id == node_id:
                    return worker
        return None
