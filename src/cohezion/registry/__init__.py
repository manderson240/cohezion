"""Registry package initializer.

Exports the primary skill‑registry API so that callers can simply:

    from cohezion.registry import load_registry, register_skill, search_skills
"""

from .skill_registry import load_registry, register_skill, search_skills

__all__ = [
    "load_registry",
    "register_skill",
    "search_skills",
]
