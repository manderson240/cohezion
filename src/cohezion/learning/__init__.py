"""Skill learning: pattern detection and template-driven code generation.

Provides :class:`SkillGenerator` which delegates to
:class:`~cohezion.core.template_engine.TemplateEngine` for parsing PRIME
skill definitions and generating agent stubs / config classes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.core.template_engine import TemplateEngine


logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    name: str = ""
    description: str = ""
    example: str = ""
    tags: list[str] = field(default_factory=list)
    occurrences: int = 1


class PatternDetector:
    """Pattern detector that tracks occurrences and enables compound analysis."""

    def __init__(self) -> None:
        self._patterns: dict[str, Pattern] = {}

    def record(
        self,
        name: str,
        description: str,
        example: str,
        tags: list[str] | None = None,
    ) -> Pattern:
        """Record a pattern occurrence, incrementing count if already seen."""
        if name in self._patterns:
            self._patterns[name].occurrences += 1
            logger.debug(
                "Pattern '%s' seen %d times",
                name,
                self._patterns[name].occurrences,
            )
            return self._patterns[name]

        pattern = Pattern(
            name=name,
            description=description,
            example=example,
            tags=tags or [],
            occurrences=1,
        )
        self._patterns[name] = pattern
        return pattern

    def get_patterns(self) -> list[Pattern]:
        """Return all recorded patterns sorted by occurrence count."""
        return sorted(
            self._patterns.values(),
            key=lambda p: p.occurrences,
            reverse=True,
        )

    def get_frequent(self, min_occurrences: int = 3) -> list[Pattern]:
        """Return patterns seen at least *min_occurrences* times."""
        return [p for p in self.get_patterns() if p.occurrences >= min_occurrences]

    def clear(self) -> None:
        """Reset all recorded patterns."""
        self._patterns.clear()


class SkillGenerator:
    """Generate agent components from PRIME skill definitions.

    Lazily initialises a :class:`~cohezion.core.template_engine.TemplateEngine`
    to parse skill markdown files and produce Python source code.
    """

    def __init__(self) -> None:
        self.detector = PatternDetector()
        self._engine: TemplateEngine | None = None

    @property
    def engine(self) -> TemplateEngine:
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


# Wiring-sweep 2026-06-22: vault_neuron_reader.py was a genuine import-graph orphan.
import contextlib

with contextlib.suppress(Exception):
    from cohezion.learning.vault_neuron_reader import (
        VaultNeuronWriter as VaultNeuronWriter,
    )

# Wiring-sweep 2026-06-22: mycelium_registry and mycelium_network were genuine orphans.
with contextlib.suppress(Exception):
    from cohezion.learning.mycelium_registry import (
        MyceliumRegistry as MyceliumRegistry,
    )
    from cohezion.learning.mycelium_registry import (
        SynthesizedSkill as SynthesizedSkill,
    )

with contextlib.suppress(Exception):
    from cohezion.learning.mycelium_network import (
        MyceliumNetwork as MyceliumNetwork,
    )

# Wiring-sweep 2026-06-22: ouroboros.py (learning layer), shadow_scripter, skill_acquisition
with contextlib.suppress(Exception):
    from cohezion.learning.ouroboros import (
        ExecutionExhaust as ExecutionExhaust,
    )
    from cohezion.learning.ouroboros import (
        OuroborosAttribution as OuroborosAttribution,
    )
    from cohezion.learning.ouroboros import (
        OuroborosEngine as OuroborosEngine,
    )

with contextlib.suppress(Exception):
    from cohezion.learning.shadow_scripter import (
        ShadowScripter as ShadowScripter,
    )

with contextlib.suppress(Exception):
    from cohezion.learning.skill_acquisition import (
        DynamicSkillAcquisition as DynamicSkillAcquisition,
    )


_instance: SkillGenerator | None = None


def get_skill_generator() -> SkillGenerator:
    """Return a singleton skill generator."""
    global _instance
    if _instance is None:
        _instance = SkillGenerator()
    return _instance


# Wiring-sweep 2026-06-22: deep_research and ouroboros_trigger were genuine import-graph orphans.
import contextlib as _contextlib

with _contextlib.suppress(Exception):
    from cohezion.learning.deep_research import (
        DeepResearchPipeline as DeepResearchPipeline,
    )

with _contextlib.suppress(Exception):
    from cohezion.learning.ouroboros_trigger import (
        OuroborosTrigger as OuroborosTrigger,
    )
    from cohezion.learning.ouroboros_trigger import (
        TriggerState as TriggerState,
    )
