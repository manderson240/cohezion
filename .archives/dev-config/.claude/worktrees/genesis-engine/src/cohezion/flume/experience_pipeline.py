"""End-to-end pipeline: collect experiences -> encode -> train FLUME VAE.

Orchestrates ExperienceCollector, ExperienceDataset, and FlumeVAETrainer
with graceful synthetic fallback when real data is insufficient.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cohezion.flume.experience_collector import ExperienceCollector
from cohezion.flume.experience_dataset import ExperienceDataset
from cohezion.flume.training import FlumeVAETrainer, TrainConfig


logger = logging.getLogger(__name__)


class ExperienceTrainingPipeline:
    """Collect real experiences, encode as 256D, and train the FLUME VAE.

    Parameters
    ----------
    collector : ExperienceCollector or None
        Custom collector; uses default if None.
    """

    def __init__(self, collector: ExperienceCollector | None = None) -> None:
        self.collector = collector or ExperienceCollector()

    async def run(
        self,
        min_real: int = 10,
        max_samples: int = 10_000,
        epochs: int = 50,
        batch_size: int = 64,
        lr: float = 1e-3,
        seed: int = 42,
        synthetic_fallback: bool = True,
        checkpoint_dir: str = "data/flume/checkpoints",
    ) -> Path:
        """Run the full experience -> VAE training pipeline.

        Parameters
        ----------
        min_real : int
            Minimum real experiences required. If fewer are found and
            ``synthetic_fallback`` is True, pad with synthetic data.
        max_samples : int
            Maximum total samples for training.
        epochs : int
            Training epochs.
        batch_size : int
            Batch size for DataLoader.
        lr : float
            Learning rate.
        seed : int
            RNG seed for reproducibility.
        synthetic_fallback : bool
            If True and real data < min_real, pad with synthetic data.
        checkpoint_dir : str
            Directory for saving model checkpoints.

        Returns
        -------
        Path
            Path to the final checkpoint file.
        """
        # --- Step 1: Collect real experiences ---
        logger.info("Collecting real experiences...")
        experiences = self.collector.collect_all(max_samples=max_samples)
        n_real = len(experiences)
        logger.info("Found %d real experience records", n_real)

        # --- Step 2: Synthetic fallback if needed ---
        if n_real < min_real and synthetic_fallback:
            n_synthetic = max_samples - n_real
            logger.info(
                "Real data (%d) < min_real (%d), padding with %d synthetic samples",
                n_real,
                min_real,
                n_synthetic,
            )
            experiences.extend(self._generate_synthetic(n_synthetic, seed))
        elif n_real < min_real and not synthetic_fallback:
            msg = (
                f"Only {n_real} real experiences found (need {min_real}). "
                "Set synthetic_fallback=True to pad with synthetic data."
            )
            raise ValueError(msg)

        # --- Step 3: Build dataset ---
        dataset = ExperienceDataset(experiences, seed=seed)
        logger.info("Dataset ready: %d samples", len(dataset))

        # --- Step 4: Train ---
        config = TrainConfig(
            z_dim=256,
            batch_size=min(batch_size, len(dataset)),
            epochs=epochs,
            lr=lr,
            checkpoint_dir=checkpoint_dir,
        )
        trainer = FlumeVAETrainer(config)
        metrics = trainer.train(dataset=dataset)

        # --- Step 5: Report ---
        final_epoch = metrics[-1] if metrics else {}
        logger.info(
            "Training complete. Final loss: %.4f | Real samples: %d | Total: %d",
            final_epoch.get("total", float("nan")),
            n_real,
            len(dataset),
        )

        checkpoint_path = Path(checkpoint_dir) / f"flume_vae_ep{epochs}.pt"
        return checkpoint_path

    @staticmethod
    def _generate_synthetic(count: int, seed: int) -> list[dict]:
        """Generate synthetic experience dicts with gaussian noise."""
        import numpy as np

        rng = np.random.default_rng(seed)
        op_types = ("generate", "analyze", "search", "transform", "persist")
        records = []
        for i in range(count):
            records.append(
                {
                    "trajectory": rng.normal(0.5, 0.15, 12).astype(np.float32),
                    "mission_id": f"synthetic_{i}",
                    "agent_id": "synthetic",
                    "skill_name": "synthetic",
                    "operation_type": op_types[i % len(op_types)],
                    "phi_score": float(rng.uniform(0.3, 0.95)),
                    "cache_hit_rate": float(rng.uniform(0.0, 1.0)),
                    "success": float(rng.choice([0.0, 1.0])),
                }
            )
        return records
