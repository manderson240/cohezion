"""Learning recorder — bridge agent/executor telemetry into Ouroboros and Mycelium.

This module closes the recursive learning loop by recording every notable agent
execution and compound-task outcome as durable precipitation events.

Design choices
--------------
* ``LearningRecorder`` is intentionally thin. It does not implement the learning
  algorithm itself; it delegates to ``OuroborosEngine`` (failure-driven rewrite)
  and ``MyceliumRegistry`` (pattern-driven skill synthesis) and emits a
  ``PrecipitationEvent`` so other sinks (vault, SurrealDB, git ledger) persist it.
* All methods are sync-compatible and swallow exceptions so learning feedback can
  never break the execution path it observes.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cohezion.learning.mycelium_registry import JournalEntry, MyceliumRegistry
from cohezion.learning.ouroboros import ExecutionExhaust, OuroborosEngine
from cohezion.precipitation import PrecipitationEvent, PrecipitationKind, emit, zero_twelve_d


logger = logging.getLogger(__name__)


def _task_id(agent_name: str, suffix: str | None = None) -> str:
    return f"{agent_name}:{suffix or int(time.time() * 1000)}"


class LearningRecorder:
    """Records agent turns and executor outcomes for Ouroboros/Mycelium loops.

    Parameters
    ----------
    ouroboros_engine : OuroborosEngine | None
        Engine that consumes failure exhaust. Created lazily if omitted.
    mycelium_registry : MyceliumRegistry | None
        Registry that ingests journal entries. Created lazily if omitted.
    """

    def __init__(
        self,
        ouroboros_engine: OuroborosEngine | None = None,
        mycelium_registry: MyceliumRegistry | None = None,
    ) -> None:
        self._ouroboros = ouroboros_engine or OuroborosEngine()
        self._mycelium = mycelium_registry or MyceliumRegistry.get_instance()

    def record_agent_turn(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        *,
        model: str | None = None,
        lane: str | None = None,
        phi_score: float = 0.5,
        confidence: float = 0.5,
        coherence: float | None = None,
        latency_ms: float | None = None,
        escalated_to_cloud: bool = False,
        embedding: list[float] | None = None,
    ) -> None:
        """Persist a single agent turn as a WITNESS_MARK and Mycelium journal entry.

        This is the write-side of the BaseAgent learning loop. Every non-trivial
        turn becomes a precipitation event that downstream sinks can route to
        SurrealDB/vault/git, while a journal entry feeds the autonomous skill
        synthesizer.
        """
        try:
            effective_coherence = coherence if coherence is not None else max(0.0, min(1.0, phi_score))
            twelve_d = zero_twelve_d()
            twelve_d["novelty"] = confidence
            twelve_d["precipitation"] = effective_coherence
            twelve_d["control"] = 0.5 if escalated_to_cloud else 0.7

            payload = {
                "agent": agent_name,
                "prompt_preview": prompt[:500],
                "response_preview": response[:500],
                "model": model,
                "lane": lane,
                "phi_score": phi_score,
                "confidence": confidence,
                "latency_ms": latency_ms,
                "escalated_to_cloud": escalated_to_cloud,
                "embedding": embedding,
            }

            event = PrecipitationEvent(
                kind=PrecipitationKind.WITNESS_MARK,
                universe_id="compound",
                coherence=effective_coherence,
                twelve_d=twelve_d,
                agent_id=agent_name,
                payload=payload,
            )
            emit(event)

            # Also feed the autonomous skill synthesizer.
            self._mycelium.ingest_entry(
                JournalEntry(
                    entry_id=event.event_id,
                    content=f"{agent_name}: {prompt[:200]} -> {response[:200]}",
                    domain="decision",
                )
            )
        except Exception:
            logger.debug("LearningRecorder failed to record agent turn", exc_info=True)

    def record_executor_outcome(
        self,
        task_description: str,
        skill_name: str,
        success: bool,
        output: str,
        metrics: dict[str, Any],
        *,
        duration_seconds: float | None = None,
        project: str = "cohezion",
    ) -> None:
        """Persist a compound executor outcome and, on failure, feed Ouroboros.

        This is the write-side of the CompoundExecutor learning loop. Successful
        runs emit a WITNESS_MARK; failed runs additionally produce an
        ``ExecutionExhaust`` for the Ouroboros rewrite cycle.
        """
        try:
            coherence = float(metrics.get("coherence", 0.5))
            twelve_d = zero_twelve_d()
            twelve_d["control"] = 0.8 if success else 0.2
            twelve_d["novelty"] = 0.5
            twelve_d["precipitation"] = coherence

            payload = {
                "project": project,
                "skill_name": skill_name,
                "task_description": task_description[:500],
                "output_preview": output[:500],
                "success": success,
                "duration_seconds": duration_seconds,
                "metrics": {k: str(v) if not isinstance(v, (int, float, str, bool, list, dict)) else v for k, v in metrics.items()},
            }

            event = PrecipitationEvent(
                kind=PrecipitationKind.WITNESS_MARK,
                universe_id=project,
                coherence=coherence,
                twelve_d=twelve_d,
                payload=payload,
            )
            emit(event)

            self._mycelium.ingest_entry(
                JournalEntry(
                    entry_id=event.event_id,
                    content=f"{skill_name}: {task_description[:200]} -> success={success}",
                    domain="experiment" if success else "pattern",
                )
            )

            if not success:
                # Failure exhaust drives the Ouroboros self-improvement loop.
                exhaust = ExecutionExhaust(
                    task_id=_task_id(skill_name, task_description[:80]),
                    error_message=output[:1000],
                    coherence_drop=max(0.0, 1.0 - coherence),
                    token_usage=int(metrics.get("tokens_used", 0)),
                    diagnostics=dict(payload),
                )
                # OuroborosEngine.consume_exhaust is async; schedule it without blocking.
                import asyncio

                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(self._ouroboros.consume_exhaust(exhaust))
                else:
                    # Sync context: fire-and-forget via asyncio.run would be risky if
                    # a loop is already running in another thread; swallow instead.
                    try:
                        asyncio.run(self._ouroboros.consume_exhaust(exhaust))
                    except RuntimeError:
                        logger.debug("Could not run Ouroboros consume_exhaust: no event loop")
        except Exception:
            logger.debug("LearningRecorder failed to record executor outcome", exc_info=True)


# Module-level singleton accessor so callers do not need to manage lifecycle.
_recorder_instance: LearningRecorder | None = None


def get_learning_recorder() -> LearningRecorder:
    """Return the module-level ``LearningRecorder`` singleton."""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = LearningRecorder()
    return _recorder_instance


def reset_learning_recorder() -> None:
    """Reset the singleton (test isolation)."""
    global _recorder_instance
    _recorder_instance = None


__all__ = [
    "LearningRecorder",
    "get_learning_recorder",
    "reset_learning_recorder",
]
