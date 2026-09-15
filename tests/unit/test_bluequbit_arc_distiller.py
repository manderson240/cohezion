"""Unit tests for BlueQubit ARC Distiller and Quantum Artifact Pipeline.

Validates:
1. QuantumDistillationArtifact serialization and deserialization (.npz).
2. BlueQubitARCDistiller quantum symmetry prior computation with mock fallback.
3. QUBO rule selection and AutoHarness deterministic verification integration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from cohezion.quantum.bluequbit_arc_distiller import (
    BlueQubitARCDistiller,
    QuantumDistillationArtifact,
)


@pytest.mark.unit
def test_quantum_distillation_artifact_roundtrip(tmp_path: Path) -> None:
    """Verify serialization and deserialization of distilled quantum artifacts."""
    artifact_path = tmp_path / "test_prior.npz"

    sym_weights = {
        "identity": 0.25,
        "rot90": 0.15,
        "rot180": 0.15,
        "rot270": 0.15,
        "flip_horizontal": 0.10,
        "flip_vertical": 0.10,
        "transpose": 0.05,
        "anti_transpose": 0.05,
    }
    kernel = np.eye(8, dtype=np.float32)
    rules = ["identity", "rotate_90_clockwise", "reflect_horizontal"]
    meta = {"source": "unit_test", "device": "cpu"}

    artifact = QuantumDistillationArtifact(
        symmetry_weights=sym_weights,
        kernel_matrix=kernel,
        verified_rules=rules,
        metadata=meta,
    )

    saved_path = artifact.save(artifact_path)
    assert saved_path.exists()

    loaded = QuantumDistillationArtifact.load(saved_path)
    assert len(loaded.symmetry_weights) == 8
    assert loaded.symmetry_weights["identity"] == pytest.approx(0.25)
    assert loaded.kernel_matrix.shape == (8, 8)
    assert loaded.verified_rules == rules
    assert loaded.metadata.get("device") == "cpu"


@pytest.mark.unit
def test_bluequbit_arc_distiller_symmetry_prior() -> None:
    """Verify quantum symmetry prior computation returns balanced smoothed distribution."""
    distiller = BlueQubitARCDistiller(device="cpu")

    mock_counts = {"0000": 250, "0001": 150, "0010": 100}
    with patch.object(distiller.bridge, "run_quantum_kernel", return_value={"counts": mock_counts}):
        weights = distiller.compute_quantum_symmetry_prior(shots=500)

    assert len(weights) == 8
    assert "identity" in weights
    assert "rot90" in weights
    assert all(w > 0.0 for w in weights.values())
    # Should sum approximately to 1.0 (with slight smoothing roundings)
    assert sum(weights.values()) == pytest.approx(1.0, abs=0.05)


@pytest.mark.unit
def test_bluequbit_arc_distiller_qubo_rule_selection() -> None:
    """Verify QUBO rule selection identifies optimal transformation candidate."""
    distiller = BlueQubitARCDistiller(device="cpu")

    mock_qubo_result = {
        "status": "SUCCESS",
        "job_id": "mock_job_123",
        "optimal_candidate_index": 1,
    }

    with patch.object(
        distiller.qubo_solver, "solve_graph_isomorphism_qubo", return_value=mock_qubo_result
    ):
        res = distiller.distill_task_qubo(
            candidate_costs=[[0.1, 0.9], [0.9, 0.2]],
            rule_names=["rule_identity", "rule_rotate_90"],
            shots=100,
        )

    assert res["status"] == "SUCCESS"
    assert res["optimal_rule"] == "rule_rotate_90"
    assert res["optimal_index"] == 1
    assert res["job_id"] == "mock_job_123"


@pytest.mark.unit
def test_bluequbit_arc_distiller_generate_artifact(tmp_path: Path) -> None:
    """Verify end-to-end generation of offline quantum prior artifact."""
    distiller = BlueQubitARCDistiller(device="cpu")
    out_file = tmp_path / "quantum_prior.npz"

    with patch.object(
        distiller,
        "compute_quantum_symmetry_prior",
        return_value={"identity": 0.5, "rot90": 0.5},
    ):
        artifact = distiller.generate_distillation_artifact(output_path=out_file)

    assert out_file.exists()
    assert artifact.kernel_matrix.shape == (2, 2)
    assert len(artifact.verified_rules) >= 5
    assert artifact.metadata["qubo_enabled"] is True
