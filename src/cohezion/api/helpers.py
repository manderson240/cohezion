"""Helper functions for Cohezion API endpoints."""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)

_vae_trainer = None
_rl_policy = None


def get_vae():
    """Lazy-load the trained FLUME VAE (singleton)."""
    global _vae_trainer
    if _vae_trainer is None:
        import torch

        from cohezion.flume.training import FlumeVAETrainer

        _vae_trainer = FlumeVAETrainer()
        ckpt_path = Path("data/flume/checkpoints/flume_vae_ep50.pt")
        if ckpt_path.exists():
            try:
                ckpt = torch.load(ckpt_path, weights_only=True)
                _vae_trainer.encoder.load_state_dict(ckpt["encoder"])
                _vae_trainer.mu_head.load_state_dict(ckpt["mu_head"])
                _vae_trainer.logvar_head.load_state_dict(ckpt["logvar_head"])
                _vae_trainer.decoder.load_state_dict(ckpt["decoder"])
                logger.info("Loaded FLUME VAE checkpoint: %s", ckpt_path)
            except (RuntimeError, KeyError) as e:
                msg = (
                    f"Failed to load FLUME VAE checkpoint {ckpt_path} (mismatch?); "
                    f"using random weights: {e}"
                )
                logger.warning(msg)
        else:
            logger.warning(
                "No FLUME VAE checkpoint found at %s; using random weights", ckpt_path
            )
    return _vae_trainer


def compute_coherence(z: list[float], z_dim: int = 256) -> float:
    """Compute HIHO coherence: 1.0 at mean=0.5, decays with variance."""
    import numpy as np

    arr = np.array(z)
    n_chunks = min(12, z_dim)
    chunk_size = z_dim // n_chunks
    variance_sum = 0.0

    for c in range(n_chunks):
        start = c * chunk_size
        end = (c + 1) * chunk_size if c < n_chunks - 1 else z_dim
        chunk_mean = float(np.mean(arr[start:end]))
        variance_sum += (chunk_mean - 0.5) ** 2

    variance = variance_sum / n_chunks
    return max(0.0, 1.0 - min(variance * 4.0, 1.0))


def get_rl_policy():
    """Lazy-load the trained RL policy singleton."""
    global _rl_policy
    if _rl_policy is None:
        import torch

        from cohezion.rl.trainer import PolicyNetwork

        _rl_policy = PolicyNetwork(state_dim=256, action_dim=256, hidden=128)
        ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
        if ckpt_path.exists():
            _rl_policy.load_state_dict(
                torch.load(ckpt_path, map_location="cpu", weights_only=True)
            )
            _rl_policy.eval()
            logger.info("Loaded RL policy from %s", ckpt_path)
        else:
            logger.warning("No RL checkpoint at %s — using random policy", ckpt_path)
    return _rl_policy


def reset_vae() -> None:
    """Reset VAE singleton (for testing)."""
    global _vae_trainer
    _vae_trainer = None


def reset_rl_policy() -> None:
    """Reset RL policy singleton (for testing)."""
    global _rl_policy
    _rl_policy = None


# Note: set_token_client moved to routes_metrics to avoid circular import
