"""Recursive-Trace — failure-class-informed strategy selection.

Conditions next candidate on TYPED failure-class of prior attempt,
distinguishing it from flat autoresearch which samples independently.

Reference: docs/research/RECURSIVE_TRACE_FALSIFIABLE_GATE_2026-06-05.md
Paper direction: arXiv 2605.30621 — harness non-monotonicity (Stage-2 gate).
"""

import contextlib


# Wiring-sweep 2026-06-22: core was a genuine import-graph orphan (no __init__.py at all).
# Creating this package marker makes recursive_trace statically reachable and wires its
# Stage-1 gate classes (RecursiveTraceLoop, TraceTask, TraceMemory) to the public surface.
with contextlib.suppress(Exception):
    from cohezion.flume.loop_goal_refactor_engine import (
        AutonomousGoalExecutor as AutonomousGoalExecutor,
    )
    from cohezion.flume.loop_goal_refactor_engine import (
        GoalSpecification as GoalSpecification,
    )
    from cohezion.flume.loop_goal_refactor_engine import (
        TraceGoalRefactorPipeline as TraceGoalRefactorPipeline,
    )
    from cohezion.flume.loop_goal_refactor_engine import (
        TraceToLoopTransformer as TraceToLoopTransformer,
    )
    from cohezion.recursive_trace.core import (
        LatentStateTracker as LatentStateTracker,
    )
    from cohezion.recursive_trace.core import (
        RecursiveTraceLoop as RecursiveTraceLoop,
    )
    from cohezion.recursive_trace.core import (
        RecursiveTraceResult as RecursiveTraceResult,
    )
    from cohezion.recursive_trace.core import (
        TraceMemory as TraceMemory,
    )
    from cohezion.recursive_trace.core import (
        TraceTask as TraceTask,
    )
    from cohezion.recursive_trace.goal_loop import (
        GoalDrivenTraceLoop as GoalDrivenTraceLoop,
    )
    from cohezion.recursive_trace.goal_loop import (
        GoalTraceResult as GoalTraceResult,
    )
    from cohezion.recursive_trace.goal_loop import (
        GoalTraceTask as GoalTraceTask,
    )
    from cohezion.recursive_trace.resolution_log import (
        record_resolution as record_resolution,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        BleedingEdgeResearchResult as BleedingEdgeResearchResult,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        CodebaseSweepResult as CodebaseSweepResult,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        ExperientialLearningResult as ExperientialLearningResult,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        TripartiteGoalLoop as TripartiteGoalLoop,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        TripartiteGoalLoopResult as TripartiteGoalLoopResult,
    )
    from cohezion.recursive_trace.tripartite_goal_loop import (
        TripartiteIterationResult as TripartiteIterationResult,
    )
