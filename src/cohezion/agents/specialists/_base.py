"""Base types for Cohezion platform specialists.

Platform specialists are DISCOVERABILITY entities, not LLM-calling agents. They declare
scope, capabilities, and routing via A2A-compatible agent cards; the actual work happens
in the PRIME skill markdown files and domain modules they reference.

See ``_bmad-output/project-context.md`` §"Agent Teams & Coordination": specialists are
NOT running services with inboxes — treating them as such hangs sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class AgentCard:
    """A2A-compatible agent card describing a platform specialist.

    Fields follow Google A2A's agent-card schema (v0.9) at a pragmatic subset:
    name, description, capabilities, role. Cohezion adds principles and reference
    pointers so discovery lands on authoritative docs fast.
    """

    name: str
    display_name: str
    description: str
    role: str
    capabilities: tuple[str, ...]
    principles: tuple[str, ...]
    prime_skill_ref: str
    canonical_modules: tuple[str, ...] = ()


class PlatformSpecialist:
    """Lightweight base for platform specialists.

    Subclasses MUST define a class-level ``CARD`` attribute of type :class:`AgentCard`.
    They do NOT call LLMs — they declare identity, capabilities, and routing. All heavy
    domain work lives in the PRIME skill markdown and the canonical modules.
    """

    CARD: ClassVar[AgentCard]

    @classmethod
    def describe(cls) -> dict[str, Any]:
        """Return agent card as a plain dict (A2A discovery payload)."""
        c = cls.CARD
        return {
            "name": c.name,
            "display_name": c.display_name,
            "description": c.description,
            "role": c.role,
            "capabilities": list(c.capabilities),
            "principles": list(c.principles),
            "prime_skill_ref": c.prime_skill_ref,
            "canonical_modules": list(c.canonical_modules),
        }

    @classmethod
    def name(cls) -> str:
        return cls.CARD.name


_REGISTRY: dict[str, type[PlatformSpecialist]] = {}


def register(specialist_cls: type[PlatformSpecialist]) -> type[PlatformSpecialist]:
    """Class decorator to register a specialist in the global registry."""
    _REGISTRY[specialist_cls.CARD.name] = specialist_cls
    return specialist_cls


def get_specialist(name: str) -> type[PlatformSpecialist] | None:
    """Look up a specialist class by kebab-case name."""
    return _REGISTRY.get(name)


def list_specialists() -> list[str]:
    """Return all registered specialist names, sorted."""
    return sorted(_REGISTRY.keys())


def describe_all() -> list[dict[str, Any]]:
    """Return agent-card dicts for all registered specialists."""
    return [cls.describe() for cls in _REGISTRY.values()]
