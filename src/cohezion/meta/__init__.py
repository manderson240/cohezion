"""Cohezion Meta-Programming System.

Enables creating agents and workflows from YAML specifications using Jinja2 templates.

Features:
- Agent generation from specs
- Workflow template rendering
- Universe tracking for generated code
- XP rewards for quality generation

Usage:
    from cohezion.meta.generator import MetaGenerator
    from cohezion.meta.evolution import EvolutionOrchestrator

    generator = MetaGenerator()
    await generator.generate_agent("specs/research_agent.yaml", "src/cohezion/agents/")
"""

from cohezion.meta.evolution import EvolutionOrchestrator
from cohezion.meta.generator import MetaGenerator

__all__ = ["MetaGenerator", "EvolutionOrchestrator"]
