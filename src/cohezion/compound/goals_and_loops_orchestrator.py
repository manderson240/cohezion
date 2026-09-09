"""Goals and Loops Orchestrator for Cohezion Autonomous Compound Delivery.

Refactors agentic execution into formal:
1. **Goals** (`GoalDefinition`, `GoalStore`): Structured objectives with deterministic Acceptance Criteria (ACs).
2. **Loops** (`ExecutionLoop`, `LoopCycle`): Formalized staged delivery loops (`team-plan` -> `team-exec` -> `team-verify` -> `team-fix`).
3. **Checkpoints & Taskboards**: State persistence synchronized across Local Filesystem, SurrealDB, and Obsidian Vault.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import inspect
import json
import logging
import os
import time
from typing import Any, Callable, Coroutine

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.contracts import VerificationResult

logger = logging.getLogger(__name__)


class GoalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    VERIFYING = "verifying"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    FAILED = "failed"


class LoopStage(str, Enum):
    PLAN = "team-plan"
    PRD = "team-prd"
    TASKBOARD = "taskboard"
    EXEC = "team-exec"
    VERIFY = "team-verify"
    FIX = "team-fix"


@dataclass
class AcceptanceCriterion:
    """Deterministic acceptance criterion required to satisfy a goal."""

    id: str
    description: str
    verifier_fn: Callable[[], bool | Coroutine[Any, Any, bool]] | None = None
    verified: bool = False
    evidence: str = ""

    async def execute_verification(self) -> bool:
        """Dynamically evaluate sync or async verifier callable."""
        if self.verifier_fn is None:
            return self.verified
        try:
            if inspect.iscoroutinefunction(self.verifier_fn):
                self.verified = await self.verifier_fn()
            else:
                res = self.verifier_fn()
                if inspect.isawaitable(res):
                    self.verified = await res
                else:
                    self.verified = bool(res)
        except Exception as exc:
            self.verified = False
            self.evidence = f"Verification error: {exc}"
        return self.verified


@dataclass
class Goal:
    """Durable autonomous goal with structured acceptance criteria."""

    id: str
    title: str
    objective: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_converged(self) -> bool:
        """Returns True if all acceptance criteria are verified (or vacuously True if none defined)."""
        if len(self.acceptance_criteria) == 0:
            return True
        return all(ac.verified for ac in self.acceptance_criteria)


@dataclass
class LoopCycleResult:
    """Result of an individual execution-verify-fix loop cycle."""

    cycle_index: int
    stage: LoopStage
    success: bool
    evidence: str
    duration_ms: float
    remaining_tasks: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


class ExecutionLoop:
    """Staged autonomous execution-verify-fix loop."""

    def __init__(
        self,
        goal: Goal,
        max_cycles: int = 5,
        verifier: AutoHarnessVerifier | None = None,
    ) -> None:
        self.goal = goal
        self.max_cycles = max_cycles
        self.verifier = verifier or AutoHarnessVerifier()
        self.cycle_history: list[LoopCycleResult] = []

    async def execute_cycle(
        self,
        cycle_idx: int,
        exec_fn: Callable[[], Coroutine[Any, Any, Any]],
        verify_fn: Callable[[], Coroutine[Any, Any, tuple[bool, str]]],
        fix_fn: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
    ) -> LoopCycleResult:
        """Run a single atomic [team-exec -> team-verify -> team-fix] cycle."""
        t0 = time.perf_counter()
        logger.info("Starting Loop Cycle %d/%d for Goal '%s'", cycle_idx, self.max_cycles, self.goal.id)

        # 1. Team-Exec
        try:
            await exec_fn()
        except Exception as exc:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return LoopCycleResult(
                cycle_index=cycle_idx,
                stage=LoopStage.EXEC,
                success=False,
                evidence=f"Execution error: {exc}",
                duration_ms=dt_ms,
                blockers=[str(exc)],
            )

        # 2. Team-Verify
        try:
            passed, verify_evidence = await verify_fn()
        except Exception as exc:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return LoopCycleResult(
                cycle_index=cycle_idx,
                stage=LoopStage.VERIFY,
                success=False,
                evidence=f"Verification probe error: {exc}",
                duration_ms=dt_ms,
                blockers=[str(exc)],
            )

        # 3. Team-Fix (if verify failed)
        if not passed and fix_fn is not None:
            logger.warning("Verification failed in cycle %d: %s. Invoking team-fix...", cycle_idx, verify_evidence)
            try:
                await fix_fn(verify_evidence)
                # Re-verify after fix
                passed, verify_evidence = await verify_fn()
            except Exception as fix_exc:
                verify_evidence += f" | Fix failed: {fix_exc}"

        dt_ms = (time.perf_counter() - t0) * 1000.0
        result = LoopCycleResult(
            cycle_index=cycle_idx,
            stage=LoopStage.VERIFY if passed else LoopStage.FIX,
            success=passed,
            evidence=verify_evidence,
            duration_ms=dt_ms,
        )
        self.cycle_history.append(result)
        return result

    async def run(
        self,
        exec_fn: Callable[[], Coroutine[Any, Any, Any]],
        verify_fn: Callable[[], Coroutine[Any, Any, tuple[bool, str]]],
        fix_fn: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
    ) -> bool:
        """Run the complete loop until the goal is satisfied or max cycles are reached."""
        self.goal.status = GoalStatus.ACTIVE

        for cycle_idx in range(1, self.max_cycles + 1):
            cycle_res = await self.execute_cycle(cycle_idx, exec_fn, verify_fn, fix_fn)
            if cycle_res.success:
                logger.info("Goal '%s' converged successfully in cycle %d!", self.goal.id, cycle_idx)
                self.goal.status = GoalStatus.SATISFIED
                self.goal.completed_at = time.time()
                return True

        logger.warning("Goal '%s' exhausted max cycles (%d) without full convergence.", self.goal.id, self.max_cycles)
        self.goal.status = GoalStatus.BLOCKED
        return False


class GoalsAndLoopsOrchestrator:
    """Master Orchestrator managing durable Goals, Execution Loops, and Taskboards."""

    def __init__(self) -> None:
        self.goals: dict[str, Goal] = {}
        self.active_loops: dict[str, ExecutionLoop] = {}

    def create_goal(
        self,
        goal_id: str,
        title: str,
        objective: str,
        criteria: list[tuple[str, str]],
    ) -> Goal:
        """Create and register a new structured Goal with Acceptance Criteria."""
        acs = [AcceptanceCriterion(id=cid, description=cdesc) for cid, cdesc in criteria]
        goal = Goal(id=goal_id, title=title, objective=objective, acceptance_criteria=acs)
        self.goals[goal_id] = goal
        return goal

    def create_loop(self, goal_id: str, max_cycles: int = 5) -> ExecutionLoop:
        """Instantiate an execution loop for a specific goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            raise KeyError(f"Goal '{goal_id}' does not exist.")
        loop = ExecutionLoop(goal=goal, max_cycles=max_cycles)
        self.active_loops[goal_id] = loop
        return loop

    def render_summary(self) -> str:
        """Generate a GitHub markdown status summary of all Goals and Loops."""
        lines = [
            "# 🎯 Cohezion Goals & Loops Status Board",
            "",
            "| Goal ID | Title | Status | Criteria Met | Progress |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for gid, g in self.goals.items():
            met = sum(1 for ac in g.acceptance_criteria if ac.verified)
            total = max(len(g.acceptance_criteria), 1)
            pct = (met / total) * 100.0
            status_badge = "🟢 SATISFIED" if g.status == GoalStatus.SATISFIED else f"🟡 {g.status.value.upper()}"
            lines.append(f"| `{g.id}` | {g.title} | {status_badge} | {met}/{total} | {pct:.1f}% |")

        lines.append("")
        return "\n".join(lines)
