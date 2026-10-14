"""PlanM: Monadic Planning Composition & Monotonic Invariant Execution.

Enforces functional isolation of planning traces:
1. Pure State-Passing: Plans are functions `run: S -> StepResult[S, A]`.
2. Monadic Composition: Chains steps via `bind` (or `>>=`) without global state side-effects.
3. Monotonic Improvement Invariant: Secondary heuristic hypotheses cannot overwrite
   valid primary outputs unless Pareto-dominance or invalidity is proven.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

S = TypeVar("S")  # State type
A = TypeVar("A")  # Action/Result type
B = TypeVar("B")  # Mapped Result type


@dataclass(frozen=True)
class StepResult(Generic[S, A]):
    """Result of a single planning step."""

    value: A
    next_state: S
    cost: float = 0.0
    trace: Tuple[str, ...] = ()
    is_terminal: bool = False
    confidence: float = 1.0

    def add_trace(self, event: str) -> StepResult[S, A]:
        return StepResult(
            value=self.value,
            next_state=self.next_state,
            cost=self.cost,
            trace=self.trace + (event,),
            is_terminal=self.is_terminal,
            confidence=self.confidence,
        )


class PlanM(Generic[S, A]):
    """Monadic container for planning operations."""

    def __init__(self, run_fn: Callable[[S], StepResult[S, A]]) -> None:
        self._run = run_fn

    def run(self, initial_state: S) -> StepResult[S, A]:
        """Executes the plan starting from the given state."""
        return self._run(initial_state)

    @classmethod
    def pure(cls, value: A, cost: float = 0.0) -> PlanM[S, A]:
        """Lifts a pure value into the planning monad."""
        return cls(lambda state: StepResult(value=value, next_state=state, cost=cost))

    def map(self, fn: Callable[[A], B]) -> PlanM[S, B]:
        """Transforms the result value of the plan."""
        def _mapped(state: S) -> StepResult[S, B]:
            res = self._run(state)
            return StepResult(
                value=fn(res.value),
                next_state=res.next_state,
                cost=res.cost,
                trace=res.trace,
                is_terminal=res.is_terminal,
                confidence=res.confidence,
            )

        return PlanM(_mapped)

    def bind(self, fn: Callable[[A], PlanM[S, B]]) -> PlanM[S, B]:
        """Monadic bind: passes the result of this step to the next plan function."""
        def _bound(state: S) -> StepResult[S, B]:
            first_res = self._run(state)
            if first_res.is_terminal:
                # If terminal, cannot continue, lift value into terminal B
                return StepResult(
                    value=None,  # type: ignore
                    next_state=first_res.next_state,
                    cost=first_res.cost,
                    trace=first_res.trace + ("TERMINATED_EARLY",),
                    is_terminal=True,
                    confidence=first_res.confidence,
                )
            next_plan = fn(first_res.value)
            second_res = next_plan.run(first_res.next_state)
            return StepResult(
                value=second_res.value,
                next_state=second_res.next_state,
                cost=first_res.cost + second_res.cost,
                trace=first_res.trace + second_res.trace,
                is_terminal=second_res.is_terminal,
                confidence=min(first_res.confidence, second_res.confidence),
            )

        return PlanM(_bound)

    def __rshift__(self, fn: Callable[[A], PlanM[S, B]]) -> PlanM[S, B]:
        """Operator overload for monadic bind (`plan >> fn`)."""
        return self.bind(fn)

    @staticmethod
    def monotonic_ensemble(
        primary_plan: PlanM[S, A],
        secondary_plan: PlanM[S, A],
        is_dummy_fn: Callable[[A], bool],
        dominance_fn: Optional[Callable[[A, A], bool]] = None,
    ) -> PlanM[S, Tuple[A, Optional[A]]]:
        """Enforces the Monotonic Improvement Invariant.

        Returns (final_primary, final_secondary).
        Primary output is NEVER clobbered by secondary unless primary is dummy or secondary Pareto-dominates.
        """
        def _ensemble(state: S) -> StepResult[S, Tuple[A, Optional[A]]]:
            res_primary = primary_plan.run(state)
            res_secondary = secondary_plan.run(state)

            primary_val = res_primary.value
            secondary_val = res_secondary.value

            # If primary produced a dummy/invalid output, promote secondary to primary
            if is_dummy_fn(primary_val):
                return StepResult(
                    value=(secondary_val, None),
                    next_state=res_secondary.next_state,
                    cost=res_primary.cost + res_secondary.cost,
                    trace=res_primary.trace + ("PROMOTED_SECONDARY_DUE_TO_DUMMY_PRIMARY",) + res_secondary.trace,
                    is_terminal=res_secondary.is_terminal,
                    confidence=res_secondary.confidence,
                )

            # If secondary is proven to Pareto-dominate primary
            if dominance_fn and dominance_fn(secondary_val, primary_val):
                return StepResult(
                    value=(secondary_val, primary_val),
                    next_state=res_secondary.next_state,
                    cost=res_primary.cost + res_secondary.cost,
                    trace=res_primary.trace + ("PROMOTED_SECONDARY_DUE_TO_DOMINANCE",) + res_secondary.trace,
                    is_terminal=res_secondary.is_terminal,
                    confidence=res_secondary.confidence,
                )

            # Standard monotonic preservation: primary preserved in slot 1, secondary in slot 2
            return StepResult(
                value=(primary_val, secondary_val),
                next_state=res_primary.next_state,
                cost=res_primary.cost + res_secondary.cost,
                trace=res_primary.trace + ("PRESERVED_PRIMARY_SLOT1_SECONDARY_SLOT2",) + res_secondary.trace,
                is_terminal=res_primary.is_terminal,
                confidence=res_primary.confidence,
            )

        return PlanM(_ensemble)
