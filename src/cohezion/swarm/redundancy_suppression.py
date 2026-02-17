"""Stub for RedundancyManager — original module was removed.

Provides a no-op redundancy manager so BaseAgent can initialize without errors.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class RedundancyManager:
    """No-op redundancy suppression manager."""

    def __init__(self, agent_name: str = "", window_size: int = 100):
        self.agent_name = agent_name
        self.window_size = window_size

    def check(self, task: str) -> tuple[int, str]:
        """Always returns level 0 (no suppression) with the original task."""
        return 0, task

    async def apply_suppression(self, level: int, task: str) -> None:
        pass
