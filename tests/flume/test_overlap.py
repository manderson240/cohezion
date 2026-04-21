import pytest
import torch
from cohezion.flume.overlap import calculate_geometric_overlap

def test_calculate_geometric_overlap():
    """Verify that geometric overlap correctly computes L2 distance."""
    # [12D vectors]
    latent_state = torch.tensor([0.1] * 12)
    universe_state = torch.tensor([0.2] * 12)
    
    # Expected L2 distance: sqrt(12 * (0.1^2)) = sqrt(12 * 0.01) = sqrt(0.12)
    expected_dist = torch.sqrt(torch.tensor(0.12)).item()
    
    result = calculate_geometric_overlap(latent_state, universe_state)
    assert pytest.approx(result["l2_distance"], 1e-5) == expected_dist
    assert "coherence_match" in result

def test_calculate_geometric_overlap_different_shapes():
    """Verify that different shapes raise error."""
    latent = torch.tensor([0.1] * 12)
    universe = torch.tensor([0.2] * 11)
    
    with pytest.raises(ValueError):
        calculate_geometric_overlap(latent, universe)
