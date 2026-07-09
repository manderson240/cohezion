"""Autonomous loop subsystem for Cohezion compound engineering."""

import contextlib


# coordinator is already wired as plain imports below; kept as suppress for uniformity
with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.coordinator import (
        LoopConfig as LoopConfig,
    )
    from cohezion.compound.autonomous_loop.coordinator import (
        LoopCoordinator as LoopCoordinator,
    )
    from cohezion.compound.autonomous_loop.coordinator import (
        LoopTask as LoopTask,
    )
    from cohezion.compound.autonomous_loop.coordinator import (
        RunReport as RunReport,
    )
    from cohezion.compound.autonomous_loop.coordinator import (
        SprintResult as SprintResult,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.executor import (
        ImprovementExecutor as ImprovementExecutor,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.local_executor import (
        LocalImprovementExecutor as LocalImprovementExecutor,
    )
    from cohezion.compound.autonomous_loop.local_executor import (
        LoopTickSweeper as LoopTickSweeper,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.quality_tracker import (
        MarkovQualityTracker as MarkovQualityTracker,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        ChallengerAgent as ChallengerAgent,
    )
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        EpisodeResult as EpisodeResult,
    )
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        RZeroChallengerExecutor as RZeroChallengerExecutor,
    )
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        SolverAgent as SolverAgent,
    )
    from cohezion.compound.autonomous_loop.rzero_challenger import (
        TaskAttempt as TaskAttempt,
    )
