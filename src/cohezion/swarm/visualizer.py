"""Journey Visualizer for the Quadrature Nexus.

Generates Mermaid-based trajectory plots and Markdown 'Showreels' 
representing agentic journeys.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.swarm.perception import PerceptionEvent

logger = logging.getLogger(__name__)


class JourneyVisualizer:
    """
    Generates high-fidelity visual representations of journeys.
    """

    def __init__(self, output_dir: str = "knowledge_graph/showreels"):
        self.output_dir = output_dir

    def generate_mermaid_trajectory(self, events: list[PerceptionEvent]) -> str:
        """
        Create a Mermaid graph representing the 12D trajectory flow.
        
        Since Mermaid can't do 12D, we project 2D (Coherence vs Efficiency)
        onto a sequence diagram or flowchart.
        """
        if not events:
            return "%% No events to visualize"
            
        mermaid = ["graph TD", "  %% Quadrature Nexus Journey Visualization"]
        
        # Link events in a sequence
        for i, event in enumerate(events):
            node_id = f"E{i}"
            # Clean description of Mermaid-breaking characters
            desc = event.description.replace('"', "'").replace("[", "(").replace("]", ")")
            label = f'"{desc[:40]}... Impact: {event.impact_score:.2f}"'
            
            # Use styling based on impact
            if event.impact_score >= 0.9:
                mermaid.append(f"  {node_id}[{label}]:::highImpact")
            else:
                mermaid.append(f"  {node_id}[{label}]")
                
            if i > 0:
                mermaid.append(f"  E{i-1} --> E{i}")
                
        mermaid.append("")
        mermaid.append("  classDef highImpact fill:#00FF00,stroke:#C0C0C0,stroke-width:2px,color:#0A0A0A")
        
        return "\n".join(mermaid)

    def generate_showreel_markdown(self, events: list[PerceptionEvent], analyzer_report: dict[str, Any]) -> str:
        """
        Generate a Markdown 'Showreel' artifact.
        """
        from cohezion.branding import Identity, get_nexus_sign_off
        
        showreel = [
            f"# AGENTIC SHOWREEL: {Identity.NAME}",
            f"\n> [!IMPORTANT]\n> Status: {analyzer_report.get('status', 'TRANSITIONING')}\n> Mean Impact: {analyzer_report.get('mean_impact', 0.0):.2f}\n",
            "## Journey Trajectory",
            "```mermaid",
            self.generate_mermaid_trajectory(events),
            "```",
            "\n## High-Impact Moments",
            "| Moment | Description | Truth Anchor (Git) | Impact Score |",
            "| :--- | :--- | :--- | :--- |"
        ]
        
        for i, event in enumerate(events):
            if event.impact_score >= 0.9:
                showreel.append(f"| {i+1} | {event.description} | `{event.git_hash[:7]}` | **{event.impact_score:.2f}** |")
                
        showreel.append(get_nexus_sign_off())
        
        return "\n".join(showreel)
