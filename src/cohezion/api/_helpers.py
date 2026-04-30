"""Shared helpers for the api package — VAE / RL / coherence singletons.

These were originally module-level in ``cohezion/api/__init__.py``. They are
re-exported from there for backward compatibility (tests patch
``cohezion.api._get_vae`` directly, and ``conftest`` resets
``cohezion.api._vae_trainer``/``_rl_policy``).

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


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


def get_vae():
    """Lazy-load the trained FLUME VAE (singleton).

    Reads/writes ``cohezion.api._vae_trainer`` so tests that monkeypatch the
    attribute on the package keep working.
    """
    import cohezion.api as api_module

    if getattr(api_module, "_vae_trainer", None) is None:
        import torch

        from cohezion.flume.training import FlumeVAETrainer

        trainer = FlumeVAETrainer()
        ckpt_path = Path("data/flume/checkpoints/flume_vae_ep50.pt")
        if ckpt_path.exists():
            try:
                ckpt = torch.load(ckpt_path, weights_only=True)
                trainer.encoder.load_state_dict(ckpt["encoder"])
                trainer.mu_head.load_state_dict(ckpt["mu_head"])
                trainer.logvar_head.load_state_dict(ckpt["logvar_head"])
                trainer.decoder.load_state_dict(ckpt["decoder"])
                logger.info("Loaded FLUME VAE checkpoint: %s", ckpt_path)
            except (RuntimeError, KeyError) as e:
                logger.warning(
                    (
                        "Failed to load FLUME VAE checkpoint %s (architecture mismatch?); using "
                        "random weights: %s"
                    ),
                    ckpt_path,
                    str(e),
                )
        else:
            logger.warning("No FLUME VAE checkpoint found at %s; using random weights", ckpt_path)
        api_module._vae_trainer = trainer
    return api_module._vae_trainer


def get_rl_policy():
    """Lazy-load the trained RL policy singleton.

    Reads/writes ``cohezion.api._rl_policy`` for the same reason as
    :func:`get_vae`.
    """
    import cohezion.api as api_module

    if getattr(api_module, "_rl_policy", None) is None:
        import torch

        from cohezion.rl.trainer import PolicyNetwork

        policy = PolicyNetwork(state_dim=256, action_dim=256, hidden=128)
        ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
        if ckpt_path.exists():
            policy.load_state_dict(torch.load(ckpt_path, map_location="cpu", weights_only=True))
            policy.eval()
            logger.info("Loaded RL policy from %s", ckpt_path)
        else:
            logger.warning("No RL checkpoint at %s — using random policy", ckpt_path)
        api_module._rl_policy = policy
    return api_module._rl_policy


__all__ = ["compute_coherence", "contextlib", "get_rl_policy", "get_vae"]
