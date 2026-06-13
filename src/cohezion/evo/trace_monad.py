"""TraceMonad — state monad threading EVO TraceState through recursive trace operations.

The state monad satisfies all three monad laws, making trace pipelines safely composable:

  Left identity:   TraceMonad.unit(a, s).bind(f)        ==  f(a, s)
  Right identity:  m.bind(lambda v, s: unit(v, s))      ==  m
  Associativity:   m.bind(f).bind(g)                    ==  m.bind(lambda v, s: f(v, s).bind(g))

Usage::

    from cohezion.evo.trace_monad import TraceMonad, TraceState

    initial = TraceMonad.unit("task description", TraceState(coherence=0.5))

    result = (
        initial
        >> physics_bind       # (str, TraceState) -> TraceMonad[str]  — HIHO step
        >> modality_bind      # (str, TraceState) -> TraceMonad[str]  — dispatch text/audio/image
        >> tracker_bind       # (str, TraceState) -> TraceMonad[str]  — JourneyTracker record
    )

    final_coherence = result.state.coherence
    final_phi       = result.state.phi
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class TraceState:
    """Immutable EVO physics state threaded through monadic trace operations.

    Frozen so each bind step derives a new state rather than mutating in place,
    preserving the monad's referential transparency.
    """

    coherence: float = 0.5
    phi: float = 1.0  # 4*c*(1-c) HIHO kernel evaluated at coherence
    step_index: int = 0
    modalities_used: tuple[str, ...] = ()
    latent_snapshot: tuple[float, ...] = ()
    latency_ms: float = 0.0
    latent_delta: float = 0.0

    def advance(
        self,
        *,
        coherence: float,
        phi: float,
        modalities: list[str],
        latent: list[float],
        latency_ms: float = 0.0,
        latent_delta: float = 0.0,
    ) -> "TraceState":
        """Derive the next state after one trace step — step_index increments, modalities accumulate."""
        return TraceState(
            coherence=coherence,
            phi=phi,
            step_index=self.step_index + 1,
            modalities_used=self.modalities_used + tuple(modalities),
            latent_snapshot=tuple(latent),
            latency_ms=latency_ms,
            latent_delta=latent_delta,
        )


class TraceMonad(Generic[T]):
    """State monad threading EVO TraceState through recursive trace operations.

    Type parameter T is the computation value at each pipeline stage (typically str
    for the task description, or TraceResult for the final output).

    The >> operator is syntactic sugar for bind, enabling Haskell-style do-notation::

        (TraceMonad.unit(v, s) >> step1 >> step2 >> step3).state
    """

    def __init__(self, value: T, state: TraceState) -> None:
        self._value = value
        self._state = state

    @classmethod
    def unit(cls, value: T, state: TraceState | None = None) -> "TraceMonad[T]":
        """Wrap a value in the monad (monadic return / pure)."""
        return cls(value, state if state is not None else TraceState())

    def bind(self, fn: Callable[[T, TraceState], "TraceMonad[U]"]) -> "TraceMonad[U]":
        """Sequence: unwrap value + state, apply fn, return new monad (monadic >>=)."""
        return fn(self._value, self._state)

    def then(self, fn: Callable[[T], U]) -> "TraceMonad[U]":
        """Apply a pure function to the value — state passes through unchanged."""
        return TraceMonad(fn(self._value), self._state)

    def __rshift__(self, fn: Callable[[T, TraceState], "TraceMonad[U]"]) -> "TraceMonad[U]":
        """>> is syntactic sugar for bind."""
        return self.bind(fn)

    @property
    def value(self) -> T:
        return self._value

    @property
    def state(self) -> TraceState:
        return self._state
