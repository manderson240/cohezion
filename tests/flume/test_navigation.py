import pytest
import torch

from cohezion.flume.navigation import lerp, similarity_score, slerp


def test_lerp_basic():
    """Test linear interpolation."""
    z1 = torch.tensor([0.0, 0.0])
    z2 = torch.tensor([1.0, 1.0])
    
    # Midpoint
    res = lerp(z1, z2, 0.5)
    assert torch.allclose(res, torch.tensor([0.5, 0.5]))
    
    # Start point
    res = lerp(z1, z2, 0.0)
    assert torch.allclose(res, z1)
    
    # End point
    res = lerp(z1, z2, 1.0)
    assert torch.allclose(res, z2)

def test_slerp_basic():
    """Test spherical linear interpolation."""
    # Two orthogonal unit vectors
    z1 = torch.tensor([1.0, 0.0])
    z2 = torch.tensor([0.0, 1.0])
    
    # Midpoint should be at 45 degrees
    res = slerp(z1, z2, 0.5)
    expected = torch.tensor([0.7071, 0.7071]) # 1/sqrt(2)
    assert torch.allclose(res, expected, atol=1e-4)
    
    # Start and end
    assert torch.allclose(slerp(z1, z2, 0.0), z1)
    assert torch.allclose(slerp(z1, z2, 1.0), z2)

def test_slerp_identical_vectors():
    """Slerp between identical vectors should return the vector."""
    z1 = torch.tensor([1.0, 0.0])
    res = slerp(z1, z1, 0.5)
    assert torch.allclose(res, z1)

def test_similarity_score():
    """Test distance-based similarity metric."""
    z1 = torch.tensor([1.0, 0.0])
    z2 = torch.tensor([1.0, 0.0]) # Identical
    z3 = torch.tensor([-1.0, 0.0]) # Opposite
    
    # Identical should be 1.0
    assert similarity_score(z1, z2) == pytest.approx(1.0)
    
    # Opposite should be 0.0
    assert similarity_score(z1, z3) == pytest.approx(0.0)
    
    # Orthogonal should be 0.5
    z4 = torch.tensor([0.0, 1.0])
    assert similarity_score(z1, z4) == pytest.approx(0.5)
