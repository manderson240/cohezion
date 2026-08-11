"""EVO Trajectory Visualizer — Graph and visualizer for EVO agentic journeys.

Converts FLUME 12D state vectors and EVO witness marks into 3D graph data
for visualization in the 3D Cockpit and Obsidian Vault.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.flume.vacuum_topology import VacuumLabel, VacuumTopologyClassifier
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.physics.evo_model import ExoticVacuumObject


logger = logging.getLogger(__name__)


@dataclass
class EVOTrajectoryPoint:
    """A single point along an agentic EVO trajectory."""

    step: int
    agent_id: str
    action: str
    state_12d: np.ndarray
    coherence: float
    topology: VacuumLabel
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "agent_id": self.agent_id,
            "action": self.action,
            "state_12d": [round(float(x), 4) for x in self.state_12d],
            "coherence": round(self.coherence, 4),
            "topology": self.topology.to_dict(),
            "timestamp": self.timestamp,
        }


class EVOJourneyVisualizer:
    """Converts FLUME 12D agentic trajectories into 3D Cockpit Graph Data."""

    def __init__(self, output_path: str = ".obsidian/evo-3d-graph.json"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.vae_encoder = FlumeVAEEncoder()
        self.topology_classifier = VacuumTopologyClassifier()

    def process_evo(self, evo: ExoticVacuumObject, actions: list[str]) -> dict[str, Any]:
        """Process an EVO lifecycle agent into a 3D graph trajectory."""
        nodes = []
        edges = []

        for i, action in enumerate(actions, start=1):
            evo.coherent_phase(0.85 + (0.10 * (i % 2)))
            evo.produce_witness_mark("decision", action)

            # Encode via FLUME VAE and project 256D -> 12D via holographic Hadamard matrix
            latent_256d = self.vae_encoder.encode(f"{evo.agent_id}:{action}")

            # Deterministic projection matrix (12 x 256) based on 12D fabric slices
            idx = np.arange(256)
            proj_matrix = np.sin(np.outer(np.arange(12) + 1, idx + 1) * (np.pi / 16.0))
            state_12d = proj_matrix @ latent_256d

            # Add action-type & step dynamics for topological resonance
            if i % 2 == 1:
                # Oscillatory instanton dynamics (alternating modes)
                state_12d += (
                    np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
                    * 0.4
                )
            else:
                # Coherent soliton dynamics (localized spatial energy)
                state_12d += (
                    np.array([0.8, 0.8, 0.8, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]) * 0.4
                )

            # Sanitize input vector against NaN / Inf vulnerabilities
            state_12d = np.nan_to_num(state_12d, nan=0.0, posinf=1.0, neginf=-1.0)
            norm = np.linalg.norm(state_12d)
            if not np.isfinite(norm) or norm == 0.0:
                state_12d_norm = np.zeros(12, dtype=np.float64)
            else:
                state_12d_norm = state_12d / norm

            topology = self.topology_classifier.classify(state_12d_norm)

            node_id = f"evo_{evo.agent_id}_step_{i}"

            # Map topology to visualization colors
            color_map = {
                "instanton": "#ff0055",  # Rapid tunneling transition (Magenta/Red)
                "soliton": "#00e5ff",  # Coherent persistent state (Cyan/Blue)
                "trivial": "#78909c",  # Vacuum baseline (Grey)
            }

            nodes.append(
                {
                    "id": node_id,
                    "label": f"EVO Step {i}: {action[:30]}",
                    "agent_id": evo.agent_id,
                    "topology": topology.label,
                    "confidence": topology.confidence,
                    "coherence": round(float(evo.coherence_history[-1]), 4),
                    "state_12d": [round(float(x), 4) for x in state_12d],
                    "color": color_map.get(topology.label, "#00ff41"),
                    "size": 6.0 + (topology.confidence * 4.0),
                }
            )

            if i > 1:
                prev_id = f"evo_{evo.agent_id}_step_{i - 1}"
                edges.append(
                    {
                        "source": prev_id,
                        "target": node_id,
                        "type": "evo_transition",
                    }
                )

        graph_data = {
            "meta": {
                "agent_id": evo.agent_id,
                "universe_id": evo.universe_id,
                "total_steps": len(actions),
                "binding_energy": round(evo.binding_energy, 4),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "nodes": nodes,
            "edges": edges,
        }

        with open(self.output_path, "w") as f:
            json.dump(graph_data, f, indent=2)

        logger.info("Exported EVO trajectory (%d steps) to %s", len(nodes), self.output_path)
        return graph_data
