"""
Hook lifecycle events.

Attribution: Event model inspired by Pilot's lifecycle architecture
Implementation: Original COHEZION design using Pydantic and HIHO principles
"""

from __future__ import annotations

from enum import Enum


class HookEvent(str, Enum):
    """Lifecycle events that can trigger hooks.

    Inspired by Pilot's 6-event model, extended with COHEZION-specific events.
    """

    # Core lifecycle (from Pilot pattern)
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    CONTEXT_WARNING = "context_warning"
    CONTEXT_CLEAR = "context_clear"

    # COHEZION-specific extensions
    COHERENCE_DROP = "coherence_drop"  # HIHO stability violation
    JOURNEY_CHECKPOINT = "journey_checkpoint"  # 12D trajectory milestone
    SKILL_REFINEMENT = "skill_refinement"  # Compound learning trigger
    VAULT_SYNC = "vault_sync"  # Knowledge persistence
