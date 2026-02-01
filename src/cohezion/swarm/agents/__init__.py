# Swarm Agents Package
"""
Agent implementations for the SLM Swarm.

- AnalystAgent: Feature extraction with configurable perspectives
- CriticAgent: Logic verification and contradiction detection
- SynthesizerAgent: Aggregation and final response generation
"""

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.base import BaseAgent
from cohezion.swarm.agents.critic import CriticAgent
from cohezion.swarm.agents.nexus_research_agent import NexusResearchAgent
from cohezion.swarm.agents.reporter import InteractiveReportAgent
from cohezion.swarm.agents.synthesizer import SynthesizerAgent
from cohezion.swarm.agents.universe_sim_agent import UniverseSimulationAgent
from cohezion.swarm.agents.world_model_agent import WorldModelAgent
from cohezion.swarm.agents.x_scout_agent import XScoutAgent
from cohezion.swarm.agents.you_tube_transcript_agent import YouTubeTranscriptAgent

__all__ = [
    "AnalystAgent",
    "CriticAgent",
    "SynthesizerAgent",
    "NexusResearchAgent",
    "YouTubeTranscriptAgent",
    "XScoutAgent",
    "UniverseSimAgent",
    "WorldModelAgent",
    "BaseAgent",
    "CriticAgent",
    "InteractiveReportAgent",
]
