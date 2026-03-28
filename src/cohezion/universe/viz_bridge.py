"""
Visualization Bridge - Manifold to 3D Cockpit Projection.
Converts 12D AxiomaticState trajectories into GraphData for the
Hyperdimensional Visualization Plugin.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from cohezion.universe.engine import UniverseJourney


logger = logging.getLogger(__name__)


class VisualizationBridge:
    """Bridges the 12D manifold simulation with the Three.js 3D Cockpit."""

    def __init__(self, output_path: str = ".obsidian/3d-graph-data.json"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def project_journey(self, journey: UniverseJourney) -> dict[str, Any]:
        """Project a single journey into graph data format."""
        nodes = []
        edges = []

        # 1. Create a node for each trajectory point
        for i, point in enumerate(journey.trajectory):
            node_id = f"{journey.id}_step_{point.step_number}"
            state = point.axiomatic

            # Map AxiomaticState to GraphNode dimensions
            # Heuristic mapping for Phase 2 compatibility:
            nodes.append(
                {
                    "id": node_id,
                    "label": f"Step {point.step_number}: {point.action_taken[:20]}",
                    "file_path": f"journeys/{journey.id}.md",
                    "type": "experiment",
                    "connectivity": state.logic,  # Logic ~ Connectivity
                    "cross_domain": state.novelty,  # Novelty ~ Cross-domain
                    "completion": state.precipitation,  # Precipitation ~ Completion
                    "temporal": state.temporal % 1.0,  # Normalization 0-1
                    "recency": point.coherence,  # Coherence ~ Recency/Active
                    "conceptual_depth": state.physics,  # Physics ~ Theory depth
                    "tags": [journey.agent_name, point.action_taken],
                    "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(point.timestamp)),
                    "wiki_links_count": 1,
                    "is_bridging": state.spin_coherence > 0.8,
                    "is_orphaned": False,
                    "theory_leaning": state.physics > 0.5,
                    "suggested_color": "#00ff41" if point.coherence > 0.8 else "#ffcc00",
                    "suggested_size": 5.0 + (point.coherence * 5.0),
                }
            )

            # 2. Create edges between sequential points
            if i > 0:
                edges.append(
                    {
                        "source": f"{journey.id}_step_{journey.trajectory[i - 1].step_number}",
                        "target": node_id,
                        "weight": point.coherence,
                        "type": "agent_journey",
                    }
                )

        graph_data = {
            "meta": {
                "export_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "Cohezion Simulation Engine",
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "phase": "2 (Agent Journey)",
            },
            "dimensions": {
                "connectivity": "Logic (Rotation)",
                "cross_domain": "Novelty (Particularization)",
                "completion": "Precipitation",
                "temporal": "Awareness (Temporal)",
                "recency": "Coherence Score",
                "conceptual_depth": "Physics (Tempic)",
            },
            "visual_mappings": {"color": "Coherence", "size": "Stability"},
            "nodes": nodes,
            "edges": edges,
        }

        return graph_data

    def export_journey(self, journey: UniverseJourney):
        """Export journey data to the plugin's data file."""
        data = self.project_journey(journey)
        with open(self.output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"✅ Exported {len(data['nodes'])} trajectory points to {self.output_path}")
