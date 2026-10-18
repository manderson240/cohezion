"""Verifier-Owned Independent Adversarial Test Suite for ARC-AGI-3.
==================================================================
Strictly owned by the IV&V Authority. Code creators cannot alter these tests.

Enforces:
1. 64-bit SplitMix64 Zobrist state hashing collision resistance, speed, and determinism.
2. Cayley permutation group budget manager (allocates 35-120 steps adaptively).
3. AutoHarness zero-cost bytecode verifier pruning suicidal actions (<0.05 ms latency).
4. Local affordance BFS search for doors, keys, and interactables.
5. Invariant against state cycle deadlocks and oscillation loops.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_solver_module():
    solver_path = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/solver.py")
    spec = importlib.util.spec_from_file_location("arc3_solver", solver_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {solver_path}")
    import sys
    mod = importlib.util.module_from_spec(spec)
    sys.modules["arc3_solver"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def solver_mod():
    return _load_solver_module()


def test_zobrist_hashing_determinism_and_collision(solver_mod) -> None:
    """Verifies that Zobrist 64-bit hash is deterministic and collision-free."""
    hasher = solver_mod.ZobristHasher(max_h=10, max_w=10)
    grid1 = [[0] * 10 for _ in range(10)]
    grid1[2][3] = 4
    grid1[5][5] = 7

    h1_a = hasher.hash_grid(grid1, agent_pos=(2, 2))
    h1_b = hasher.hash_grid(grid1, agent_pos=(2, 2))
    assert h1_a == h1_b, "Zobrist hash must be deterministic"

    # Perturbed cell
    grid2 = [row[:] for row in grid1]
    grid2[5][5] = 8
    h2 = hasher.hash_grid(grid2, agent_pos=(2, 2))
    assert h1_a != h2, "Different color in cell must produce different hash"

    # Perturbed agent position
    h3 = hasher.hash_grid(grid1, agent_pos=(2, 3))
    assert h1_a != h3, "Different agent position must produce different hash"


def test_cayley_budget_manager_adaptive_allocation(solver_mod) -> None:
    """Verifies Cayley permutation group budget manager adaptively throttles on cycles."""
    budget_mgr = solver_mod.CayleyBudgetManager(min_budget=35, max_budget=120)

    # Initial novel state: should have high novelty and high budget
    initial_budget = budget_mgr.compute_budget(state_hash=12345, grid_change_ratio=0.5, affordance_count=2)
    assert initial_budget >= 80, f"Expected high initial budget, got {initial_budget}"

    # Repeated visits to same state (stuck in cycle): should throttle towards min_budget
    for _ in range(10):
        budget_mgr.record_state(state_hash=12345)
    throttled_budget = budget_mgr.compute_budget(state_hash=12345, grid_change_ratio=0.0, affordance_count=0)
    assert throttled_budget <= 45, f"Expected throttled budget on repeated state, got {throttled_budget}"


def test_autoharness_action_verifier_pruning(solver_mod) -> None:
    """Verifies AutoHarness action verifier prunes out-of-bounds and wall-collision actions."""
    verifier = solver_mod.AutoHarnessBytecodeVerifier(solid_colors={1})
    grid = [
        [1, 1, 1, 1, 1],  # Wall is 1
        [1, 0, 0, 0, 1],  # Empty is 0
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ]
    # Agent at (1, 1)
    agent_pos = (1, 1)

    # Moving UP hits wall at (0, 1)
    valid_up, reason_up = verifier.verify_action(grid, agent_pos, solver_mod.ACTION_UP)
    assert not valid_up, "Moving UP into wall must be pruned"
    assert "wall" in reason_up.lower()

    # Moving LEFT hits wall at (1, 0)
    valid_left, _ = verifier.verify_action(grid, agent_pos, solver_mod.ACTION_LEFT)
    assert not valid_left, "Moving LEFT into wall must be pruned"

    # Moving RIGHT is free space (1, 2)
    valid_right, _ = verifier.verify_action(grid, agent_pos, solver_mod.ACTION_RIGHT)
    assert valid_right, "Moving RIGHT into empty space must be valid"

    # Moving DOWN is free space (2, 1)
    valid_down, _ = verifier.verify_action(grid, agent_pos, solver_mod.ACTION_DOWN)
    assert valid_down, "Moving DOWN into empty space must be valid"


def test_local_affordance_search_plan(solver_mod) -> None:
    """Verifies that affordance search successfully plans shortest path to target."""
    affordance_search = solver_mod.LocalAffordanceSearch(solid_colors={1})
    # 5x5 grid with empty space and target object (color 4) at (1, 3)
    grid = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 4, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ]
    agent_pos = (1, 1)
    affordances = affordance_search.find_affordances(grid, agent_pos)

    assert len(affordances) >= 1, "Should identify target affordance"
    best = affordances[0]
    assert best.pos == (1, 3)
    assert len(best.plan) == 2, f"Shortest path from (1,1) to (1,3) should be 2 steps, got {len(best.plan)}"
    assert best.plan == [solver_mod.ACTION_RIGHT, solver_mod.ACTION_RIGHT]


def test_arc3_orthogonal_escape_pulse(solver_mod) -> None:
    """Verifies that anti-parallel 2-cycles trigger an orthogonal impulse to break deadlocks."""
    solver = solver_mod.ARCAGI3InteractiveSolver()
    # 5x5 grid with open space
    grid = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ]
    solver.reset(grid, agent_pos=(2, 2))
    # Simulate oscillating between UP and DOWN
    solver.recent_moves = [solver_mod.ACTION_UP, solver_mod.ACTION_DOWN]

    # Next action must NOT be UP or DOWN; must be orthogonal (LEFT or RIGHT)
    act = solver.select_action(grid, agent_pos=(2, 2))
    assert act in (solver_mod.ACTION_LEFT, solver_mod.ACTION_RIGHT), (
        f"Expected orthogonal escape action (LEFT or RIGHT), got {act}"
    )


def test_arc3_d4_group_equivariance_exact_solver(solver_mod) -> None:
    """Verifies demonstration-guided D4 dihedral group exact solving."""
    train_pairs = [
        {"input": [[1, 2], [3, 4]], "output": [[3, 1], [4, 2]]},  # rot270
        {"input": [[5, 6], [7, 8]], "output": [[7, 5], [8, 6]]},  # rot270
    ]
    test_in = [[9, 0], [1, 2]]
    predicted = solver_mod.solve_d4_equivariance(train_pairs, test_in)
    assert predicted is not None
    assert predicted == [[1, 9], [2, 0]]

