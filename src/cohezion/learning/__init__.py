"""Skill learning: pattern detection and template-driven code generation.

Provides :class:`SkillGenerator` which delegates to
:class:`~cohezion.core.template_engine.TemplateEngine` for parsing PRIME
skill definitions and generating agent stubs / config classes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    name: str = ""
    description: str = ""
    example: str = ""
    tags: list[str] = field(default_factory=list)
    occurrences: int = 1


class PatternDetector:
    """No-op pattern detector."""

    def record(
        self,
        name: str,
        description: str,
        example: str,
        tags: list[str] | None = None,
    ) -> Pattern:
        return Pattern(
            name=name,
            description=description,
            example=example,
            tags=tags or [],
            occurrences=1,
        )


class SkillGenerator:
    """Generate agent components from PRIME skill definitions.

    Lazily initialises a :class:`~cohezion.core.template_engine.TemplateEngine`
    to parse skill markdown files and produce Python source code.
    """

    def __init__(self) -> None:
        self.detector = PatternDetector()
        self._engine: TemplateEngine | None = None  # noqa: F821

    @property
    def engine(self) -> TemplateEngine:  # noqa: F821
        """Lazily create the template engine."""
        if self._engine is None:
            from cohezion.core.template_engine import TemplateEngine

            self._engine = TemplateEngine()
        return self._engine

    def generate(self, skill_name: str) -> str:
        """Generate an agent stub for a named skill.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        str
            Python source code for the agent class.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")
        return self.engine.generate_agent_stub(spec)

    def generate_config(self, skill_name: str) -> str:
        """Generate a config dataclass for a named skill.

        Parameters
        ----------
        skill_name : str
            PRIME skill identifier (case-insensitive).

        Returns
        -------
        str
            Python source code for the config dataclass.

        Raises
        ------
        KeyError
            If the skill cannot be found.
        """
        spec = self.engine.get_spec_by_name(skill_name)
        if spec is None:
            raise KeyError(f"Skill not found: {skill_name}")
        return self.engine.generate_config_class(spec)


_instance: SkillGenerator | None = None


def get_skill_generator() -> SkillGenerator:
    """Return a singleton skill generator."""
    global _instance
    if _instance is None:
        _instance = SkillGenerator()
    return _instance
