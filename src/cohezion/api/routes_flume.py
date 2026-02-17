"""FLUME VAE training and inference endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from cohezion.api.models import (
    FlumeDecodeRequest,
    FlumeDecodeResponse,
    FlumeEncodeRequest,
    FlumeEncodeResponse,
    FlumeInterpolateRequest,
    FlumeInterpolateResponse,
    FlumeStatusResponse,
    FlumeTrainRequest,
    FlumeTrainResponse,
    TemplateParseRequest,
    TemplateParseResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flume", tags=["flume"])


@router.post("/train", response_model=FlumeTrainResponse)
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
        logger.error('FLUME training failed: %s', e)
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


@router.get("/status", response_model=FlumeStatusResponse)
async def flume_status():
    """Check FLUME VAE training status and latest checkpoint."""
    checkpoint_dir = Path("data/flume/checkpoints")
    if not checkpoint_dir.exists():
        return FlumeStatusResponse(trained=False)

    ckpt_files = sorted(checkpoint_dir.glob("flume_vae_ep*.pt"))
    if not ckpt_files:
        return FlumeStatusResponse(trained=False)

    latest = ckpt_files[-1]

    metrics_file = checkpoint_dir / "training_metrics.json"
    last_metrics = None
    if metrics_file.exists():
        import json

        try:
            all_metrics = json.loads(metrics_file.read_text())
            if all_metrics:
                last_metrics = (
                    all_metrics[-1] if isinstance(all_metrics, list) else all_metrics
                )
        except (json.JSONDecodeError, OSError):
            pass

    return FlumeStatusResponse(
        trained=True,
        checkpoint_path=str(latest),
        last_metrics=last_metrics,
    )


def _get_vae():
    """Lazy-load the trained FLUME VAE (singleton) via helpers."""
    from cohezion.api.helpers import get_vae

    return get_vae()


def _compute_coherence(z: list[float], z_dim: int = 256) -> float:
    """Compute HIHO coherence via helpers."""
    from cohezion.api.helpers import compute_coherence

    return compute_coherence(z, z_dim)


@router.post("/encode", response_model=FlumeEncodeResponse)
async def flume_encode(request: FlumeEncodeRequest):
    """Encode a 256D vector through the trained VAE, returning mu and log_var."""
    import torch

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


@router.post("/decode", response_model=FlumeDecodeResponse)
async def flume_decode(request: FlumeDecodeRequest):
    """Decode a latent vector through the VAE, returning the reconstruction."""
    import torch

    vae = _get_vae()

    with torch.no_grad():
        z = torch.tensor([request.latent], dtype=torch.float32, device=vae.device)
        recon = vae.decoder(z)

    recon_list = recon.squeeze(0).tolist()
    coherence = _compute_coherence(recon_list, len(recon_list))

    return FlumeDecodeResponse(reconstruction=recon_list, coherence=coherence)


@router.post("/interpolate", response_model=FlumeInterpolateResponse)
async def flume_interpolate(request: FlumeInterpolateRequest):
    """Interpolate between two 256D vectors in latent space."""
    import torch

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

        ha = vae.encoder(xa)
        mu_a = vae.mu_head(ha)
        hb = vae.encoder(xb)
        mu_b = vae.mu_head(hb)

        mu_interp = (1.0 - request.ratio) * mu_a + request.ratio * mu_b

        result = vae.decoder(mu_interp)

    result_list = result.squeeze(0).tolist()
    coherence = _compute_coherence(result_list, z_dim)

    return FlumeInterpolateResponse(
        result=result_list,
        coherence=coherence,
        mu_a=mu_a.squeeze(0).tolist(),
        mu_b=mu_b.squeeze(0).tolist(),
    )


@router.post("/templates/parse", response_model=TemplateParseResponse)
async def parse_template(request: TemplateParseRequest):
    """Parse a PRIME skill definition and return structured spec + generated code."""
    from cohezion.core.config_templates import ConfigTemplateManager

    manager = ConfigTemplateManager()

    try:
        spec = manager.engine.get_spec_by_name(request.skill_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    if spec is None:
        raise HTTPException(
            status_code=404,
            detail=f"Skill not found: {request.skill_name}",
        )

    return TemplateParseResponse(
        name=spec.name,
        domain_expertise=spec.domain_expertise,
        concepts=spec.concepts,
        instructions=spec.instructions,
        version=spec.version,
        see_also=spec.see_also,
        agent_stub=manager.engine.generate_agent_stub(spec),
        config_class=manager.engine.generate_config_class(spec),
    )
