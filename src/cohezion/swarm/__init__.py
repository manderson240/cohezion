# Cohezion Swarm Package
"""
SLM Swarm - A coordinated hierarchy of Small Language Models.

The swarm consists of:
- Analyst agents (Gemma) - Feature extraction with multiple perspectives
- Critic agent (Phi-3) - Logic verification and contradiction detection  
- Synthesizer agent (Mistral) - Aggregation and final response
"""

from cohezion.swarm.swarm_types import ThoughtVector, CritiqueResult, SynthesizedResponse

__all__ = ["ThoughtVector", "CritiqueResult", "SynthesizedResponse"]
