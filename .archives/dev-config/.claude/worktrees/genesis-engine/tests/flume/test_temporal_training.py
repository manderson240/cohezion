"""Tests for TemporalVAE training pipeline."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")

STEP_DIM = 29


def _synthetic_jsonl(n_sessions: int, steps_per_session: int, tmp_path: Path) -> Path:
    """Write a minimal journeys.jsonl for testing."""
    rng = np.random.RandomState(42)
    path = tmp_path / "journeys.jsonl"
    with open(path, "w") as f:
        for s in range(n_sessions):
            for step in range(steps_per_session):
                traj = rng.randn(12).tolist()
                f.write(
                    json.dumps(
                        {
                            "id": f"s{s}_{step}",
                            "session_id": f"session_{s}",
                            "iteration": step,
                            "skill": "RETROSPECTIVE_SKILL",
                            "coherence": float(rng.uniform(0.5, 0.75)),
                            "novelty": 0.5,
                            "improvement": 1.0,
                            "trajectory": traj,
                        }
                    )
                    + "\n"
                )
    return path


class TestTemporalVAELoss:
    """Test loss function correctness."""

    def test_loss_returns_dict_with_expected_keys(self) -> None:
        """temporal_vae_loss() returns dict with total, recon, kl."""
        import torch

        from scripts.train_temporal_vae import temporal_vae_loss

        B, T = 4, 10
        recon = torch.randn(B, T, STEP_DIM)
        target = torch.randn(B, T, STEP_DIM)
        mu = torch.randn(B, 256)
        logvar = torch.zeros(B, 256)

        losses = temporal_vae_loss(recon, target, mu, logvar, beta=1.0)
        assert "total" in losses
        assert "recon" in losses
        assert "kl" in losses

    def test_loss_is_nonnegative(self) -> None:
        """Total loss is ≥ 0."""
        import torch

        from scripts.train_temporal_vae import temporal_vae_loss

        B, T = 4, 10
        recon = torch.randn(B, T, STEP_DIM)
        target = torch.randn(B, T, STEP_DIM)
        mu = torch.randn(B, 256)
        logvar = torch.zeros(B, 256)

        losses = temporal_vae_loss(recon, target, mu, logvar, beta=0.1)
        assert losses["total"].item() >= 0

    def test_kl_is_zero_for_standard_normal(self) -> None:
        """KL = 0 when mu=0, logvar=0 (standard normal posterior)."""
        import torch

        from scripts.train_temporal_vae import temporal_vae_loss

        B, T = 4, 10
        recon = target = torch.zeros(B, T, STEP_DIM)
        mu = torch.zeros(B, 256)
        logvar = torch.zeros(B, 256)

        losses = temporal_vae_loss(recon, target, mu, logvar, beta=1.0)
        assert abs(losses["kl"].item()) < 1e-5

    def test_padding_mask_excludes_padded_positions(self) -> None:
        """Recon loss ignores padded positions when mask is all True (all padding)."""
        import torch

        from scripts.train_temporal_vae import temporal_vae_loss

        B, T = 2, 5
        # Large reconstruction error in positions 2-4
        recon = torch.zeros(B, T, STEP_DIM)
        target = torch.zeros(B, T, STEP_DIM)
        target[:, 2:] = 100.0  # big error in padded positions

        mask_none = torch.zeros(B, T, dtype=torch.bool)  # no padding
        mask_pad = torch.zeros(B, T, dtype=torch.bool)
        mask_pad[:, 2:] = True  # positions 2-4 are padding

        loss_none = temporal_vae_loss(recon, target, torch.zeros(B, 256), torch.zeros(B, 256), padding_mask=mask_none)
        loss_pad = temporal_vae_loss(recon, target, torch.zeros(B, 256), torch.zeros(B, 256), padding_mask=mask_pad)

        # With padding masked, loss should be lower
        assert loss_pad["recon"].item() < loss_none["recon"].item()


class TestTemporalVAETrainFunction:
    """Smoke-test the train() function end-to-end."""

    def test_train_completes_and_returns_metrics(self, tmp_path: Path) -> None:
        """train() runs without error and returns a dict with 'total' key."""
        from scripts.train_temporal_vae import train

        data_path = _synthetic_jsonl(n_sessions=4, steps_per_session=10, tmp_path=tmp_path)
        metrics = train(
            data_path=data_path,
            epochs=2,
            batch_size=4,
            max_seq_len=10,
            checkpoint_dir=tmp_path / "checkpoints",
        )
        assert "total" in metrics
        assert metrics["total"] >= 0

    def test_train_saves_checkpoint(self, tmp_path: Path) -> None:
        """train() saves a checkpoint file after training."""
        from scripts.train_temporal_vae import train

        data_path = _synthetic_jsonl(n_sessions=4, steps_per_session=10, tmp_path=tmp_path)
        ckpt_dir = tmp_path / "checkpoints"
        train(
            data_path=data_path,
            epochs=2,
            batch_size=4,
            max_seq_len=10,
            checkpoint_dir=ckpt_dir,
        )
        assert (ckpt_dir / "temporal_vae_best.pt").exists()

    def test_checkpoint_loadable(self, tmp_path: Path) -> None:
        """Saved checkpoint can be loaded and used to restore model state."""
        import torch

        from cohezion.flume.temporal_encoder import TemporalDecoder, TemporalEncoder
        from scripts.train_temporal_vae import train

        data_path = _synthetic_jsonl(n_sessions=4, steps_per_session=10, tmp_path=tmp_path)
        ckpt_dir = tmp_path / "checkpoints"
        train(
            data_path=data_path,
            epochs=2,
            batch_size=4,
            max_seq_len=10,
            checkpoint_dir=ckpt_dir,
        )

        ckpt = torch.load(ckpt_dir / "temporal_vae_best.pt", weights_only=True)
        enc = TemporalEncoder()
        dec = TemporalDecoder()
        enc.load_state_dict(ckpt["encoder_state_dict"])
        dec.load_state_dict(ckpt["decoder_state_dict"])

        # Verify loaded model produces correct output shape
        enc.eval()
        dec.eval()
        x = torch.randn(2, 10, 29)
        mu, _ = enc.encode(x)
        recon = dec.decode(mu, x)
        assert recon.shape == x.shape
