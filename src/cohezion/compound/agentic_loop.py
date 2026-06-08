"""Agent-governed loop tick — makes the compound loop agentic.

Brackets the improvement work between two existing agents, so the loop is governed
by agents rather than a fixed script:

  - **Chronos** (``compound.chronos``): the resource-aware gate. Under CRITICAL
    memory pressure it advises deferring background compute, so the tick HOLDS heavy
    work — the loop-level counterpart to the per-command OOM gate (2026-06-07).
  - **Vault Keeper** (``agents.specialists.vault_keeper``): the specialist that OWNS
    the vault knowledge/health capability. The tick routes the knowledge step to it
    via the A2A specialist registry (its card declares ``report.vault.health``) —
    genuine capability routing, NOT a fabricated method (``PlatformSpecialist`` s are
    declarative and have no callable ``report_health``; inventing one would be the
    "fabricated consumer" the anti-gaming doctrine forbids).

Report-first + fully observable: every governance signal lands on :class:`TickResult`,
and the agents only ADVISE / OWN — nothing is auto-mutated. Human-in-the-loop by design.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cohezion.agents.specialists import vault_keeper as _vk  # noqa: F401  (force-register)
from cohezion.agents.specialists._base import describe_all
from cohezion.compound.chronos import get_chronos


_KNOWLEDGE_CAPABILITY = "report.vault.health"


def route_capability(capability: str) -> str | None:
    """Name of the specialist that OWNS a given capability (A2A routing).

    Generalizes the loop across ALL registered specialists: any capability resolves to
    its owning specialist card from the live registry (not hardcoded). This is the
    keystone for extending the loop to every specialist — pass the capability the work
    needs and the tick routes the knowledge step to its owner (vault-keeper for vault
    health, surreal-dba for schema, mcp-specialist for MCP health, …).
    """
    for spec in describe_all():
        if capability in spec.get("capabilities", ()):
            return spec.get("name")
    return None


def _knowledge_owner(capability: str = _KNOWLEDGE_CAPABILITY) -> str | None:
    """Owner of the loop's knowledge capability (defaults to vault health)."""
    return route_capability(capability)


@dataclass
class TickResult:
    """Fully observable outcome of one agent-governed loop iteration (HITL visibility)."""

    ran: bool
    deferred_reason: str | None = None
    deferred_jobs: list[str] = field(default_factory=list)
    knowledge_owner: str | None = None
    vault_health: dict[str, Any] | None = None
    context_count: int = 0
    work_summary: Any = None


def agentic_tick(
    *,
    improvement_fn: Callable[[list], Any],
    chronos: Any = None,
    level: Any = None,
    capability: str = _KNOWLEDGE_CAPABILITY,
    vault_health_fn: Callable[[], dict] | None = None,
    context_fn: Callable[[], list] | None = None,
) -> TickResult:
    """Run one agent-governed iteration of the compound loop.

    Chronos gates whether to run (resource-aware); Vault Keeper owns the knowledge
    step; ``improvement_fn(context)`` runs between them ONLY when there is headroom.

    Parameters
    ----------
    improvement_fn:
        The unit of loop work (e.g. next backlog item / audit). Called with the
        pulled context list, only when not deferred.
    chronos:
        A ChronosRegistry (default :func:`get_chronos`). Injectable for tests.
    level:
        Pressure level forwarded to ``resource_advisory``; ``None`` reads the live
        memory-pressure monitor.
    vault_health_fn / context_fn:
        Optional injectables for the knowledge step (health readout + context pull).
    """
    chronos = chronos or get_chronos()
    advised = chronos.resource_advisory(level=level)
    if advised:
        # CRITICAL pressure — hold heavy work; improvement_fn is NOT called.
        return TickResult(
            ran=False,
            deferred_reason="chronos: CRITICAL memory pressure — deferring loop work",
            deferred_jobs=[getattr(j, "name", str(j)) for j in advised],
            knowledge_owner=_knowledge_owner(capability),
        )

    owner = _knowledge_owner(capability)
    health = vault_health_fn() if vault_health_fn else None
    context = context_fn() if context_fn else []
    work = improvement_fn(context)
    return TickResult(
        ran=True,
        deferred_jobs=[],
        knowledge_owner=owner,
        vault_health=health,
        context_count=len(context),
        work_summary=work,
    )
