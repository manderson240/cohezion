"""Skills sub-package for compound engineering."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.skills.selector import (
        SelectorFeedbackRefiner as SelectorFeedbackRefiner,
        SimpleSkills as SimpleSkills,
        SkillMatch as SkillMatch,
        SkillSelector as SkillSelector,
    )
