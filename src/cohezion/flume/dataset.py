"""Dataset classes for FLUME autoencoder training.

Loads latent trajectories from mass simulation checkpoints
for training the VAE encoder/decoder.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


logger = logging.getLogger(__name__)


class FlumeTrajectoryDataset(Dataset):
    """Load mass sim checkpoint trajectories as training data.

    Each sample is a 256D latent vector from a simulation checkpoint.
    The dataset loads JSONL artifacts or numpy arrays from the mass sim
    output directory.

    Parameters
    ----------
    data_dir : str or Path
        Directory containing mass sim artifacts.
    max_samples : int
        Maximum number of samples to load (default 100000).
    z_dim : int
        Expected latent dimensionality (default 256).
    """

    def __init__(
        self,
        data_dir: str | Path = "data/mass_sim/artifacts",
        max_samples: int = 100_000,
        z_dim: int = 256,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.z_dim = z_dim
        self.vectors: list[np.ndarray] = []

        self._load_data(max_samples)
        logger.info(f"Loaded {len(self.vectors)} trajectory samples from {data_dir}")

    def _load_data(self, max_samples: int) -> None:
        """Load data from available sources."""
        # Try numpy checkpoints first
        npy_files = sorted(self.data_dir.glob("**/*.npy"))
        for npy_file in npy_files:
            if len(self.vectors) >= max_samples:
                break
            try:
                data = np.load(npy_file)
                if data.ndim == 2 and data.shape[1] == self.z_dim:
                    for row in data:
                        self.vectors.append(row.astype(np.float32))
                        if len(self.vectors) >= max_samples:
                            break
            except Exception as e:
                logger.debug(f"Skipping {npy_file}: {e}")

        # Fall back to JSONL checkpoints
        if not self.vectors:
            jsonl_files = sorted(self.data_dir.glob("**/*.jsonl"))
            for jsonl_file in jsonl_files:
                if len(self.vectors) >= max_samples:
                    break
                try:
                    with open(jsonl_file) as f:
                        for line in f:
                            record = json.loads(line)
                            if "latent" in record:
                                vec = np.array(record["latent"], dtype=np.float32)
                                if vec.shape == (self.z_dim,):
                                    self.vectors.append(vec)
                except Exception as e:
                    logger.debug(f"Skipping {jsonl_file}: {e}")

        # Generate synthetic data if nothing loaded (for initial training)
        if not self.vectors:
            logger.warning("No training data found. Generating synthetic samples.")
            rng = np.random.default_rng(42)
            n_synthetic = min(max_samples, 10000)
            for _ in range(n_synthetic):
                # Samples centered near HIHO target with varied spread
                vec = rng.normal(0.5, 0.15, (self.z_dim,)).astype(np.float32)
                self.vectors.append(vec)

    def __len__(self) -> int:
        return len(self.vectors)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return torch.from_numpy(self.vectors[idx])


class SyntheticFlumeDataset(Dataset):
    """Generate synthetic FLUME training data on the fly.

    Creates normally distributed latent vectors centered at HIHO target.
    Useful for bootstrapping training before real sim data is available.

    Parameters
    ----------
    n_samples : int
        Number of samples (default 10000).
    z_dim : int
        Latent dimension (default 256).
    seed : int
        RNG seed (default 42).
    """

    def __init__(self, n_samples: int = 10000, z_dim: int = 256, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self.data = rng.normal(0.5, 0.15, (n_samples, z_dim)).astype(np.float32)

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> torch.Tensor:
        return torch.from_numpy(self.data[idx])


class RealSkillStateDataset(SyntheticFlumeDataset):
    """Load skill-state latent vectors from SurrealDB.

    Falls back to SyntheticFlumeDataset when SurrealDB is unreachable.
    Gaussian augmentation is applied only to continuous dims [0:29];
    the SHA-256 fingerprint region [29:256] is kept bit-exact.
    """

    def __init__(
        self,
        *,
        surreal_url: str = "ws://localhost:8001",
        n_fallback: int = 10000,
        z_dim: int = 256,
        seed: int = 42,
        augment_sigma: float = 0.01,
    ) -> None:
        raise NotImplementedError
