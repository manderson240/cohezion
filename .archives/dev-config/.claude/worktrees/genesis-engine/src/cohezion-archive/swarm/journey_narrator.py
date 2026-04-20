"""Stub for JourneyNarrator — original module was removed.

Provides a no-op narrator so BaseAgent can initialize without errors.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class JourneyNarrator:
    """No-op journey narrator."""

    def generate_narration(self, agent_name: str, prompt: str, result: str) -> str:
        return ""

    async def narrate(self, narration: str) -> None:
        pass
