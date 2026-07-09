# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""
FLUME VAE Service - Logic for encoding, decoding, and training Flume latent vectors.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# --- Models ---


class FlumeTrainRequest(BaseModel):
    epochs: int = 50
    batch_size: int = 64
    lr: float = 1e-3
    z_dim: int = 256
    kl_weight: float = 0.1
    coherence_weight: float = 0.05
    n_samples: int = 10000


class FlumeTrainResponse(BaseModel):
    epochs_completed: int
    final_mse: float
    final_kl: float
    final_total: float
    checkpoint_path: str


class FlumeStatusResponse(BaseModel):
    trained: bool
    checkpoint_path: str | None = None
    last_metrics: dict[str, Any] | None = None


class FlumeEncodeRequest(BaseModel):
    vector: list[float]  # 256D input vector


class FlumeEncodeResponse(BaseModel):
    mu: list[float]
    log_var: list[float]
    coherence: float


class FlumeDecodeRequest(BaseModel):
    latent: list[float]  # Latent-space vector


class FlumeDecodeResponse(BaseModel):
    reconstruction: list[float]
    coherence: float


class FlumeInterpolateRequest(BaseModel):
    vector_a: list[float]  # 256D input vector A
    vector_b: list[float]  # 256D input vector B
    ratio: float = 0.5  # Interpolation ratio (0=A, 1=B)


class FlumeInterpolateResponse(BaseModel):
    result: list[float]
    coherence: float
    mu_a: list[float]
    mu_b: list[float]


# --- Service Logic ---

_vae_trainer = None


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
                logger.warning(
                    "Failed to load FLUME VAE checkpoint %s (architecture mismatch?); using random weights: %s",
                    ckpt_path,
                    str(e),
                )
        else:
            logger.warning("No FLUME VAE checkpoint found at %s; using random weights", ckpt_path)
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


async def train_flume_service(request: FlumeTrainRequest) -> FlumeTrainResponse:
    """Trigger FLUME VAE training on synthetic data."""
    from cohezion.flume.dataset import SyntheticFlumeDataset
    from cohezion.flume.training import FlumeVAETrainer, TrainConfig

    config = TrainConfig(
        z_dim=request.z_dim,
        batch_size=request.batch_size,
        epochs=request.epochs,
        lr=request.lr,
        kl_weight=request.kl_weight,
        coherence_weight=request.coherence_weight,
    )

    dataset = SyntheticFlumeDataset(n_samples=request.n_samples, z_dim=request.z_dim)
    trainer = FlumeVAETrainer(config)

    try:
        metrics = trainer.train(dataset=dataset)
    except Exception as e:
        logger.error(f"FLUME training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    final = metrics[-1]
    checkpoint_dir = Path(config.checkpoint_dir)
    ckpt_files = sorted(checkpoint_dir.glob("flume_vae_ep*.pt"))
    checkpoint_path = str(ckpt_files[-1]) if ckpt_files else ""

    return FlumeTrainResponse(
        epochs_completed=len(metrics),
        final_mse=final["mse"],
        final_kl=final["kl"],
        final_total=final["total"],
        checkpoint_path=checkpoint_path,
    )


async def get_flume_status() -> FlumeStatusResponse:
    """Check FLUME VAE training status and latest checkpoint."""
    checkpoint_dir = Path("data/flume/checkpoints")
    if not checkpoint_dir.exists():
        return FlumeStatusResponse(trained=False)

    ckpt_files = sorted(checkpoint_dir.glob("flume_vae_ep*.pt"))
    if not ckpt_files:
        return FlumeStatusResponse(trained=False)

    latest = ckpt_files[-1]

    # Try to load metrics
    metrics_file = checkpoint_dir / "training_metrics.json"
    last_metrics = None
    if metrics_file.exists():
        try:
            all_metrics = json.loads(metrics_file.read_text())
            if all_metrics:
                last_metrics = all_metrics[-1] if isinstance(all_metrics, list) else all_metrics
        except (json.JSONDecodeError, OSError):
            pass

    return FlumeStatusResponse(
        trained=True,
        checkpoint_path=str(latest),
        last_metrics=last_metrics,
    )


async def flume_encode_service(request: FlumeEncodeRequest) -> FlumeEncodeResponse:
    """Encode a 256D vector through the trained VAE."""
    import torch

    vae = get_vae()
    z_dim = vae.config.z_dim

    if len(request.vector) != z_dim:
        raise HTTPException(
            status_code=422,
            detail=f"Expected {z_dim}D vector, got {len(request.vector)}D",
        )

    with torch.no_grad():
        x = torch.tensor([request.vector], dtype=torch.float32, device=vae.device)
        h = vae.encoder(x)
        mu = vae.mu_head(h)
        log_var = vae.logvar_head(h)

    mu_list = mu.squeeze(0).tolist()
    log_var_list = log_var.squeeze(0).tolist()
    coherence = compute_coherence(mu_list, z_dim)

    return FlumeEncodeResponse(mu=mu_list, log_var=log_var_list, coherence=coherence)


async def flume_decode_service(request: FlumeDecodeRequest) -> FlumeDecodeResponse:
    """Decode a latent vector through the VAE."""
    import torch

    vae = get_vae()

    with torch.no_grad():
        z = torch.tensor([request.latent], dtype=torch.float32, device=vae.device)
        recon = vae.decoder(z)

    recon_list = recon.squeeze(0).tolist()
    coherence = compute_coherence(recon_list, len(recon_list))

    return FlumeDecodeResponse(reconstruction=recon_list, coherence=coherence)


async def flume_interpolate_service(request: FlumeInterpolateRequest) -> FlumeInterpolateResponse:
    """Interpolate between two 256D vectors in latent space."""
    import torch

    vae = get_vae()
    z_dim = vae.config.z_dim

    if len(request.vector_a) != z_dim or len(request.vector_b) != z_dim:
        raise HTTPException(
            status_code=422,
            detail=f"Both vectors must be {z_dim}D",
        )

    if not 0.0 <= request.ratio <= 1.0:
        raise HTTPException(
            status_code=422,
            detail="Ratio must be between 0.0 and 1.0",
        )

    with torch.no_grad():
        xa = torch.tensor([request.vector_a], dtype=torch.float32, device=vae.device)
        xb = torch.tensor([request.vector_b], dtype=torch.float32, device=vae.device)

        # Encode both vectors
        ha = vae.encoder(xa)
        mu_a = vae.mu_head(ha)
        hb = vae.encoder(xb)
        mu_b = vae.mu_head(hb)

        # Linear interpolation in latent space
        mu_interp = (1.0 - request.ratio) * mu_a + request.ratio * mu_b

        # Decode the interpolated latent
        result = vae.decoder(mu_interp)

    result_list = result.squeeze(0).tolist()
    coherence = compute_coherence(result_list, z_dim)

    return FlumeInterpolateResponse(
        result=result_list,
        coherence=coherence,
        mu_a=mu_a.squeeze(0).tolist(),
        mu_b=mu_b.squeeze(0).tolist(),
    )
