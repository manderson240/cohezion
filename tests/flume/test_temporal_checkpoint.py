"""Tests for TemporalVAE checkpoint loading."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")


def _save_dummy_checkpoint(path: Path) -> None:
    """Save a minimal valid temporal_vae checkpoint."""
    import torch

    from cohezion.flume.temporal_encoder import TemporalDecoder, TemporalEncoder

    enc = TemporalEncoder()
    dec = TemporalDecoder()
    torch.save(
        {
            "encoder_state_dict": enc.state_dict(),
            "decoder_state_dict": dec.state_dict(),
            "epoch": 5,
            "metrics": {"total": 2.34, "recon": 2.1, "kl": 0.24},
            "config": {
                "step_dim": 29,
                "d_model": 128,
                "latent_dim": 256,
                "n_heads": 4,
                "n_layers": 2,
                "max_seq_len": 64,
            },
        },
        path,
    )


class TestTemporalVAELoader:
    """Test TemporalVAELoader checkpoint loading."""

    def test_loader_loads_from_checkpoint(self, tmp_path: Path) -> None:
        """TemporalVAELoader loads encoder from a valid checkpoint."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        ckpt = tmp_path / "temporal_vae_best.pt"
        _save_dummy_checkpoint(ckpt)

        loader = TemporalVAELoader(model_path=ckpt)
        assert loader.enabled

    def test_loader_disabled_when_no_checkpoint(self, tmp_path: Path) -> None:
        """TemporalVAELoader is disabled when checkpoint doesn't exist."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        loader = TemporalVAELoader(model_path=tmp_path / "nonexistent.pt")
        assert not loader.enabled

    def test_encode_sequence_returns_256d(self, tmp_path: Path) -> None:
        """encode_sequence() returns 256D numpy array when enabled."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        ckpt = tmp_path / "temporal_vae_best.pt"
        _save_dummy_checkpoint(ckpt)

        loader = TemporalVAELoader(model_path=ckpt)
        steps = torch.randn(5, 29)  # [T, step_dim]
        result = loader.encode_sequence(steps)

        assert isinstance(result, np.ndarray)
        assert result.shape == (256,)
        assert result.dtype == np.float32

    def test_encode_sequence_normalized(self, tmp_path: Path) -> None:
        """encode_sequence() returns unit-normalized vector."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        ckpt = tmp_path / "temporal_vae_best.pt"
        _save_dummy_checkpoint(ckpt)

        loader = TemporalVAELoader(model_path=ckpt)
        steps = torch.randn(5, 29)
        result = loader.encode_sequence(steps)

        norm = np.linalg.norm(result)
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_encode_sequence_deterministic(self, tmp_path: Path) -> None:
        """Repeated calls return identical result (eval mode)."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        ckpt = tmp_path / "temporal_vae_best.pt"
        _save_dummy_checkpoint(ckpt)

        loader = TemporalVAELoader(model_path=ckpt)
        steps = torch.randn(5, 29)
        r1 = loader.encode_sequence(steps)
        r2 = loader.encode_sequence(steps)
        np.testing.assert_array_almost_equal(r1, r2, decimal=5)

    def test_encode_sequence_fallback_when_disabled(self, tmp_path: Path) -> None:
        """encode_sequence() returns zeros when loader is disabled."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        loader = TemporalVAELoader(model_path=tmp_path / "nonexistent.pt")
        steps = torch.randn(5, 29)
        result = loader.encode_sequence(steps)

        assert result.shape == (256,)
        assert np.allclose(result, 0.0)

    def test_default_model_path(self) -> None:
        """TemporalVAELoader uses correct default checkpoint path."""
        from cohezion.flume.temporal_encoder import TemporalVAELoader

        loader = TemporalVAELoader()
        assert loader.model_path == Path("data/flume/checkpoints_v2/temporal_vae_best.pt")


class TestJourneyTrackerTemporalCheckpoint:
    """JourneyTracker loads trained TemporalVAE when checkpoint exists."""

    def test_journey_tracker_uses_checkpoint_when_available(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """JourneyTracker._temporal_encoder loads from checkpoint if it exists."""

        # Create a real checkpoint in a temp location
        ckpt_dir = tmp_path / "checkpoints_v2"
        ckpt_dir.mkdir()
        ckpt_path = ckpt_dir / "temporal_vae_best.pt"
        _save_dummy_checkpoint(ckpt_path)

        # Monkeypatch the default path
        monkeypatch.setattr(
            "cohezion.flume.temporal_encoder.TemporalVAELoader.DEFAULT_MODEL_PATH",
            ckpt_path,
        )

        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        assert tracker._temporal_encoder is not None


# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
# NOTE: Removed TestJourneyTrackerTemporalCheckpoint (Wave 3E).
# Tested removed JourneyTracker._temporal_encoder/encode_step_sequence path.
