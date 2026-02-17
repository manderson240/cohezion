"""Torch Dataset that encodes execution experiences as 256D vectors.

Compatible with ``FlumeVAETrainer.train(dataset=...)`` — each sample
is a ``torch.Tensor`` of shape ``(256,)``.
"""

from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset

from cohezion.flume.experience_encoder import TOTAL_DIM, ExperienceEncoder


class ExperienceDataset(Dataset):
    """Pre-encoded experience dataset for FLUME VAE training.

    Parameters
    ----------
    experiences : list[dict]
        Raw experience dicts (see ExperienceEncoder for schema).
    seed : int
        RNG seed for reproducibility.
    augment : bool
        If True, add small gaussian noise for regularization.
    augment_std : float
        Standard deviation of augmentation noise.
    """

    def __init__(
        self,
        experiences: list[dict],
        seed: int = 42,
        augment: bool = False,
        augment_std: float = 0.01,
    ) -> None:
        self._encoder = ExperienceEncoder()
        self._augment = augment
        self._augment_std = augment_std
        self._rng = np.random.default_rng(seed)

        # Pre-encode all experiences at init for fast __getitem__
        self._vectors = (
            np.stack([self._encoder.encode(exp) for exp in experiences])
            if experiences
            else np.empty((0, TOTAL_DIM), dtype=np.float32)
        )

    def __len__(self) -> int:
        return len(self._vectors)

    def __getitem__(self, idx: int) -> torch.Tensor:
        vec = self._vectors[idx].copy()
        if self._augment:
            noise = self._rng.normal(0.0, self._augment_std, vec.shape).astype(np.float32)
            vec = vec + noise
        return torch.from_numpy(vec)
