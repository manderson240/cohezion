"""Autonomous loop subsystem for Cohezion compound engineering."""

import contextlib

# coordinator is already wired as plain imports below; kept as suppress for uniformity
with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.coordinator import (
        LoopConfig as LoopConfig,
        LoopCoordinator as LoopCoordinator,
        LoopTask as LoopTask,
        RunReport as RunReport,
        SprintResult as SprintResult,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.executor import (
        ImprovementExecutor as ImprovementExecutor,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.local_executor import (
        LocalImprovementExecutor as LocalImprovementExecutor,
        LoopTickSweeper as LoopTickSweeper,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.quality_tracker import (
        MarkovQualityTracker as MarkovQualityTracker,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        ChallengerAgent as ChallengerAgent,
        EpisodeResult as EpisodeResult,
        RZeroChallengerExecutor as RZeroChallengerExecutor,
        SolverAgent as SolverAgent,
        TaskAttempt as TaskAttempt,
    )
