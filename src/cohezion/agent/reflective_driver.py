"""ReflectiveDriver — the keystone that makes the compound self-improvement loop LIVE.

Three components were built and tested this session but never joined by a live caller:
  * WRITE  — ``adapt_skill`` records fault-guards into a ``GroundTruthHierarchy`` (rejected guards
             are recorded then contradicted, so they decay rather than surface).
  * BOUND  — ``run_with_reflection`` enforces a persisted re-dispatch (livelock) bound via a
             ``ReDispatchLedger`` that must outlive the stateless worker.
  * READ   — ``UnifiedAgent(guidance=H)`` injects trust-ranked guards back into its planning prompt.

The loop only runs end to end when ONE ``GroundTruthHierarchy`` is shared between the read side
(``agent.guidance``) and the write side (``run_with_reflection(trust=...)``), and ONE
``ReDispatchLedger`` is owned by the orchestrator (not the worker) so the bound survives across
tasks. ``ReflectiveDriver`` is exactly that join — it owns ``self.guidance`` and ``self.ledger`` and
guarantees both identities. Nothing else in the codebase does this, which is why the loop was latent.

It is a thin, additive composition: it does not modify ``UnifiedAgent``, ``run_with_reflection``,
``reflect``, ``adapt_skill``, or ``GroundTruthHierarchy``. It only wires them together.

Durability (the compound payoff): ``self.guidance`` and ``self.ledger`` are public and round-trip
losslessly — ``GroundTruthHierarchy.to_dict/from_dict`` (tier + full Beta posterior survive) and
``ReDispatchLedger.to_dict/from_dict`` — so the loop's accumulated learning and its livelock bounds
can be persisted across process restarts and rehydrated into a new driver.

Concurrency: a single driver holds ONE ledger, so concurrent ``run`` calls on the same driver share
it and are subject to ``run_with_reflection``'s single-flight caveat (a check-then-dispatch TOCTOU
that can exceed the cap). For concurrent task batches, use one driver per batch (separate ledgers).

Honest scope: a ``retry`` re-runs the SAME task (correct for transient faults; thin for
divergence/resource until guard text feeds planning beyond the trust-ranked block). Guards are
injected as *advisory* (tier-gated in ``inject_context``), never as inviolable ground truth, and the
trust score currently rises on recurrence (frequency, not efficacy) — see EXP-trust-efficacy.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from cohezion.agent.error_loop import ReDispatchLedger
from cohezion.agent.reflective_orchestrator import run_with_reflection
from cohezion.agent.unified_harness import UnifiedAgent
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy


logger = logging.getLogger(__name__)

__all__ = ["ReflectiveDriver"]


class ReflectiveDriver:
    """Run tasks through the full self-improvement loop with a shared hierarchy + owned ledger.

    Parameters
    ----------
    guidance:
        The shared ``GroundTruthHierarchy`` (created if not given). Wired into every worker the
        driver builds AND passed as ``trust=`` to ``run_with_reflection`` — the same object on both
        sides, which is what closes the loop.
    ledger:
        The driver-owned ``ReDispatchLedger`` (created if not given). Persists across ``run`` calls so
        the livelock bound holds across tasks, not just within one.
    max_redispatch:
        Default absolute re-dispatch cap per ``run`` (overridable per call).
    executor_factory:
        Optional ``() -> LLMExecutor`` for the worker's model; used by the default agent builder.
    agent_factory:
        Optional ``() -> worker`` full override (e.g. a stub in tests). When given, the driver does
        NOT force ``guidance`` onto it — the caller owns that wiring; the write side still uses the
        driver's shared hierarchy via ``trust=``.
    """

    def __init__(
        self,
        *,
        guidance: GroundTruthHierarchy | None = None,
        ledger: ReDispatchLedger | None = None,
        max_redispatch: int = 3,
        executor_factory: Callable[[], object] | None = None,
        agent_factory: Callable[[], object] | None = None,
    ) -> None:
        self.guidance = guidance if guidance is not None else GroundTruthHierarchy()
        self.ledger = ledger if ledger is not None else ReDispatchLedger()
        self.max_redispatch = max_redispatch
        self._executor_factory = executor_factory
        self._agent_factory = agent_factory

    def build_agent(self) -> object:
        """Build a fresh worker. The default builder wires the shared hierarchy as ``guidance=``.

        A fresh worker per call honours the stateless-worker model — the bound and the learning live
        on the driver (ledger + hierarchy), never on the worker.
        """
        if self._agent_factory is not None:
            agent = self._agent_factory()
            # Half-open-loop guard: the write side always targets self.guidance. If a custom factory's
            # worker reads a DIFFERENT (or no) hierarchy, guards accumulate but are never read back —
            # a silent half-open loop. Make it loud rather than letting the read side die quietly.
            if getattr(agent, "guidance", None) is not self.guidance:
                logger.warning(
                    "agent_factory worker does not share the driver's guidance hierarchy; the READ "
                    "half of the loop is detached (writes accumulate via trust=, reads see nothing)"
                )
            return agent
        executor = self._executor_factory() if self._executor_factory is not None else None
        return UnifiedAgent(executor=executor, guidance=self.guidance)

    async def run(
        self,
        task: object,
        *,
        env: dict | None = None,
        timeout: int = 1800,
        max_redispatch: int | None = None,
        prior_signature: str | None = None,
    ) -> dict:
        """Run one task through the loop: build a worker, dispatch + reflect, bounded re-dispatch.

        The same ``self.guidance`` is the worker's read source AND the ``trust=`` write target; the
        same ``self.ledger`` bounds re-dispatch across this and every other ``run``.
        """
        agent = self.build_agent()
        return await run_with_reflection(
            agent,
            task,
            ledger=self.ledger,
            trust=self.guidance,
            env=env,
            timeout=timeout,
            max_redispatch=self.max_redispatch if max_redispatch is None else max_redispatch,
            prior_signature=prior_signature,
        )
