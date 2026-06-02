"""Markov / MDP state-transition control for agentic loops — SGLang-free.

Implements the "state-managed execution" pattern (constrain the agent to valid next
states; audit the path) WITHOUT SGLang. The guide's `sgl.select(choices=...)` gatekeeping
is just enum-constrained decoding, which our lemonade/llama.cpp stack already does via
`response_format: {type: json_schema, schema: {enum: [...]}}` (verified 2026-06-01). So the
control layer runs on the existing fleet — no CUDA, no AWQ/FP16, no abandoning GGUF/NPU.

Two pieces:
  - ``TransitionController`` — the transition matrix, validity checks, the constrained-
    decoding response_format for the next-state pick, and dynamic edge weights updated
    from observed rewards (lower the weight of transitions that keep failing).
  - Markov path analysis (``first_passage`` / ``time_in_states`` / ``detect_stuck_loops``)
    over a state sequence — e.g. the state path extracted from a recursive ExecutionTrace
    (agent.unified_harness) — to verify the agent spends time in productive states rather
    than stuck in error-correction loops (the guide's "First Passage" reliability analysis).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransitionController:
    """Enforce a Markov transition matrix over an agent's state machine.

    ``matrix`` maps each state to its allowed next states. Edge ``weights`` start at 1.0
    and are nudged by :meth:`record_transition` so consistently-bad transitions decay.
    """

    matrix: dict[str, list[str]]
    weights: dict[tuple[str, str], float] = field(default_factory=dict)

    def valid_next(self, state: str) -> list[str]:
        """Allowed next states from ``state`` (empty if terminal/unknown)."""
        return list(self.matrix.get(state, []))

    def is_valid(self, frm: str, to: str) -> bool:
        return to in self.matrix.get(frm, [])

    def enum_schema(self, state: str, name: str = "transition") -> dict[str, Any]:
        """Build the lemonade/OpenAI ``response_format`` that constrains the model to pick
        ONLY a valid next state — the SGLang ``select(choices=...)`` equivalent on our stack.

        Pass the returned dict as ``response_format`` to the chat-completions call; the model
        is then guaranteed to emit ``{"next_state": <one of valid_next(state)>}``.
        """
        choices = self.valid_next(state)
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"next_state": {"type": "string", "enum": choices}},
                    "required": ["next_state"],
                    "additionalProperties": False,
                },
            },
        }

    def record_transition(self, frm: str, to: str, reward: float) -> float:
        """Update the edge weight from an observed outcome (reward in roughly [-1, 1]).

        Exponential nudge toward (1 + reward); clamped to [0.01, 2.0]. A transition that
        keeps leading to non-convergence (negative reward) decays; productive ones rise.
        Returns the new weight. (Invalid edges are recorded too — useful to spot a matrix
        that's missing a transition the agent keeps wanting.)
        """
        key = (frm, to)
        w = self.weights.get(key, 1.0)
        target = max(0.0, 1.0 + reward)
        w = max(0.01, min(2.0, w + 0.25 * (target - w)))
        self.weights[key] = w
        return w

    def ranked_next(self, state: str) -> list[tuple[str, float]]:
        """Valid next states sorted by current weight (highest first)."""
        return sorted(
            ((s, self.weights.get((state, s), 1.0)) for s in self.valid_next(state)),
            key=lambda kv: kv[1],
            reverse=True,
        )


# --- Markov path analysis (First-Passage reliability over a state sequence) ---


def first_passage(state_sequence: list[str], target: str) -> int | None:
    """Index of first arrival at ``target`` (0-based), or None if never reached."""
    for i, s in enumerate(state_sequence):
        if s == target:
            return i
    return None


def time_in_states(state_sequence: list[str]) -> dict[str, int]:
    """How many steps the agent spent in each state."""
    return dict(Counter(state_sequence))


def detect_stuck_loops(state_sequence: list[str], threshold: int = 3) -> list[str]:
    """States the agent occupied for >= ``threshold`` CONSECUTIVE steps (stuck signal).

    E.g. an agent cycling in 'error_correction' for 3+ steps is a reliability red flag —
    the guide's "stuck in error-correction loops" detector.
    """
    stuck: list[str] = []
    run_state: str | None = None
    run_len = 0
    for s in state_sequence:
        if s == run_state:
            run_len += 1
        else:
            run_state, run_len = s, 1
        if run_len == threshold and run_state not in stuck:
            stuck.append(run_state)
    return stuck
