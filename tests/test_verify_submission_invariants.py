"""
Unit tests for scripts/kaggle/verify_submission_invariants.py
"""

import os
import json
import pytest
import pandas as pd
import numpy as np

from scripts.kaggle.verify_submission_invariants import (
    verify_biohub_submission,
    verify_rsna_submission,
    verify_arc_submission,
    verify_kaggriculture_bot,
)


def test_verify_biohub_official_schema(tmp_path):
    csv_path = tmp_path / "biohub_sub.csv"
    data = {
        "id": [0, 1, 2, 3],
        "dataset": ["ds1", "ds1", "ds1", "ds1"],
        "row_type": ["node", "node", "edge", "edge"],
        "node_id": [0, 1, -1, -1],
        "t": [0, 1, -1, -1],
        "z": [10, 10, -1, -1],
        "y": [20, 21, -1, -1],
        "x": [30, 31, -1, -1],
        "source_id": [-1, -1, 0, 0],
        "target_id": [-1, -1, 1, 1],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = verify_biohub_submission(str(csv_path))
    assert result.passed is True
    assert result.metrics["total_nodes"] == 2
    assert result.metrics["total_edges"] == 2


def test_verify_rsna_logloss_bounds(tmp_path):
    csv_path = tmp_path / "rsna_sub.csv"
    data = {
        "series_id": ["s1", "s2"],
        "acl_tear": [0.15, 0.20],
        "meniscus_tear": [0.30, 0.35],
        "abnormal": [0.45, 0.50],
        "fracture": [0.05, 0.08],
        "tendon_injury": [0.03, 0.04],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = verify_rsna_submission(str(csv_path))
    assert result.passed is True
    assert result.metrics["min_predicted_probability"] >= 0.03
    assert result.metrics["max_predicted_probability"] <= 0.50


def test_verify_rsna_logloss_singularity_caught(tmp_path):
    csv_path = tmp_path / "rsna_singularity.csv"
    data = {
        "series_id": ["s1"],
        "acl_tear": [0.0],  # Fatal singularity
        "meniscus_tear": [0.3],
        "abnormal": [0.4],
        "fracture": [0.05],
        "tendon_injury": [0.03],
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    result = verify_rsna_submission(str(csv_path))
    assert result.passed is False
    assert any("Fatal Log-Loss Singularity" in e for e in result.errors)


def test_verify_arc_submission_valid(tmp_path):
    json_path = tmp_path / "arc_sub.json"
    data = {
        "task_001": [
            {
                "attempt_1": [[1, 2], [3, 4]],
                "attempt_2": [[2, 1], [4, 3]],
            }
        ]
    }
    with open(json_path, "w") as f:
        json.dump(data, f)
    result = verify_arc_submission(str(json_path))
    assert result.passed is True
    assert result.metrics["total_tasks"] == 1
    assert result.metrics["identical_attempt_pairs"] == 0


def test_verify_kaggriculture_bot(tmp_path):
    py_path = tmp_path / "bot.py"
    code = """
def agent(obs, config):
    # Buy cows for dairy compounding
    dairy_cows = 8
    # Turn 28 liquidation
    if obs['step'] >= 28:
        return 'liquidate'
    return 'noop'
"""
    with open(py_path, "w") as f:
        f.write(code)
    result = verify_kaggriculture_bot(str(py_path))
    assert result.passed is True
    assert "agent" in result.metrics["functions"]
