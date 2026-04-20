"""Registry package initializer.

Exports the primary registry APIs so that callers can simply:

    from cohezion.registry import load_registry, register_skill, search_skills
    from cohezion.registry import CapabilityRegistry
"""

from .capability_registry import Capability, CapabilityRegistry
from .skill_registry import auto_sync, load_registry, register_skill, search_skills


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "auto_sync",
    "load_registry",
    "register_skill",
    "search_skills",
]
