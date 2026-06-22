"""Swarm agent implementations: scouts, code review, and ARC-AGI wrappers."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.base_scout import ASTSummary as ASTSummary
    from cohezion.swarm.agents.base_scout import BaseScout as BaseScout
    from cohezion.swarm.agents.base_scout import Finding as Finding

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.anti_pattern_scout import (
        AntiPatternScout as AntiPatternScout,
    )

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.pattern_scout import PatternScout as PatternScout

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.architecture_scout import (
        ArchitectureScout as ArchitectureScout,
    )

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.quality_scout import QualityScout as QualityScout

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.eigent_agent import EigentAgent as EigentAgent

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.code_review_swarm import (
        CodeReviewSwarm as CodeReviewSwarm,
    )
    from cohezion.swarm.agents.code_review_swarm import SwarmReport as SwarmReport

with contextlib.suppress(Exception):
    from cohezion.swarm.agents.arc_agi_3_wrapper import ARCAGI3Env as ARCAGI3Env
    from cohezion.swarm.agents.arc_agi_3_wrapper import (
        RecursiveChainOfThought as RecursiveChainOfThought,
    )
