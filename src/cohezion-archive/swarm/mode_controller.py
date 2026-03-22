"""Stub for mode_controller — original module was removed.

Provides a no-op mode controller so the routing system can initialize.
"""

from __future__ import annotations

import logging
from enum import Enum


logger = logging.getLogger(__name__)


class SystemMode(Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class ModeController:
    """No-op system mode controller."""

    def __init__(self) -> None:
        self.mode = SystemMode.NORMAL

    def get_recommended_context(self, model: str) -> int:
        """Return default context window size."""
        return 32768

    def get_mode(self) -> SystemMode:
        return self.mode


_instance: ModeController | None = None


def get_mode_controller() -> ModeController:
    """Return a singleton mode controller."""
    global _instance
    if _instance is None:
        _instance = ModeController()
    return _instance
