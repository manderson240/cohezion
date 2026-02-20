"""
COHEZION Hooks System

Lifecycle event hooks for quality enforcement and context preservation.
Inspired by Pilot's hooks architecture but implemented from scratch using COHEZION patterns.

Attribution: Pattern inspired by Claude Pilot (github.com/maxritter/claude-pilot)
License: Original COHEZION implementation respecting Pilot's proprietary license
"""

from __future__ import annotations

from .events import HookEvent
from .executor import HookExecutor
from .registry import HookRegistry

__all__ = ["HookEvent", "HookExecutor", "HookRegistry"]
