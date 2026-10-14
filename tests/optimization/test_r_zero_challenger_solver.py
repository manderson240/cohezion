"""Unit tests for R-Zero Challenger vs Solver engine."""

import pytest

from cohezion.optimization.r_zero_challenger_solver import (
    ProceduralARCGenerator,
    RZeroChallenge,
    RZeroChallenger,
    RZeroPragmatist,
    RZeroSolution,
    RZeroSolver,
    RZeroTriadLoop,
)


def test_procedural_arc_generator():
    task = ProceduralARCGenerator.generate_task(difficulty=2.0)
    assert "train" in task
    assert len(task["train"]) >= 2
    assert "test" in task
    assert "ground_truth_test_output" in task

    # Verify input and output grids have identical dimensions
    for pair in task["train"]:
        assert len(pair["input"]) == len(pair["output"])
        assert len(pair["input"][0]) == len(pair["output"][0])


@pytest.mark.asyncio
async def test_challenger_creation_and_difficulty():
    challenger = RZeroChallenger(domain="arc_agi", initial_difficulty=2.0, difficulty_step=0.5)
    challenge = await challenger.create_challenge()

    assert challenge.challenge_id.startswith("rzero_arc_agi_")
    assert challenge.difficulty == 2.0
    assert len(challenge.constraints) > 0

    # Difficulty adjustment on high success rate
    new_diff = challenger.adjust_difficulty(success_rate=1.0)
    assert new_diff > 2.0

    # Difficulty adjustment on low success rate
    lower_diff = challenger.adjust_difficulty(success_rate=0.0)
    assert lower_diff < new_diff


@pytest.mark.asyncio
async def test_solver_deterministic_heuristic():
    solver = RZeroSolver(model_name="test_model")
    challenge = RZeroChallenge(
        challenge_id="test_c1",
        domain="arc_agi",
        difficulty=1.5,
        task_spec={"transform_rule": "horizontal_flip", "train": []},
    )
    solution = await solver.solve(challenge)

    assert solution.challenge_id == "test_c1"
    assert "def transform(grid):" in solution.code
    assert solution.execution_time_ms >= 0.0


def test_pragmatist_evaluation_success_and_failure(tmp_path):
    archive_file = tmp_path / "verified.jsonl"
    pragmatist = RZeroPragmatist(archive_path=archive_file)
    challenger = RZeroChallenger(initial_difficulty=2.0)

    # 1. Successful case: Horizontal flip
    task_spec = {
        "train": [
            {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
        ],
        "test": [{"input": [[5, 6], [7, 8]]}],
        "ground_truth_test_output": [[6, 5], [8, 7]],
    }
    challenge = RZeroChallenge(
        challenge_id="c_success",
        domain="arc_agi",
        difficulty=2.0,
        task_spec=task_spec,
    )
    good_solution = RZeroSolution(
        solution_id="s_good",
        challenge_id="c_success",
        solver_model="test_model",
        code="def transform(grid):\n    return [row[::-1] for row in grid]",
    )

    eval_good = pragmatist.evaluate(challenge, good_solution, challenger)
    assert eval_good.is_success
    assert eval_good.train_accuracy == 1.0
    assert eval_good.test_accuracy == 1.0
    assert archive_file.exists()

    # 2. Failing case: Buggy code
    bad_solution = RZeroSolution(
        solution_id="s_bad",
        challenge_id="c_success",
        solver_model="test_model",
        code="def transform(grid):\n    return grid[999]",  # IndexError
    )
    eval_bad = pragmatist.evaluate(challenge, bad_solution, challenger)
    assert not eval_bad.is_success
    assert eval_bad.train_accuracy == 0.0


@pytest.mark.asyncio
async def test_r_zero_triad_loop_step(tmp_path):
    loop = RZeroTriadLoop(domain="arc_agi", initial_difficulty=2.0)
    loop.pragmatist.archive_path = tmp_path / "triad_verified.jsonl"

    eval_result = await loop.step()
    assert eval_result.challenge_id.startswith("rzero_arc_agi_")
    assert len(loop.history) == 1


def test_rank_candidate_solutions_with_jev():
    loop = RZeroTriadLoop(domain="arc_agi")
    candidates = [
        ("HorizontalFlip", "def transform(g): return [r[::-1] for r in g]"),
        ("Identity", "def transform(g): return [r[:] for r in g]"),
    ]
    chosen_idx = loop.rank_candidate_solutions_with_jev(candidates, "Select transform")
    assert chosen_idx in (1, 2)
