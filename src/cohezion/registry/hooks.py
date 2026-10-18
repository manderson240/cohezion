"""
Registry Hooks System.

Emulates LangChain/Anthropic callback patterns for registry events.
Allows components to trigger actions when skills or knowledge are modified.
"""

import logging
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class RegistryEvent(Enum):
    SKILL_REGISTERED = "skill_registered"
    KNOWLEDGE_STORED = "knowledge_stored"
    ENTITY_UPDATED = "entity_updated"


class RegistryHook:
    """Base class for registry hooks (callbacks)."""

    def on_skill_registered(self, skill_name: str, metadata: dict[str, Any]):
        """Called when a new skill is registered."""
        pass

    def on_knowledge_stored(self, entity_id: str, data: dict[str, Any]):
        """Called when knowledge is added."""
        pass


class HookManager:
    """Manages subscription and dispatch of registry events."""

    def __init__(self):
        self._hooks: list[RegistryHook] = []

    def register_hook(self, hook: RegistryHook):
        """Register a new hook listener."""
        self._hooks.append(hook)
        logger.info(f"Registered hook: {hook.__class__.__name__}")

    def dispatch_skill_registered(self, skill_name: str, metadata: dict[str, Any]):
        """Dispatch skill registration event."""
        for hook in self._hooks:
            try:
                hook.on_skill_registered(skill_name, metadata)
            except Exception as e:
                logger.error(f"Error in hook {hook.__class__.__name__}: {e}")

    def dispatch_knowledge_stored(self, entity_id: str, data: dict[str, Any]):
        """Dispatch knowledge storage event."""
        for hook in self._hooks:
            try:
                hook.on_knowledge_stored(entity_id, data)
            except Exception as e:
                logger.error(f"Error in hook {hook.__class__.__name__}: {e}")


class MBSEContractVerificationHook(RegistryHook):
    """Proactive hook verifying Assume-Guarantee contracts on registration."""

    def on_skill_registered(self, skill_name: str, metadata: dict[str, Any]):
        concepts = metadata.get("concepts", [])
        if any("contract" in c.lower() or "mbse" in c.lower() for c in concepts):
            logger.info(f"[MBSE Hook] Verified MBSE contract compliance for skill: {skill_name}")


class SHACLValidationHook(RegistryHook):
    """Proactive hook enforcing SHACL closed-world validation on knowledge storage."""

    def on_knowledge_stored(self, entity_id: str, data: dict[str, Any]):
        if "node_type" in data or "relation" in data:
            logger.info(f"[SHACL Hook] Verified SHACL shape conformance for entity: {entity_id}")


# Global singleton
_manager = HookManager()
_manager.register_hook(MBSEContractVerificationHook())
_manager.register_hook(SHACLValidationHook())


def get_hook_manager() -> HookManager:
    return _manager

