"""FLUME VAE API routes — training, encoding, decoding, interpolation, latent space.

Extracted from api/__init__.py (Session 87) to keep files under 500 lines.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

flume_router = APIRouter(tags=["flume"])


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
    vector: list[float]


class FlumeEncodeResponse(BaseModel):
    mu: list[float]
    log_var: list[float]
    coherence: float


class FlumeDecodeRequest(BaseModel):
    latent: list[float]


class FlumeDecodeResponse(BaseModel):
    reconstruction: list[float]
    coherence: float


class FlumeInterpolateRequest(BaseModel):
    vector_a: list[float]
    vector_b: list[float]
    ratio: float = 0.5


class FlumeInterpolateResponse(BaseModel):
    result: list[float]
    coherence: float
    mu_a: list[float]
    mu_b: list[float]


class FlumeLatentSpaceRequest(BaseModel):
    n_samples: int = 100
    seed: int | None = None


class FlumeLatentSpaceResponse(BaseModel):
    latent_dim: int
    samples: list[list[float]]
    samples_3d: list[list[float]]
    variance_explained: list[float]
    coherence_scores: list[float]


# --- Helpers ---

_vae_trainer = None


def _get_vae():
    """Lazy-load the trained FLUME VAE (singleton)."""
    global _vae_trainer
    if _vae_trainer is None:
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
                logger.warning("Failed to load FLUME VAE checkpoint: %s", e)
        else:
            logger.warning("No FLUME VAE checkpoint found at %s", ckpt_path)
    return _vae_trainer


def _compute_coherence(z: list[float], z_dim: int = 256) -> float:
    """Compute HIHO coherence: 1.0 at mean=0.5, decays with variance."""
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


# --- Routes ---


@flume_router.post("/flume/train", response_model=FlumeTrainResponse)
async def train_flume(request: FlumeTrainRequest):
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
        logger.error("FLUME training failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Training failed") from e

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


@flume_router.get("/flume/status", response_model=FlumeStatusResponse)
async def flume_status():
    """Check FLUME VAE training status and latest checkpoint."""
    checkpoint_dir = Path("data/flume/checkpoints")
    if not checkpoint_dir.exists():
        return FlumeStatusResponse(trained=False)

    ckpt_files = sorted(checkpoint_dir.glob("flume_vae_ep*.pt"))
    if not ckpt_files:
        return FlumeStatusResponse(trained=False)

    latest = ckpt_files[-1]
    last_metrics = None
    metrics_file = checkpoint_dir / "training_metrics.json"
    if metrics_file.exists():
        try:
            all_metrics = json.loads(metrics_file.read_text())
            if all_metrics:
                last_metrics = all_metrics[-1] if isinstance(all_metrics, list) else all_metrics
        except (json.JSONDecodeError, OSError):
            pass

    return FlumeStatusResponse(trained=True, checkpoint_path=str(latest), last_metrics=last_metrics)


@flume_router.post("/flume/encode", response_model=FlumeEncodeResponse)
async def flume_encode(request: FlumeEncodeRequest):
    """Encode a 256D vector through the trained VAE."""
    vae = _get_vae()
    z_dim = vae.config.z_dim
    if len(request.vector) != z_dim:
        raise HTTPException(
            status_code=422, detail=f"Expected {z_dim}D vector, got {len(request.vector)}D"
        )

    with torch.no_grad():
        x = torch.tensor([request.vector], dtype=torch.float32, device=vae.device)
        h = vae.encoder(x)
        mu = vae.mu_head(h)
        log_var = vae.logvar_head(h)

    mu_list = mu.squeeze(0).tolist()
    return FlumeEncodeResponse(
        mu=mu_list,
        log_var=log_var.squeeze(0).tolist(),
        coherence=_compute_coherence(mu_list, z_dim),
    )


@flume_router.post("/flume/decode", response_model=FlumeDecodeResponse)
async def flume_decode(request: FlumeDecodeRequest):
    """Decode a latent vector through the VAE."""
    vae = _get_vae()
    with torch.no_grad():
        z = torch.tensor([request.latent], dtype=torch.float32, device=vae.device)
        recon = vae.decoder(z)
    recon_list = recon.squeeze(0).tolist()
    return FlumeDecodeResponse(
        reconstruction=recon_list, coherence=_compute_coherence(recon_list, len(recon_list))
    )


@flume_router.post("/flume/interpolate", response_model=FlumeInterpolateResponse)
async def flume_interpolate(request: FlumeInterpolateRequest):
    """Interpolate between two 256D vectors in latent space."""
    vae = _get_vae()
    z_dim = vae.config.z_dim
    if len(request.vector_a) != z_dim or len(request.vector_b) != z_dim:
        raise HTTPException(status_code=422, detail=f"Both vectors must be {z_dim}D")
    if not 0.0 <= request.ratio <= 1.0:
        raise HTTPException(status_code=422, detail="Ratio must be between 0.0 and 1.0")

    with torch.no_grad():
        xa = torch.tensor([request.vector_a], dtype=torch.float32, device=vae.device)
        xb = torch.tensor([request.vector_b], dtype=torch.float32, device=vae.device)
        mu_a = vae.mu_head(vae.encoder(xa))
        mu_b = vae.mu_head(vae.encoder(xb))
        mu_interp = (1.0 - request.ratio) * mu_a + request.ratio * mu_b
        result = vae.decoder(mu_interp)

    result_list = result.squeeze(0).tolist()
    return FlumeInterpolateResponse(
        result=result_list,
        coherence=_compute_coherence(result_list, z_dim),
        mu_a=mu_a.squeeze(0).tolist(),
        mu_b=mu_b.squeeze(0).tolist(),
    )


@flume_router.post("/flume/latent-space", response_model=FlumeLatentSpaceResponse)
async def flume_latent_space(request: FlumeLatentSpaceRequest):
    """Sample the VAE latent space and return PCA-reduced 3D coordinates."""
    from sklearn.decomposition import PCA

    if request.n_samples <= 0:
        raise HTTPException(status_code=422, detail="n_samples must be positive")
    if request.n_samples > 1000:
        raise HTTPException(status_code=422, detail="n_samples must be <= 1000")

    try:
        vae = _get_vae()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"FLUME VAE not available ({type(e).__name__})"
        ) from e

    z_dim = vae.config.z_dim
    if request.seed is not None:
        torch.manual_seed(request.seed)
        np.random.seed(request.seed)
    else:
        seed = int(time.time() * 1000) % (2**32)
        torch.manual_seed(seed)
        np.random.seed(seed)

    with torch.no_grad():
        z_samples = torch.randn(request.n_samples, z_dim, device=vae.device)
        z_samples_np = z_samples.cpu().numpy()

    try:
        async with asyncio.timeout(10.0):
            loop = asyncio.get_event_loop()
            n_components = min(3, z_dim, request.n_samples)
            pca = PCA(n_components=n_components)
            samples_3d = await loop.run_in_executor(None, pca.fit_transform, z_samples_np)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="PCA timed out. Reduce n_samples")

    if np.isnan(samples_3d).any():
        raise HTTPException(status_code=500, detail="PCA produced NaN. VAE may not be trained")

    if samples_3d.shape[1] < 3:
        padding = np.zeros((samples_3d.shape[0], 3 - samples_3d.shape[1]))
        samples_3d = np.hstack([samples_3d, padding])

    coherence_scores = [
        _compute_coherence(z_samples_np[i].tolist(), z_dim) for i in range(len(z_samples_np))
    ]

    return FlumeLatentSpaceResponse(
        latent_dim=z_dim,
        samples=[],
        samples_3d=samples_3d.tolist(),
        variance_explained=pca.explained_variance_ratio_.tolist() if n_components > 0 else [],
        coherence_scores=coherence_scores,
    )
