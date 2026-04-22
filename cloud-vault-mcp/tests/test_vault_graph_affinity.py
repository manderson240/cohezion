# tests/test_vault_graph_affinity.py
import os
import sys

import numpy as np


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.vault_graph.affinity import normalize_l2, project_to_12d


def test_project_to_12d_shape():
    vec = [0.1] * 768
    matrix = np.random.randn(12, 768).astype(np.float32)
    result = project_to_12d(vec, matrix)
    assert len(result) == 12


def test_project_to_12d_deterministic():
    vec = [0.5] * 768
    matrix = np.eye(12, 768, dtype=np.float32)
    assert project_to_12d(vec, matrix) == project_to_12d(vec, matrix)


def test_normalize_l2_unit_length():
    vec = [3.0, 4.0, 0.0]
    normed = normalize_l2(vec)
    length = sum(v**2 for v in normed) ** 0.5
    assert abs(length - 1.0) < 1e-6


def test_normalize_l2_zero_vector_safe():
    vec = [0.0, 0.0, 0.0]
    result = normalize_l2(vec)
    assert result == [0.0, 0.0, 0.0]
