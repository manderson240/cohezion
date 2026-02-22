"""Trigger.dev integration for Cohezion background processes.

Provides a Python client for the Trigger.dev REST API and defines
background task entry points for:

- Research Lab: model scouting, paper ingestion, experiment analysis
- Universe Simulations: training pipelines, FLUME VAE, RL policy training
- Project Health: test suites, repo hygiene, security audits, metrics
- Compound Engineering: skill refinement, retrospection loops
"""

from __future__ import annotations

from cohezion.triggers.client import TriggerClient
from cohezion.triggers.config import TriggerConfig

__all__ = ["TriggerClient", "TriggerConfig"]
