r"""Goal-Driven Trace Loop — Unifying execution traces, recursive search, and durable goals.
========================================================================================

Architecture:
  1. Formalizes tasks as durable disk-backed goals via `cohezion.compound.goal_state`.
  2. Binds iterative failure-informed strategy selection (`RecursiveTraceLoop`).
  3. Uses monadic execution (`MonadResult`) for pure error isolation and typed failure capture.
  4. Records empirical resolution data to `resolution_log.jsonl` for statistical validation.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cohezion.compound.goal_state import observe, set_goal, status
from cohezion.flume.monadic_markov_trace_engine import MonadResult
from cohezion.recursive_trace.core import TraceMemory
from cohezion.recursive_trace.resolution_log import record_resolution


logger = logging.getLogger(__name__)


@dataclass
class GoalTraceTask:
    """A unit of work tracked as a durable goal with typed failure progression."""

    goal_id: str
    condition: str
    initial_failure_class: str = "initial"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalTraceResult:
    """Outcome of a GoalDrivenTraceLoop run."""

    solved: bool
    iterations: int
    path: list[str] = field(default_factory=list)
    last_observation: str = ""
    goal_status: dict[str, Any] = field(default_factory=dict)


StepReturn = tuple[bool | None, str, str | None]
"""(satisfied, observation_note, next_failure_class)"""


class GoalDrivenTraceLoop:
    """Iterative goal-directed loop conditioning candidate strategies on prior failure classes.

    Combines:
      - Durable atomic goal tracking (`set_goal`, `observe`, `status`)
      - Deduplicated failure-class-conditioned strategy progression
      - Monadic error containment (exceptions converted to typed failures)
      - Fail-soft resolution logging to `resolution_log.jsonl`
    """

    def __init__(
        self,
        strategies: Sequence[str],
        failure_map: Mapping[str, Sequence[str]],
        *,
        max_depth: int | None = None,
        domain: str = "goal_loop",
        source: str = "live",
        memory: TraceMemory | None = None,
        verifier: Callable[[GoalTraceTask, str], tuple[bool, str | None]] | None = None,
        persist_graph: bool = False,
        notify_operator: bool = False,
    ) -> None:
        self.strategies = list(strategies)
        self.failure_map = {k: list(v) for k, v in failure_map.items()}
        self.max_depth = max_depth if max_depth is not None else len(self.strategies)
        self.domain = domain
        self.source = source
        self.memory = memory or TraceMemory()
        self.verifier = verifier
        self.persist_graph = persist_graph
        self.notify_operator = notify_operator

    def _persist_graph_edge(
        self,
        goal_id: str,
        strategy: str,
        failure_class: str,
        satisfied: bool | None,
        iteration: int,
    ) -> None:
        """Persist directed graph edge to SurrealDB v2 (fail-soft)."""
        if not self.persist_graph:
            return
        import httpx

        try:
            rel = "RESOLVED_BY" if satisfied else "ATTEMPTED"
            clean_goal = "".join(c for c in goal_id if c.isalnum() or c in "_-")
            clean_strat = "".join(c for c in strategy if c.isalnum() or c in "_-")
            clean_fc = "".join(c for c in failure_class if c.isalnum() or c in "_-")
            sql = f"""
            USE NS cohezion DB main;
            LET $g = (UPSERT kg_node:goal_{clean_goal} SET label = '{clean_goal}', type = 'goal');
            LET $s = (UPSERT kg_node:strategy_{clean_strat} SET label = '{clean_strat}', type = 'strategy');
            RELATE $g->{rel}->$s SET failure_class = '{clean_fc}', satisfied = {str(bool(satisfied)).lower()}, iteration = {iteration}, timestamp = time::now();
            """
            from cohezion.storage.surreal_http import checked_statements

            resp = httpx.post(
                "http://127.0.0.1:8001/sql",
                headers={"Accept": "application/json"},
                auth=("root", "root"),
                content=sql,
                timeout=1.0,
            )
            checked_statements(resp.json(), status_code=resp.status_code, text=resp.text)
        except Exception as exc:
            logger.warning(
                "SurrealDB graph edge persistence failed (non-blocking): %s", str(exc)[:200]
            )

    def _notify_tg(self, text: str) -> None:
        """Send notification to operator via Telegram bot (fail-soft)."""
        if not self.notify_operator:
            return
        try:
            from cohezion.compound.telegram_notify import notify

            notify(text)
        except Exception as exc:
            logger.debug("Telegram notification failed (non-blocking): %s", exc)

    def _select_next_strategy(self, failure_class: str, tried: set[str]) -> str | None:
        """Selects the next strategy informed by memory and failure_map without duplicates."""
        # 1. Check memory jump-start
        mem_cand = self.memory.best_for(failure_class)
        if mem_cand and mem_cand in self.strategies and mem_cand not in tried:
            return mem_cand

        # 2. Prefer strategies mapped from current failure-class
        for cand in self.failure_map.get(failure_class, []):
            if cand in self.strategies and cand not in tried:
                return cand

        # 3. Fall back to next unused declared strategy
        for cand in self.strategies:
            if cand not in tried:
                return cand

        return None

    def run(
        self,
        task: GoalTraceTask,
        step_fn: Callable[[GoalTraceTask, str], MonadResult[StepReturn] | StepReturn],
    ) -> GoalTraceResult:
        """Executes synchronous goal-directed trace loop."""
        set_goal(task.condition, source=self.source)

        current_fc = task.initial_failure_class
        tried: set[str] = set()
        path: list[str] = []
        last_obs = ""

        for iteration in range(1, self.max_depth + 1):
            strategy = self._select_next_strategy(current_fc, tried)
            if strategy is None:
                break

            tried.add(strategy)
            path.append(strategy)

            # AutoHarness in-process verifier check (0ms latency bytecode/predicate validation)
            if self.verifier is not None:
                is_valid, reject_reason = self.verifier(task, strategy)
                if not is_valid:
                    satisfied = False
                    note = f"AutoHarness rejected '{strategy}': {reject_reason}"
                    next_fc = f"autoharness:{reject_reason}"
                    last_obs = note
                    observe(note, satisfied=False)
                    self._persist_graph_edge(task.goal_id, strategy, current_fc, False, iteration)
                    if next_fc:
                        current_fc = next_fc
                    continue

            # Monadic execution wrapper
            try:
                raw_res = step_fn(task, strategy)
                if isinstance(raw_res, MonadResult):
                    if raw_res.is_success and raw_res.value is not None:
                        satisfied, note, next_fc = raw_res.value
                    else:
                        satisfied = False
                        note = f"Step failed: {raw_res.error}"
                        next_fc = f"error:{raw_res.error}"
                else:
                    satisfied, note, next_fc = raw_res
            except Exception as e:
                satisfied = False
                note = f"Exception in step execution: {e}"
                next_fc = f"exception:{type(e).__name__}"

            last_obs = note
            observe(note, satisfied=satisfied)
            self._persist_graph_edge(task.goal_id, strategy, current_fc, satisfied, iteration)

            try:
                record_resolution(
                    self.domain,
                    current_fc,
                    strategy,
                    bool(satisfied),
                    source=self.source,
                    tried_order=list(path),
                )
            except Exception as e:
                logger.debug("Resolution log record failed: %s", e)

            if satisfied is True:
                self.memory.record_success(current_fc, strategy)
                self._notify_tg(
                    f"🎯 <b>Goal Converged</b>: <code>{task.condition}</code>\n"
                    f"Resolved in {iteration} steps via <code>{strategy}</code>"
                )
                return GoalTraceResult(
                    solved=True,
                    iterations=iteration,
                    path=path,
                    last_observation=last_obs,
                    goal_status=status(),
                )

            if next_fc:
                current_fc = next_fc

        self._notify_tg(
            f"⚠️ <b>Goal Blocked / Exhausted</b>: <code>{task.condition}</code>\n"
            f"Path: <code>{' → '.join(path)}</code>\n"
            f"Last note: {last_obs[:120]}"
        )
        return GoalTraceResult(
            solved=False,
            iterations=len(path),
            path=path,
            last_observation=last_obs,
            goal_status=status(),
        )

    async def arun(
        self,
        task: GoalTraceTask,
        step_fn: Callable[[GoalTraceTask, str], Any],
    ) -> GoalTraceResult:
        """Executes asynchronous goal-directed trace loop for inference / external I/O."""
        set_goal(task.condition, source=self.source)

        current_fc = task.initial_failure_class
        tried: set[str] = set()
        path: list[str] = []
        last_obs = ""

        for iteration in range(1, self.max_depth + 1):
            strategy = self._select_next_strategy(current_fc, tried)
            if strategy is None:
                break

            tried.add(strategy)
            path.append(strategy)

            # AutoHarness in-process verifier check (0ms latency bytecode/predicate validation)
            if self.verifier is not None:
                is_valid, reject_reason = self.verifier(task, strategy)
                if not is_valid:
                    satisfied = False
                    note = f"AutoHarness rejected '{strategy}': {reject_reason}"
                    next_fc = f"autoharness:{reject_reason}"
                    last_obs = note
                    observe(note, satisfied=False)
                    self._persist_graph_edge(task.goal_id, strategy, current_fc, False, iteration)
                    if next_fc:
                        current_fc = next_fc
                    continue

            # Monadic execution wrapper (async-aware)
            try:
                res = step_fn(task, strategy)
                if inspect.isawaitable(res):
                    raw_res = await res
                else:
                    raw_res = res

                if isinstance(raw_res, MonadResult):
                    if raw_res.is_success and raw_res.value is not None:
                        satisfied, note, next_fc = raw_res.value
                    else:
                        satisfied = False
                        note = f"Step failed: {raw_res.error}"
                        next_fc = f"error:{raw_res.error}"
                else:
                    satisfied, note, next_fc = raw_res
            except Exception as e:
                satisfied = False
                note = f"Exception in async step execution: {e}"
                next_fc = f"exception:{type(e).__name__}"

            last_obs = note
            observe(note, satisfied=satisfied)
            self._persist_graph_edge(task.goal_id, strategy, current_fc, satisfied, iteration)

            try:
                record_resolution(
                    self.domain,
                    current_fc,
                    strategy,
                    bool(satisfied),
                    source=self.source,
                    tried_order=list(path),
                )
            except Exception as e:
                logger.debug("Resolution log record failed: %s", e)

            if satisfied is True:
                self.memory.record_success(current_fc, strategy)
                self._notify_tg(
                    f"🎯 <b>Goal Converged</b>: <code>{task.condition}</code>\n"
                    f"Resolved in {iteration} steps via <code>{strategy}</code>"
                )
                return GoalTraceResult(
                    solved=True,
                    iterations=iteration,
                    path=path,
                    last_observation=last_obs,
                    goal_status=status(),
                )

            if next_fc:
                current_fc = next_fc

        self._notify_tg(
            f"⚠️ <b>Goal Blocked / Exhausted</b>: <code>{task.condition}</code>\n"
            f"Path: <code>{' → '.join(path)}</code>\n"
            f"Last note: {last_obs[:120]}"
        )
        return GoalTraceResult(
            solved=False,
            iterations=len(path),
            path=path,
            last_observation=last_obs,
            goal_status=status(),
        )
