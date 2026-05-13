"""Training loop for the JourneyToFlumeEncoder.

Given a batch of AgentTrajectory records (from UniverseFactory.run), train the
journey-VAE end-to-end: encode → sample z → decode → minimize MSE + β·KL.
Emits a TRAINING_CHECKPOINT precipitation event every checkpoint_every steps
so the PrecipitationOrchestrator (Phase 4) observes training progress.

Example:
    from cohezion.flume.train import FlumeTrainConfig, train_flume_on_journeys

    config = FlumeTrainConfig(epochs=3, batch_size=4, checkpoint_every=50)
    ckpt_path = train_flume_on_journeys(trajectories, config=config)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset

from cohezion.precipitation import PrecipitationEvent, PrecipitationKind, emit
from cohezion.universe.llm_training_bridge import AgentTrajectory

from .journey_encoder import (
    JourneyEncoderConfig,
    JourneyToFlumeEncoder,
    _trajectory_to_tensor,
    compute_journey_vae_loss,
    save_checkpoint,
)


logger = logging.getLogger(__name__)


@dataclass
class FlumeTrainConfig:
    """Configuration for the journey-VAE training loop."""

    epochs: int = 3
    batch_size: int = 4
    lr: float = 1e-4
    kl_weight: float = 0.1
    checkpoint_every: int = 100  # steps (not epochs)
    output_dir: Path = Path("models/flume")
    max_seq_len: int = 128
    # Device default is "cpu" on purpose: this Cohezion hardware (Ryzen AI MAX+ 395 iGPU)
    # has flaky torch CUDA detection that can segfault on .to('cuda'). Callers who
    # know their hardware can override explicitly.
    device: str = "cpu"
    universe_id_for_events: str = "flume-training"  # attached to emitted events

    def resolve_device(self) -> str:
        return self.device


class JourneyDataset(Dataset):
    """Wrap a list of AgentTrajectory as a PyTorch Dataset."""

    def __init__(self, trajectories: list[AgentTrajectory], max_seq_len: int) -> None:
        self.trajectories = trajectories
        self.max_seq_len = max_seq_len

    def __len__(self) -> int:
        return len(self.trajectories)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        features, mask = _trajectory_to_tensor(self.trajectories[idx], self.max_seq_len)
        return features, mask


def train_flume_on_journeys(
    trajectories: list[AgentTrajectory],
    config: FlumeTrainConfig | None = None,
    encoder: JourneyToFlumeEncoder | None = None,
) -> Path:
    """Train (or continue-training) a JourneyToFlumeEncoder on trajectory data.

    Returns the path to the final checkpoint.
    """
    config = config or FlumeTrainConfig()
    device = config.resolve_device()
    encoder = encoder or JourneyToFlumeEncoder(JourneyEncoderConfig(max_seq_len=config.max_seq_len))
    encoder.to(device).train()

    dataset = JourneyDataset(trajectories, max_seq_len=config.max_seq_len)
    loader = DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=True,
        drop_last=False,
    )
    optimizer = torch.optim.Adam(encoder.parameters(), lr=config.lr)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    global_step = 0
    last_checkpoint_path: Path | None = None

    for epoch in range(config.epochs):
        epoch_total = 0.0
        epoch_recon = 0.0
        epoch_kl = 0.0
        batches = 0
        for features, mask in loader:
            features = features.to(device)
            mask = mask.to(device)

            recon, mu, log_var, _z = encoder(features, mask)
            total_loss, recon_loss, kl_loss = compute_journey_vae_loss(
                recon,
                features,
                mask,
                mu,
                log_var,
                kl_weight=config.kl_weight,
            )
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

            epoch_total += float(total_loss.detach().cpu())
            epoch_recon += float(recon_loss.detach().cpu())
            epoch_kl += float(kl_loss.detach().cpu())
            batches += 1
            global_step += 1

            if global_step % config.checkpoint_every == 0:
                last_checkpoint_path = _save_and_emit(
                    encoder=encoder,
                    config=config,
                    step=global_step,
                    epoch=epoch,
                    loss=float(total_loss.detach().cpu()),
                    recon=float(recon_loss.detach().cpu()),
                    kl=float(kl_loss.detach().cpu()),
                )

        logger.info(
            "flume-vae epoch=%d batches=%d total=%.4f recon=%.4f kl=%.4f",
            epoch,
            batches,
            epoch_total / max(1, batches),
            epoch_recon / max(1, batches),
            epoch_kl / max(1, batches),
        )

    # Always save a final checkpoint even if we never hit checkpoint_every.
    last_checkpoint_path = _save_and_emit(
        encoder=encoder,
        config=config,
        step=global_step,
        epoch=config.epochs - 1,
        loss=epoch_total / max(1, batches),
        recon=epoch_recon / max(1, batches),
        kl=epoch_kl / max(1, batches),
        final=True,
    )
    return last_checkpoint_path


def _save_and_emit(
    *,
    encoder: JourneyToFlumeEncoder,
    config: FlumeTrainConfig,
    step: int,
    epoch: int,
    loss: float,
    recon: float,
    kl: float,
    final: bool = False,
) -> Path:
    """Save checkpoint to disk and emit TRAINING_CHECKPOINT precipitation event."""
    tag = "final" if final else f"step{step}"
    path = config.output_dir / f"journey-encoder-{tag}.pt"
    save_checkpoint(
        encoder,
        path,
        metadata={
            "step": step,
            "epoch": epoch,
            "loss": loss,
            "recon_loss": recon,
            "kl_loss": kl,
            "final": final,
        },
    )
    try:
        # Map training loss to a pseudo-coherence in [0, 1]: higher loss = lower coherence.
        pseudo_coherence = max(0.0, min(1.0, 1.0 / (1.0 + loss)))
        emit(
            PrecipitationEvent(
                kind=PrecipitationKind.TRAINING_CHECKPOINT,
                universe_id=config.universe_id_for_events,
                coherence=pseudo_coherence,
                payload={
                    "checkpoint_path": str(path),
                    "step": step,
                    "epoch": epoch,
                    "loss": loss,
                    "recon_loss": recon,
                    "kl_loss": kl,
                    "final": final,
                    "model_kind": "journey_vae",
                },
            )
        )
    except Exception:  # noqa: BLE001
        logger.debug("Precipitation emit failed for TRAINING_CHECKPOINT", exc_info=True)
    return path


__all__ = [
    "FlumeTrainConfig",
    "JourneyDataset",
    "train_flume_on_journeys",
]
