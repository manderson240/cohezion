# ruff: noqa: B904  # raise pattern in HTTP/API handlers — explicit user-facing errors
"""FLUME VAE inline routes — train / status / encode / decode / interpolate / latent-space.

Extracted from api/__init__.py (Wave 2B of synthetic-sniffing-panda).

These re-use ``cohezion.api._get_vae`` and ``cohezion.api._compute_coherence``
so existing test patches (e.g. ``patch("cohezion.api._get_vae", ...)``) keep
working.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


logger = logging.getLogger(__name__)

flume_inline_router = APIRouter(tags=["flume"])


# --- Pydantic models ---


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


# --- Routes ---


@flume_inline_router.post("/flume/train", response_model=FlumeTrainResponse)
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
        # FastAPI endpoint — convert any training failure to clean 500 with logged detail.
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


@flume_inline_router.get("/flume/status", response_model=FlumeStatusResponse)
async def flume_status():
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
        import json

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


@flume_inline_router.post("/flume/encode", response_model=FlumeEncodeResponse)
async def flume_encode(request: FlumeEncodeRequest):
    """Encode a 256D vector through the trained VAE, returning mu and log_var."""
    import torch

    # Use the package-level helpers (so test patches still hit them)
    from cohezion.api import _compute_coherence, _get_vae

    vae = _get_vae()
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
    coherence = _compute_coherence(mu_list, z_dim)

    return FlumeEncodeResponse(mu=mu_list, log_var=log_var_list, coherence=coherence)


@flume_inline_router.post("/flume/decode", response_model=FlumeDecodeResponse)
async def flume_decode(request: FlumeDecodeRequest):
    """Decode a latent vector through the VAE, returning the reconstruction."""
    import torch

    from cohezion.api import _compute_coherence, _get_vae

    vae = _get_vae()

    with torch.no_grad():
        z = torch.tensor([request.latent], dtype=torch.float32, device=vae.device)
        recon = vae.decoder(z)

    recon_list = recon.squeeze(0).tolist()
    coherence = _compute_coherence(recon_list, len(recon_list))

    return FlumeDecodeResponse(reconstruction=recon_list, coherence=coherence)


@flume_inline_router.post("/flume/interpolate", response_model=FlumeInterpolateResponse)
async def flume_interpolate(request: FlumeInterpolateRequest):
    """Interpolate between two 256D vectors in latent space."""
    import torch

    from cohezion.api import _compute_coherence, _get_vae

    vae = _get_vae()
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
    coherence = _compute_coherence(result_list, z_dim)

    return FlumeInterpolateResponse(
        result=result_list,
        coherence=coherence,
        mu_a=mu_a.squeeze(0).tolist(),
        mu_b=mu_b.squeeze(0).tolist(),
    )


@flume_inline_router.post("/flume/latent-space", response_model=FlumeLatentSpaceResponse)
async def flume_latent_space(request: FlumeLatentSpaceRequest):
    """Sample the VAE latent space and return PCA-reduced 3D coordinates for visualization."""
    import asyncio
    import time

    import numpy as np
    import torch
    from sklearn.decomposition import PCA

    from cohezion.api import _compute_coherence, _get_vae

    # Validate parameters (prevent DOS, invalid inputs)
    if request.n_samples <= 0:
        raise HTTPException(
            status_code=422,
            detail="n_samples must be positive",
        )
    if request.n_samples > 1000:
        raise HTTPException(
            status_code=422,
            detail="n_samples must be ≤1000 (performance limit)",
        )

    # Get VAE with explicit error handling (sanitize error messages)
    try:
        vae = _get_vae()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="FLUME VAE checkpoint not found. Train the model first using /flume/train",
        )
    except Exception as e:
        # FastAPI endpoint — sanitize error type to avoid leaking paths/internals to client.
        error_type = type(e).__name__
        raise HTTPException(
            status_code=500,
            detail=f"FLUME VAE not available ({error_type}). Check server logs",
        )

    z_dim = vae.config.z_dim

    # Set seed for reproducibility
    if request.seed is not None:
        torch.manual_seed(request.seed)
        np.random.seed(request.seed)
    else:
        # Default: use random seed for exploration
        seed = int(time.time() * 1000) % (2**32)
        torch.manual_seed(seed)
        np.random.seed(seed)

    # Sample from standard normal distribution in latent space
    with torch.no_grad():
        z_samples = torch.randn(request.n_samples, z_dim, device=vae.device)
        z_samples_np = z_samples.cpu().numpy()

    # Compute PCA for 3D visualization with timeout
    try:
        async with asyncio.timeout(10.0):
            # Run PCA in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            n_components = min(3, z_dim, request.n_samples)
            pca = PCA(n_components=n_components)
            samples_3d = await loop.run_in_executor(None, pca.fit_transform, z_samples_np)
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="PCA computation timed out. Try reducing n_samples",
        )

    # Validate PCA output
    if np.isnan(samples_3d).any() or np.isnan(pca.explained_variance_ratio_).any():
        raise HTTPException(
            status_code=500,
            detail="PCA produced invalid results (NaN). VAE may not be properly trained",
        )

    # Pad with zeros if we have fewer than 3 components
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
