"""Unit tests for Strix Halo Multithreaded DSL Search Engine."""

from __future__ import annotations

import numpy as np

from cohezion.arc.strix_dsl_search import (
    StrixHaloDSLEngine,
    grid_hash,
)


def test_grid_hash_deterministic():
    g1 = np.array([[1, 2], [3, 4]], dtype=np.int32)
    g2 = np.array([[1, 2], [3, 4]], dtype=np.int32)
    g3 = np.array([[1, 2], [3, 5]], dtype=np.int32)

    assert grid_hash(g1) == grid_hash(g2)
    assert grid_hash(g1) != grid_hash(g3)


def test_strix_dsl_engine_solves_rot90():
    engine = StrixHaloDSLEngine(max_depth=2, beam_width=20, n_threads=4)

    task = {
        "train": [
            {
                "input": [[1, 2], [3, 4]],
                "output": [[2, 4], [1, 3]],
            },  # rot90 in numpy is counter-clockwise: [[2, 4], [1, 3]]
        ],
        "test": [{"input": [[5, 6], [7, 8]]}],
    }

    prog, preds = engine.solve_single_task(task)
    assert prog is not None
    assert prog.ops == ("rotate_90",)
    assert len(preds) == 1
    assert preds[0]["solution"] == [[6, 8], [5, 7]]
    assert preds[0]["source"] == "strix_exact_dsl"


def test_strix_dsl_parallel_batch():
    engine = StrixHaloDSLEngine(max_depth=2, beam_width=20, n_threads=8)

    tasks = {
        "t1": {
            "train": [{"input": [[1, 0], [0, 0]], "output": [[0, 1], [0, 0]]}],
            "test": [{"input": [[2, 0], [0, 0]]}],
        },
        "t2": {
            "train": [{"input": [[1, 2], [3, 4]], "output": [[2, 4], [1, 3]]}],
            "test": [{"input": [[9, 8], [7, 6]]}],
        },
    }

    results = engine.solve_task_batch_parallel(tasks)
    assert "t1" in results and "t2" in results
    assert len(results["t1"]) == 1
    assert len(results["t2"]) == 1
