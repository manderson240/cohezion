"""Autonomous research module for training optimization.

Elegant integration of karpathy/autoresearch patterns into Cohezion.
"""

from __future__ import annotations

from cohezion.research.agent import ResearchAgent, ResearchSession
from cohezion.research.config import ExperimentResult, ResearchConfig

__all__ = [
    "ResearchAgent",
    "ResearchConfig",
    "ResearchSession",
    "ExperimentResult",
]

__version__ = "0.1.0"
