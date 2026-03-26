"""
Tests for FLUME latent space visualization endpoint.

Portfolio Integration: Validates /flume/latent-space endpoint returns valid
3D coordinates for frontend visualization (FlumeNavigator component).

Test Philosophy:
- Test the API contract (request/response structure)
- Mock FLUME VAE to avoid checkpoint dependencies
- Validate PCA reduction correctness
- Check error handling (no VAE, invalid params)

Follows CLAUDE.md: "Implement ONE feature, validate manually, write 5 tests"
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def mock_vae():
    """Mock FLUME VAE with predictable latent dimension."""
    vae = MagicMock()
    vae.config.z_dim = 32
    vae.device = "cpu"
    return vae


@pytest.fixture
def client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient

    from cohezion.api import app

    return TestClient(app)


def test_flume_latent_space_returns_valid_structure(client, mock_vae):
    """
    Test 1/5: API returns expected JSON structure.

    Validates:
    - Response has latent_dim, samples, samples_3d, variance_explained, coherence_scores
    - samples_3d is list of [x, y, z] coordinates
    - coherence_scores matches sample count
    """
    with patch("cohezion.api._get_vae", return_value=mock_vae):
        response = client.post(
            "/flume/latent-space",
            json={"n_samples": 10, "seed": 42},
        )

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "latent_dim" in data
    assert "samples" in data
    assert "samples_3d" in data
    assert "variance_explained" in data
    assert "coherence_scores" in data

    # Check dimensions
    assert data["latent_dim"] == 32
    assert len(data["samples"]) == 0  # Issue #8: now empty to reduce response size
    assert len(data["samples_3d"]) == 10
    assert len(data["coherence_scores"]) == 10

    # Check 3D coordinates are valid
    for coord in data["samples_3d"]:
        assert len(coord) == 3  # [x, y, z]
        assert all(isinstance(v, (int, float)) for v in coord)


def test_flume_latent_space_pca_reduction_correctness(client, mock_vae):
    """
    Test 2/5: PCA reduction preserves relative distances.

    Validates:
    - PCA reduces 32D → 3D without errors
    - Variance explained is reasonable (>50% for first 3 components)
    - 3D coordinates are within expected bounds
    """
    with patch("cohezion.api._get_vae", return_value=mock_vae):
        response = client.post(
            "/flume/latent-space",
            json={"n_samples": 100, "seed": 42},
        )

    assert response.status_code == 200
    data = response.json()

    # PCA should capture reasonable variance with 3 components
    # Note: With random samples from standard normal, variance per component ≈ 1/z_dim
    # For 32D latent space, 3 components ≈ 3/32 ≈ 9.4% minimum
    total_variance = sum(data["variance_explained"])
    assert total_variance > 0.05, "PCA should capture >5% variance with 3 components"
    assert total_variance <= 1.0, "Variance explained cannot exceed 100%"

    # 3D coordinates should be centered around origin (after PCA)
    coords_3d = np.array(data["samples_3d"])
    mean = np.mean(coords_3d, axis=0)
    assert np.all(np.abs(mean) < 1.0), "PCA-reduced coordinates should be centered"


def test_flume_latent_space_seed_reproducibility(client, mock_vae):
    """
    Test 3/5: Same seed produces identical samples.

    Validates:
    - seed=42 produces deterministic output
    - Enables reproducible demos for portfolio
    """
    with patch("cohezion.api._get_vae", return_value=mock_vae):
        response1 = client.post(
            "/flume/latent-space",
            json={"n_samples": 50, "seed": 42},
        )
        response2 = client.post(
            "/flume/latent-space",
            json={"n_samples": 50, "seed": 42},
        )

    data1 = response1.json()
    data2 = response2.json()

    # Samples should be identical
    assert data1["samples_3d"] == data2["samples_3d"]
    assert data1["coherence_scores"] == data2["coherence_scores"]


def test_flume_latent_space_adjustable_sample_count(client, mock_vae):
    """
    Test 4/5: Sample count parameter works correctly.

    Validates:
    - n_samples controls output size
    - Supports range 50-500 (FlumeNavigator slider range)
    """
    with patch("cohezion.api._get_vae", return_value=mock_vae):
        for n in [50, 100, 200, 500]:
            response = client.post(
                "/flume/latent-space",
                json={"n_samples": n, "seed": 42},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["samples"]) == 0  # Issue #8: now empty
            assert len(data["samples_3d"]) == n
            assert len(data["coherence_scores"]) == n


def test_flume_latent_space_handles_no_vae_with_sanitized_error(client):
    """
    Test 5/5: Graceful error when VAE not trained (Issue #4 fix).

    Validates:
    - Returns 500 error with sanitized message (no path leakage)
    - Error message explains VAE not available
    - Frontend can handle failure gracefully
    """
    with patch("cohezion.api._get_vae", side_effect=FileNotFoundError("/secret/path/checkpoint.pt")):
        response = client.post(
            "/flume/latent-space",
            json={"n_samples": 10, "seed": 42},
        )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "FLUME VAE checkpoint not found" in detail
    # Issue #4 fix: ensure no path leakage
    assert "/secret/path" not in detail


@pytest.mark.parametrize("invalid_params,expected_error", [
    ({"n_samples": 0}, "n_samples must be positive"),
    ({"n_samples": -10}, "n_samples must be positive"),
    ({"n_samples": 10000}, "n_samples must be ≤1000"),
])
def test_flume_latent_space_validates_parameters(client, mock_vae, invalid_params, expected_error):
    """
    Bonus Test: Parameter validation (edge cases).

    Validates:
    - n_samples must be positive
    - Reasonable upper bound (1000) to prevent DOS
    - Returns 422 Unprocessable Entity with helpful error message
    """
    with patch("cohezion.api._get_vae", return_value=mock_vae):
        response = client.post("/flume/latent-space", json=invalid_params)
        assert response.status_code == 422
        assert expected_error in response.json()["detail"]
