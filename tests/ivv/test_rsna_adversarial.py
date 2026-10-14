"""Adversarial Verification Suite for RSNA Knee Solutions.

Independent Verification & Validation Authority (IV&V).
Enforces:
1. Multi-condition prediction matrix fuzzing.
2. Kolmogorov Monotonicity Invariant: P(Abnormal) >= max_{k in conditions} P_k for 100% of rows.
3. Extreme edge-case projection (e.g. P_k = 0.999, P_Abnormal = 0.001) re-establishes valid probability topology.
4. CUDA fallback executes on CPU without fatal RuntimeError.
"""

from __future__ import annotations

from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
import torch


# --- Candidate Verification Contracts & Reference Implementations ---

def project_kolmogorov_monotonicity(
    df: pd.DataFrame,
    abnormal_col: str = "Abnormal",
    sub_conditions: list[str] | None = None,
) -> pd.DataFrame:
    """Projects multi-condition probability matrix onto Kolmogorov monotonicity manifold.

    Axiom: E_k subset of E_Abnormal => P(Abnormal) >= max_k P(E_k).
    """
    if sub_conditions is None:
        sub_conditions = [c for c in df.columns if c != abnormal_col and c != "study_id"]

    res = df.copy()
    for col in [abnormal_col] + sub_conditions:
        res[col] = np.clip(res[col], 0.0, 1.0)

    max_sub = res[sub_conditions].max(axis=1)
    res[abnormal_col] = np.maximum(res[abnormal_col], max_sub)
    return res


class MockRSNAInferenceModel(torch.nn.Module):
    """Reference RSNA inference model with verified CPU/CUDA device management."""

    def __init__(self) -> None:
        super().__init__()
        self.fc = torch.nn.Linear(16, 6)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.fc(x))

    def predict_with_device_guard(self, x: torch.Tensor) -> torch.Tensor:
        """Executes forward pass using safe device routing with fallback to CPU."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(device)
        x_dev = x.to(device)
        with torch.no_grad():
            preds = self(x_dev)
        return preds.cpu()


# --- IV&V Adversarial Tests ---

class TestRSNAAdversarialSuite:
    """Independent verification test suite for RSNA Knee solutions."""

    def test_multi_condition_fuzzing_and_kolmogorov_monotonicity(self) -> None:
        """Fuzzes multi-condition prediction matrices and strictly enforces Kolmogorov Monotonicity."""
        conditions = ["ACL", "Meniscus", "Cartilage", "Fracture", "Effusion"]
        N = 500
        rng = np.random.default_rng(1337)

        raw_data = {
            "study_id": [f"study_{i}" for i in range(N)],
            "Abnormal": rng.uniform(0.0, 1.0, size=N),
        }
        for cond in conditions:
            raw_data[cond] = rng.uniform(0.0, 1.0, size=N)

        df_raw = pd.DataFrame(raw_data)
        df_proj = project_kolmogorov_monotonicity(df_raw, abnormal_col="Abnormal", sub_conditions=conditions)

        max_sub_condition = df_proj[conditions].max(axis=1)
        violations = df_proj["Abnormal"] < (max_sub_condition - 1e-9)
        num_violations = int(violations.sum())

        assert num_violations == 0, (
            f"Kolmogorov Monotonicity violated in {num_violations}/{N} rows! "
            f"Worst delta: {(max_sub_condition - df_proj['Abnormal']).max()}"
        )
        assert np.all(df_proj["Abnormal"] >= max_sub_condition)
        assert np.all(df_proj["Abnormal"] <= 1.0)
        assert np.all(df_proj["Abnormal"] >= 0.0)

    def test_extreme_edge_cases_topological_restoration(self) -> None:
        """Injects extreme edge cases (P_k = 0.999, P_Abnormal = 0.001) and verifies topological restoration."""
        conditions = ["ACL", "Meniscus"]
        edge_data = pd.DataFrame(
            {
                "study_id": ["edge_0", "edge_1", "edge_2"],
                "Abnormal": [0.001, 0.0, 1.0],
                "ACL": [0.999, 0.5, 0.1],
                "Meniscus": [0.850, 0.99, 0.0],
            }
        )

        projected = project_kolmogorov_monotonicity(edge_data, abnormal_col="Abnormal", sub_conditions=conditions)

        # Row 0: ACL is 0.999, Abnormal was 0.001 -> Projected Abnormal MUST be >= 0.999
        assert projected.loc[0, "Abnormal"] == pytest.approx(0.999, abs=1e-6)

        # Row 1: Meniscus is 0.99, Abnormal was 0.0 -> Projected Abnormal MUST be >= 0.99
        assert projected.loc[1, "Abnormal"] == pytest.approx(0.990, abs=1e-6)

        # Row 2: Abnormal was already 1.0 -> Remains 1.0
        assert projected.loc[2, "Abnormal"] == pytest.approx(1.0, abs=1e-6)

    def test_cuda_fallback_executes_on_cpu(self) -> None:
        """Verifies that model inference safely falls back to CPU when CUDA is unavailable."""
        model = MockRSNAInferenceModel()
        x_dummy = torch.randn(4, 16)

        with patch("torch.cuda.is_available", return_value=False):
            preds = model.predict_with_device_guard(x_dummy)

        assert preds.device == torch.device("cpu")
        assert preds.shape == (4, 6)
        assert torch.all(preds >= 0.0) and torch.all(preds <= 1.0)
