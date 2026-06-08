"""swarm_tick — an agentic tick whose improvement work is a local-silicon SWARM.

Composes the three layers built this session into one governed unit:

  - **agentic_tick** (``compound.agentic_loop``): Chronos resource-gate + Vault Keeper
    knowledge ownership + a HITL-visible ``TickResult``.
  - **Cohezion swarm** (``swarm.team_orchestrator`` + ``swarm.execution_orchestrator``):
    ``plan_team(intent)`` decomposes the intent into a team of agents + dependency-tracked
    tasks; ``ExecutionOrchestrator.execute`` runs them CONCURRENTLY in waves.
  - **Local silicon**: the orchestrator's direct path uses ``PlanExecutor`` (0 cloud
    tokens) — $0.

The swarm is constructed and run INSIDE the Chronos gate: under CRITICAL memory pressure
the tick defers and the swarm is **never planned or executed**, so concurrent multi-agent
work cannot re-trigger the OOM that motivated this whole stack. This is "wiring as part of
the loop": pass a wiring INTENT and the swarm decomposes + executes it, governed and
observable. Owner agent of the knowledge step: ``surreal-dba``/``vault-keeper`` via the
agentic_tick A2A routing.
"""

from __future__ import annotations

import asyncio
from typing import Any

from cohezion.compound.agentic_loop import TickResult, agentic_tick


def swarm_tick(
    intent: str,
    *,
    chronos: Any = None,
    level: Any = None,
    orchestrator: Any = None,
    executor: Any = None,
    max_agents: int = 4,
) -> TickResult:
    """Plan + execute a swarm for ``intent`` on local silicon, Chronos-governed.

    Parameters
    ----------
    intent:
        The wiring/improvement goal the swarm should decompose and execute.
    chronos / level:
        Resource gate (defaults to the live Chronos + memory-pressure monitor).
    orchestrator / executor:
        Injectable swarm components (defaults: real ``TeamOrchestrator`` +
        ``ExecutionOrchestrator``). Lazy-imported so the governance core stays light
        and the swarm is only constructed when the gate actually allows a run.
    """

    def _swarm_work(_ctx) -> dict[str, Any]:
        orch = orchestrator
        if orch is None:
            from cohezion.swarm.team_orchestrator import TeamOrchestrator

            orch = TeamOrchestrator()
        ex = executor
        if ex is None:
            from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator

            ex = ExecutionOrchestrator(token_client=None)

        plan = orch.plan_team(intent, max_agents=max_agents)
        report = asyncio.run(ex.execute(plan))
        return {
            "intent": intent,
            "agents": len(plan.agents),
            "tasks": len(plan.tasks),
            "status": getattr(report, "status", "unknown"),
        }

    return agentic_tick(
        improvement_fn=_swarm_work, chronos=chronos, level=level, context_fn=lambda: []
    )
