# Swarm Agents Package
"""
Agent implementations for the SLM Swarm.

- AnalystAgent: Feature extraction with configurable perspectives
- CriticAgent: Logic verification and contradiction detection
- SynthesizerAgent: Aggregation and final response generation
"""

from cohezion.agents.analyst import AnalystAgent
from cohezion.agents.base import BaseAgent
from cohezion.agents.critic import CriticAgent
from cohezion.agents.nexus_research_agent import NexusResearchAgent
from cohezion.agents.reporter import InteractiveReportAgent
from cohezion.agents.synthesizer import SynthesizerAgent
from cohezion.agents.universe_sim_agent import UniverseSimulationAgent
from cohezion.agents.world_model_agent import WorldModelAgent
from cohezion.agents.x_scout_agent import XScoutAgent
from cohezion.agents.you_tube_transcript_agent import YouTubeTranscriptAgent

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
