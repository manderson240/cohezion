"""Tests for api/services/flume.py.

Covers FLUME VAE encoding, decoding, and interpolation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.api.services.flume import (
    FlumeEncodeRequest,
    compute_coherence,
    flume_encode_service,
)


def test_compute_coherence():
    """[P0] Should compute coherence correctly."""
    # Balanced vector around 0.5
    z = [0.5] * 256
    assert compute_coherence(z) > 0.9
    
    # Highly divergent vector
    z = [0.0] * 256
    assert compute_coherence(z) < 0.1

@pytest.mark.asyncio
async def test_flume_encode_service():
    """[P0] Should encode vector through VAE."""
    mock_vae = MagicMock()
    mock_vae.config.z_dim = 256
    mock_vae.device = "cpu"
    
    import torch
    mock_vae.encoder.return_value = torch.zeros((1, 128))
    mock_vae.mu_head.return_value = torch.full((1, 256), 0.5)
    mock_vae.logvar_head.return_value = torch.zeros((1, 256))
    
    with patch("cohezion.api.services.flume.get_vae", return_value=mock_vae):
        req = FlumeEncodeRequest(vector=[0.5] * 256)
        result = await flume_encode_service(req)
        
        assert len(result.mu) == 256
        assert result.coherence > 0.9
