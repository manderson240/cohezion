"""Unit tests for ARC-AGI-3 JAZ Interactive Solver."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.agi.arc_agi_3_jaz_solver import (
    ARC3Action,
    ARC3JAZSolver,
    ARC3Transition,
    ZobristHasher,
)
from cohezion.compound.jaz_primitive import ReturnType, ValidateReturn, invoke, scope


def test_zobrist_hasher_determinism():
    """Verify Zobrist hasher produces deterministic, color-sensitive 64-bit hashes."""
    hasher = ZobristHasher()
    grid1 = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    grid2 = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    grid3 = np.array([[1, 2], [3, 5]], dtype=np.uint8)

    h1 = hasher.hash_grid(grid1)
    h2 = hasher.hash_grid(grid2)
    h3 = hasher.hash_grid(grid3)

    assert h1 == h2
    assert h1 != h3
    assert isinstance(h1, int)


def test_action_verifier_pruning():
    """Verify AutoHarness invariant pruning rejects oscillations."""
    solver = ARC3JAZSolver()
    history = [
        ARC3Transition(
            state_hash=123,
            action=ARC3Action.UP,
            reward=0.0,
            next_state_hash=456,
            done=False,
        )
    ]

    # Moving DOWN immediately after UP when at state 456 is a 2-step oscillation
    is_valid = solver.verify_action(current_state_hash=456, action=ARC3Action.DOWN, history=history)
    assert is_valid is False

    # Moving LEFT or RIGHT is valid
    assert solver.verify_action(current_state_hash=456, action=ARC3Action.RIGHT, history=history) is True


def test_jaz_interactive_step_execution():
    """Verify solver execution inside JAZ invoke with history tracking."""
    solver = ARC3JAZSolver()
    test_grid = np.array([[0, 1, 2], [3, 4, 5], [6, 7, 8]], dtype=np.uint8)

    history: list = []
    # Execute through JAZ invoke primitive
    result = invoke(
        ValidateReturn(lambda r: r["status"] == "completed"),
        func=solver.solve_interactive_step,
        grid=test_grid,
        step_budget=5,
        __history__=history,
    )

    assert result["status"] == "completed"
    assert result["steps_executed"] == 5
    assert len(history) == 6
    steps = [x for x in history if "step" in x]
    assert len(steps) == 5
    assert history[-1]["type"] == "func_call"
    assert result["unique_states"] >= 1
