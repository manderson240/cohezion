# Swarm Agents Package
"""
Agent implementations for the SLM Swarm.

- AnalystAgent: Feature extraction with configurable perspectives
- CriticAgent: Logic verification and contradiction detection
- SynthesizerAgent: Aggregation and final response generation
"""

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.critic import CriticAgent
from cohezion.swarm.agents.synthesizer import SynthesizerAgent
from cohezion.swarm.agents.base import BaseAgent

__all__ = ["AnalystAgent", "CriticAgent", "SynthesizerAgent", "BaseAgent"]
