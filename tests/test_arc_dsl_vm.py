"""Tests for the Rust PyO3 ARC DSL Virtual Machine and Rayon Hypothesis Evaluator."""

import time
import pytest
import cohezion_physics_core as cpc


def test_connected_components_multi_color() -> None:
    """Verifies 4-connectivity flood fill object extraction on multi-color test grids."""
    grid = [
        [1, 1, 0, 2],
        [1, 0, 0, 2],
        [0, 0, 0, 0],
        [3, 3, 3, 0],
    ]
    comps = cpc.py_extract_connected_components(grid)
    assert len(comps) == 3

    # Check component 1 (color 1)
    c1 = next(c for c in comps if any(1 in row for row in c))
    assert c1[0][0] == 1 and c1[0][1] == 1 and c1[1][0] == 1

    # Check component 2 (color 2)
    c2 = next(c for c in comps if any(2 in row for row in c))
    assert c2[0][3] == 2 and c2[1][3] == 2

    # Check component 3 (color 3)
    c3 = next(c for c in comps if any(3 in row for row in c))
    assert c3[3][0] == 3 and c3[3][1] == 3 and c3[3][2] == 3


def test_gravity_all_directions() -> None:
    """Verifies gravity in all 4 cardinal directions (down, up, left, right)."""
    grid = [
        [1, 0, 0],
        [0, 2, 0],
        [0, 0, 3],
    ]

    # Down (0): drops to bottom
    down = [list(r) for r in cpc.py_gravity(grid, 0)]
    assert down == [
        [0, 0, 0],
        [0, 0, 0],
        [1, 2, 3],
    ]

    # Up (1): rises to top
    up = [list(r) for r in cpc.py_gravity(grid, 1)]
    assert up == [
        [1, 2, 3],
        [0, 0, 0],
        [0, 0, 0],
    ]

    # Left (2): slides to column 0
    left = [list(r) for r in cpc.py_gravity(grid, 2)]
    assert left == [
        [1, 0, 0],
        [2, 0, 0],
        [3, 0, 0],
    ]

    # Right (3): slides to column 2
    right = [list(r) for r in cpc.py_gravity(grid, 3)]
    assert right == [
        [0, 0, 1],
        [0, 0, 2],
        [0, 0, 3],
    ]


def test_recolor_and_filter() -> None:
    """Verifies recoloring and filter_color primitives."""
    grid = [
        [1, 2, 1],
        [2, 1, 2],
    ]

    # Recolor 1 -> 8
    recolored = [list(r) for r in cpc.py_recolor(grid, 1, 8)]
    assert recolored == [
        [8, 2, 8],
        [2, 8, 2],
    ]

    # Filter color 2 (keeps 2, zeroes rest)
    filtered = [list(r) for r in cpc.py_filter_color(grid, 2)]
    assert filtered == [
        [0, 2, 0],
        [2, 0, 2],
    ]


def test_crop_and_bounding_box() -> None:
    """Verifies bounding box calculation and subgrid cropping."""
    grid = [
        [0, 0, 0, 0],
        [0, 4, 4, 0],
        [0, 4, 0, 0],
        [0, 0, 0, 0],
    ]
    bbox = cpc.py_bounding_box(grid)
    assert bbox == (1, 1, 2, 2)

    cropped = [list(r) for r in cpc.py_crop(grid, bbox[0], bbox[1], bbox[2], bbox[3])]
    assert cropped == [
        [4, 4],
        [4, 0],
    ]


def test_vm_execution_chained() -> None:
    """Verifies multi-instruction transformation chains executed in VM."""
    grid = [
        [1, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]
    # Chain: Recolor 1->5 [2, 1, 5], then Gravity Down [4, 0]
    bytecode = [2, 1, 5, 4, 0]
    out = [list(r) for r in cpc.py_execute_arc_dsl(grid, bytecode)]
    assert out == [
        [0, 0, 0],
        [0, 0, 0],
        [5, 0, 0],
    ]


def test_parallel_hypothesis_evaluation_rayon() -> None:
    """Verifies Rayon parallel hypothesis evaluation across candidate programs."""
    # Define 3 demonstration pairs: Program is Recolor 3->7 then Gravity Right
    train_pairs = [
        (
            [[3, 0], [0, 0]],
            [[0, 7], [0, 0]],
        ),
        (
            [[0, 3], [3, 0]],
            [[0, 7], [0, 7]],
        ),
        (
            [[3, 3], [0, 0]],
            [[7, 7], [0, 0]],
        ),
    ]

    # Synthesize candidates:
    # 0: identity [1]
    # 1: gravity down [4, 0]
    # 2: recolor 3->7 [2, 3, 7] (partial score)
    # 3: recolor 3->7 then gravity right [2, 3, 7, 4, 3] (perfect score 1.0)
    # 4..500: dummy bytecodes to test Rayon multi-threading scale
    correct_idx = 3
    candidates = [
        [1],
        [4, 0],
        [2, 3, 7],
        [2, 3, 7, 4, 3],
    ]
    for i in range(496):
        candidates.append([i % 15, (i * 3) % 10])

    t0 = time.perf_counter()
    results = cpc.py_eval_arc_hypotheses(train_pairs, candidates)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(results) == len(candidates)
    # Top ranked program must be the exact match with 1.0 accuracy
    top_cand, top_score = results[0]
    assert top_cand == correct_idx
    assert top_score == pytest.approx(1.0, abs=1e-5)

    # Partial program should score higher than identity/wrong gravity
    score_map = dict(results)
    assert score_map[2] > score_map[1]
    assert score_map[2] > score_map[0]

    print(f"\nRayon Parallel Evaluation: {len(candidates)} programs scored in {elapsed_ms:.2f} ms")
