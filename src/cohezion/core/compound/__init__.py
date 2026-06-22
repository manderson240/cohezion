"""Compound logic engine for task compounding and pattern reuse."""

import contextlib

from cohezion.core.compound.retrospection import RetrospectionEngine
from cohezion.core.compound.skill_refiner import SkillRefiner


__all__ = [
    "CompoundLogicEngine",
    "LearningPattern",
    "RefinementResult",
    "RetrospectionEngine",
    "SkillRefiner",
]

# Wiring-sweep 2026-06-22: engine was an import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.core.compound.engine import (
        CompoundLogicEngine as CompoundLogicEngine,
    )

with contextlib.suppress(Exception):
    from cohezion.core.compound.retrospection import (
        LearningPattern as LearningPattern,
    )

with contextlib.suppress(Exception):
    from cohezion.core.compound.skill_refiner import (
        RefinementResult as RefinementResult,
    )
