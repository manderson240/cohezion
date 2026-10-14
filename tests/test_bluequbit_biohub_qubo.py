"""Unit tests for BlueQubit Biohub QUBO Lineage & Morphogenetic Tracker.
=====================================================================
Verifies:
1. Linear and quadratic conflict matrix construction.
2. Deterministic offline fallback solver correctness.
3. Live / mock BlueQubit dispatch.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from cohezion.quantum.bluequbit_biohub_qubo import BiohubQUBOTracker


def test_build_lineage_qubo_empty():
    tracker = BiohubQUBOTracker()
    h, J, mapping = tracker.build_lineage_qubo([])
    assert len(h) == 0
    assert J.shape == (0, 0)
    assert len(mapping) == 0


def test_build_lineage_qubo_conflict_structure():
    tracker = BiohubQUBOTracker()
    # Edges: (src, tgt, cost)
    # (1 -> 10, cost -3.0), (1 -> 11, cost -2.0) [conflict on src=1]
    # (2 -> 10, cost -4.0) [conflict on tgt=10 with edge 0]
    # (3 -> 12, cost -1.0) [no conflict]
    edges = [
        (1, 10, -3.0),
        (1, 11, -2.0),
        (2, 10, -4.0),
        (3, 12, -1.0),
    ]
    h, J, mapping = tracker.build_lineage_qubo(edges, conflict_penalty=10.0)

    assert len(h) == 4
    assert np.allclose(h, [-3.0, -2.0, -4.0, -1.0])
    # Edge 0 (1->10) conflicts with Edge 1 (1->11) on src=1
    assert J[0, 1] == 10.0
    assert J[1, 0] == 10.0
    # Edge 0 (1->10) conflicts with Edge 2 (2->10) on tgt=10
    assert J[0, 2] == 10.0
    assert J[2, 0] == 10.0
    # Edge 3 has no conflict with edge 0, 1, or 2
    assert J[3, 0] == 0.0
    assert J[3, 1] == 0.0
    assert J[3, 2] == 0.0


def test_solve_qubo_deterministic_fallback():
    tracker = BiohubQUBOTracker(token="dummy")
    tracker.client = None  # Force offline fallback
    edges = [
        (1, 10, -3.0),
        (1, 11, -2.0),  # Conflicting with edge 0, but edge 0 has better cost (-3 vs -2)
        (2, 10, -4.0),  # Conflicting with edge 0, but edge 2 has best cost (-4 vs -3)
        (3, 12, -1.5),  # No conflict
    ]
    h, J, _ = tracker.build_lineage_qubo(edges, conflict_penalty=10.0)
    sol, meta = tracker.solve_qubo(h, J)

    assert len(sol) == 4
    assert meta["status"] == "DETERMINISTIC_FALLBACK"
    assert sol[2] == 1  # Best cost (2->10)
    assert sol[0] == 0  # Rejected due to conflict with edge 2
    assert sol[1] == 1  # (1->11) selected
    assert sol[3] == 1  # (3->12) selected


def test_solve_qubo_live_bluequbit():
    """Verify live dispatch to BlueQubit if token is present in environment."""
    tracker = BiohubQUBOTracker()
    if tracker.client is not None:
        edges = [
            (1, 10, -3.0),
            (2, 11, -2.5),
        ]
        h, J, _ = tracker.build_lineage_qubo(edges, conflict_penalty=10.0)
        sol, meta = tracker.solve_qubo(h, J, shots=200)
        assert meta["status"] == "SUCCESS"
        assert "bluequbit" in meta["backend"]
        assert len(sol) == 2


def test_solve_qubo_with_mock_bluequbit():
    mock_client = MagicMock()
    mock_job = MagicMock()
    mock_job.job_id = "test_job_123"
    mock_job.get_counts.return_value = {"0101": 800, "1010": 200}
    mock_client.run.return_value = mock_job

    with patch("cohezion.quantum.bluequbit_biohub_qubo.HAS_BLUEQUBIT", True):
        tracker = BiohubQUBOTracker(token="mock_token")
        tracker.client = mock_client

        h = np.array([-2.0, 1.0, -3.0, 2.0])
        J = np.zeros((4, 4))
        sol, meta = tracker.solve_qubo(h, J)

        assert meta["status"] == "SUCCESS"
        assert meta["job_id"] == "test_job_123"
        assert len(sol) == 4
