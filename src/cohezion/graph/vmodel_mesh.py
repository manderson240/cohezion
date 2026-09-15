"""Systems Engineering V-Model Mesh Engine.

Implements formal Systems Engineering V-Model verification and traceability,
linking Left-Leg Specifications (L0..L3) across to Right-Leg Verification Gates
(R0..R3) through bottom-vertex AutonomousLoop execution engines and Proof Obligations.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np


class VModelLevel(StrEnum):
    """Systems Engineering V-Model abstraction levels."""

    L0_OPERATIONAL_INTENT = "L0_OPERATIONAL_INTENT"
    L1_SYSTEM_REQUIREMENT = "L1_SYSTEM_REQUIREMENT"
    L2_SUBSYSTEM_SPEC = "L2_SUBSYSTEM_SPEC"
    L3_COMPONENT_CONTRACT = "L3_COMPONENT_CONTRACT"
    VERTEX_EXECUTION = "VERTEX_EXECUTION"
    R3_UNIT_AUTOHARNESS = "R3_UNIT_AUTOHARNESS"
    R2_INTEGRATION_CONTRACT = "R2_INTEGRATION_CONTRACT"
    R1_SYSTEM_QUALIFICATION = "R1_SYSTEM_QUALIFICATION"
    R0_ACCEPTANCE = "R0_ACCEPTANCE"

    @property
    def counterpart(self) -> VModelLevel:
        """Return symmetrical counterpart across the V-Model."""
        mapping = {
            VModelLevel.L0_OPERATIONAL_INTENT: VModelLevel.R0_ACCEPTANCE,
            VModelLevel.L1_SYSTEM_REQUIREMENT: VModelLevel.R1_SYSTEM_QUALIFICATION,
            VModelLevel.L2_SUBSYSTEM_SPEC: VModelLevel.R2_INTEGRATION_CONTRACT,
            VModelLevel.L3_COMPONENT_CONTRACT: VModelLevel.R3_UNIT_AUTOHARNESS,
            VModelLevel.VERTEX_EXECUTION: VModelLevel.VERTEX_EXECUTION,
            VModelLevel.R3_UNIT_AUTOHARNESS: VModelLevel.L3_COMPONENT_CONTRACT,
            VModelLevel.R2_INTEGRATION_CONTRACT: VModelLevel.L2_SUBSYSTEM_SPEC,
            VModelLevel.R1_SYSTEM_QUALIFICATION: VModelLevel.L1_SYSTEM_REQUIREMENT,
            VModelLevel.R0_ACCEPTANCE: VModelLevel.L0_OPERATIONAL_INTENT,
        }
        return mapping[self]


class ProofStatus(StrEnum):
    """Proof obligation status."""

    UNVERIFIED = "UNVERIFIED"
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"


@dataclass(slots=True)
class ProofObligation:
    """Formal proof obligation or verification invariant."""

    id: str
    formula: str
    verifier: str  # "autoharness", "zkfv", "lyapunov", "multiperspective", "unit_test"
    status: ProofStatus = ProofStatus.UNVERIFIED
    proof_hash: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def satisfy(self, proof_hash: str) -> None:
        """Mark proof obligation as satisfied with cryptographic or bytecode hash."""
        self.status = ProofStatus.SATISFIED
        self.proof_hash = proof_hash
        self.timestamp = time.time()

    def violate(self, reason: str) -> None:
        """Mark proof obligation as violated."""
        self.status = ProofStatus.VIOLATED
        self.metadata["violation_reason"] = reason
        self.timestamp = time.time()

    def to_surreal_record(self) -> str:
        """Formatted SurrealDB record ID."""
        if ":" in self.id:
            return self.id
        return f"proof_obligation:{self.id}"


@dataclass(slots=True)
class VModelGate:
    """Right-leg verification gate gating stage completion."""

    id: str
    level: VModelLevel
    name: str
    obligations: list[ProofObligation] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_obligation(self, obligation: ProofObligation) -> None:
        self.obligations.append(obligation)

    @property
    def is_unlocked(self) -> bool:
        """Gate unlocks only if all obligations are satisfied."""
        if not self.obligations:
            return False
        return all(ob.status == ProofStatus.SATISFIED for ob in self.obligations)

    def to_surreal_record(self) -> str:
        """Formatted SurrealDB record ID."""
        if ":" in self.id:
            return self.id
        return f"vmodel_gate:{self.id}"


@dataclass(slots=True)
class VModelSpec:
    """Left-leg specification or operational requirement."""

    id: str
    level: VModelLevel
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surreal_record(self) -> str:
        """Formatted SurrealDB record ID."""
        if ":" in self.id:
            return self.id
        return f"vmodel_spec:{self.id}"


@dataclass(slots=True)
class VModelMeshEngine:
    """Engine managing Systems Engineering V-Model mesh traceability and gates."""

    specs: dict[str, VModelSpec] = field(default_factory=dict)
    gates: dict[str, VModelGate] = field(default_factory=dict)
    traceability_links: dict[str, str] = field(default_factory=dict)  # spec_id -> gate_id

    def register_spec(
        self,
        spec_id: str,
        level: VModelLevel,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> VModelSpec:
        """Register a specification on the left leg of the V-Model."""
        spec = VModelSpec(
            id=spec_id,
            level=level,
            description=description,
            metadata=metadata or {},
        )
        self.specs[spec_id] = spec
        return spec

    def create_gate(
        self,
        gate_id: str,
        level: VModelLevel,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> VModelGate:
        """Factory for right-leg verification gates."""
        return VModelGate(
            id=gate_id,
            level=level,
            name=name,
            metadata=metadata or {},
        )

    def register_gate(self, gate: VModelGate) -> None:
        """Register a right-leg gate in the mesh."""
        self.gates[gate.id] = gate

    def link_traceability(self, spec_id: str, gate_id: str) -> None:
        """Create bidirectional traceability link across the V."""
        if spec_id not in self.specs:
            raise KeyError(f"Spec {spec_id} not registered.")
        if gate_id not in self.gates:
            raise KeyError(f"Gate {gate_id} not registered.")
        self.traceability_links[spec_id] = gate_id

    def is_level_closed(self, level: VModelLevel) -> bool:
        """Check if all specs at the given level are verified by unlocked gates."""
        level_specs = [s for s in self.specs.values() if s.level == level]
        if not level_specs:
            return False

        for spec in level_specs:
            gate_id = self.traceability_links.get(spec.id)
            if not gate_id:
                return False
            gate = self.gates.get(gate_id)
            if not gate or not gate.is_unlocked:
                return False

        return True

    def is_mesh_closed(self) -> bool:
        """Check if entire V-Model (all left-leg levels) is closed."""
        left_levels = [
            VModelLevel.L0_OPERATIONAL_INTENT,
            VModelLevel.L1_SYSTEM_REQUIREMENT,
            VModelLevel.L2_SUBSYSTEM_SPEC,
            VModelLevel.L3_COMPONENT_CONTRACT,
        ]
        active_left_levels = {s.level for s in self.specs.values() if s.level in left_levels}
        if not active_left_levels:
            return False
        return all(self.is_level_closed(lvl) for lvl in active_left_levels)

    def to_surrealql(self) -> str:
        """Export V-Model mesh into idempotent SurrealQL statements."""
        statements: list[str] = []

        # 1. Specs
        for spec in self.specs.values():
            rec_id = spec.to_surreal_record()
            payload = json.dumps(
                {
                    "level": spec.level.value,
                    "description": spec.description,
                    "metadata": spec.metadata,
                }
            )
            statements.append(f"UPSERT {rec_id} CONTENT {payload};")

        # 2. Gates
        for gate in self.gates.values():
            rec_id = gate.to_surreal_record()
            payload = json.dumps(
                {
                    "level": gate.level.value,
                    "name": gate.name,
                    "is_unlocked": gate.is_unlocked,
                    "obligation_count": len(gate.obligations),
                    "metadata": gate.metadata,
                }
            )
            statements.append(f"UPSERT {rec_id} CONTENT {payload};")

            # Obligations
            for ob in gate.obligations:
                ob_id = ob.to_surreal_record()
                ob_payload = json.dumps(
                    {
                        "formula": ob.formula,
                        "verifier": ob.verifier,
                        "status": ob.status.value,
                        "proof_hash": ob.proof_hash,
                        "timestamp": ob.timestamp,
                    }
                )
                statements.append(f"UPSERT {ob_id} CONTENT {ob_payload};")
                statements.append(f"RELATE {rec_id}->PROVES->{ob_id};")

        # 3. Traceability links
        for spec_id, gate_id in self.traceability_links.items():
            s_rec = self.specs[spec_id].to_surreal_record()
            g_rec = self.gates[gate_id].to_surreal_record()
            statements.append(f"RELATE {s_rec}->VERIFIED_BY->{g_rec};")

        return "\n".join(statements)

    def to_knowledge_graph_mesh(self) -> Any:
        """Export V-Model mesh into unified KnowledgeGraphMesh with Poincaré hyperbolic coordinates."""
        from cohezion.graph.graph_engine import EdgeType, KnowledgeGraphMesh

        kg = KnowledgeGraphMesh()

        # Hyperbolic coordinates: radius corresponds to abstraction depth, angle corresponds to V leg
        level_geometry: dict[VModelLevel, tuple[float, float]] = {
            VModelLevel.L0_OPERATIONAL_INTENT: (0.20, -math.pi / 4),
            VModelLevel.L1_SYSTEM_REQUIREMENT: (0.40, -3 * math.pi / 8),
            VModelLevel.L2_SUBSYSTEM_SPEC: (0.60, -math.pi / 2),
            VModelLevel.L3_COMPONENT_CONTRACT: (0.75, -5 * math.pi / 8),
            VModelLevel.VERTEX_EXECUTION: (0.88, -math.pi),
            VModelLevel.R3_UNIT_AUTOHARNESS: (0.75, 5 * math.pi / 8),
            VModelLevel.R2_INTEGRATION_CONTRACT: (0.60, math.pi / 2),
            VModelLevel.R1_SYSTEM_QUALIFICATION: (0.40, 3 * math.pi / 8),
            VModelLevel.R0_ACCEPTANCE: (0.20, math.pi / 4),
        }

        def _poincare_vector(level: VModelLevel) -> np.ndarray:
            r, theta = level_geometry.get(level, (0.50, 0.0))
            vec = np.zeros(2048, dtype=np.float32)
            vec[0] = float(r * math.cos(theta))
            vec[1] = float(r * math.sin(theta))
            # Ensure strict boundary clamping
            norm = float(np.linalg.norm(vec))
            if norm >= 1.0 - 1e-5:
                vec = vec * ((1.0 - 1e-5) / max(norm, 1e-12))
            return vec

        # Add specs as nodes
        for spec in self.specs.values():
            emb = _poincare_vector(spec.level)
            kg.add_node(
                node_id=spec.id,
                node_type="vmodel_spec",
                properties={"level": spec.level.value, "description": spec.description},
                embedding=emb,
            )

        # Add gates as nodes
        for gate in self.gates.values():
            emb = _poincare_vector(gate.level)
            kg.add_node(
                node_id=gate.id,
                node_type="vmodel_gate",
                properties={"level": gate.level.value, "name": gate.name, "unlocked": gate.is_unlocked},
                embedding=emb,
            )

        # Add traceability edges
        for spec_id, gate_id in self.traceability_links.items():
            if spec_id in kg.nodes and gate_id in kg.nodes:
                kg.add_edge(
                    in_node_id=spec_id,
                    relation=EdgeType.SATISFIES,
                    out_node_id=gate_id,
                    weight=1.0,
                )

        return kg

