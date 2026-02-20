"""
Hook registry for managing and executing lifecycle hooks.

Attribution: Registry pattern inspired by Pilot's hook management
Implementation: Original COHEZION design with vault-backed persistence
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List

from .events import HookEvent

logger = logging.getLogger(__name__)


class HookRegistry:
    """Registry for managing lifecycle hooks.

    Maintains hook registration and ordering. Integrates with vault for
    persistent hook configuration across sessions.
    """

    def __init__(self) -> None:
        """Initialize empty hook registry."""
        self._hooks: Dict[HookEvent, List[Callable]] = defaultdict(list)
        self._blocking: Dict[str, bool] = {}  # hook_id -> is_blocking

    def register(
        self,
        event: HookEvent,
        hook_fn: Callable,
        hook_id: str,
        blocking: bool = False,
    ) -> None:
        """Register a hook for a lifecycle event.

        Args:
            event: The lifecycle event to hook into
            hook_fn: The function to execute when event fires
            hook_id: Unique identifier for this hook
            blocking: If True, hook must complete before proceeding
        """
        self._hooks[event].append(hook_fn)
        self._blocking[hook_id] = blocking
        logger.debug(f"Registered {hook_id} for {event} (blocking={blocking})")

    def unregister(self, event: HookEvent, hook_id: str) -> None:
        """Remove a hook from an event."""
        # Note: This simplified implementation doesn't track hook_id on the callable
        # In production, you'd want to wrap callables with metadata
        logger.warning(
            f"Hook unregister not fully implemented: {hook_id} for {event}"
        )

    def get_hooks(self, event: HookEvent) -> List[Callable]:
        """Get all registered hooks for an event."""
        return self._hooks.get(event, [])

    def is_blocking(self, hook_id: str) -> bool:
        """Check if a hook is blocking."""
        return self._blocking.get(hook_id, False)

    def list_hooks(self) -> Dict[HookEvent, int]:
        """List all registered hooks by event."""
        return {event: len(hooks) for event, hooks in self._hooks.items()}

    def save_to_vault(self, vault_path: Path) -> None:
        """Persist hook configuration to vault.

        This enables cross-session hook persistence and team sharing.
        """
        # TODO: Implement vault serialization
        logger.info(f"Hook vault persistence not yet implemented: {vault_path}")

    def load_from_vault(self, vault_path: Path) -> None:
        """Load hook configuration from vault."""
        # TODO: Implement vault deserialization
        logger.info(f"Hook vault loading not yet implemented: {vault_path}")
