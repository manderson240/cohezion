"""
Cohezion API - FastAPI server exposing swarm and MCP tools.

Provides REST endpoints for Open-Notebook integration.
"""

import contextlib
import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cohezion.api.services.anima import anima_router
from cohezion.api.services.architecture import architecture_router
from cohezion.api.services.brand import brand_router
from cohezion.api.services.universe import universe_router
from cohezion.mcp.knowledge_server import get_server as get_knowledge_server
from cohezion.mcp.registry import get_registry
from cohezion.mcp.swarm_server import get_server as get_swarm_server
from cohezion.security.rate_limiter import get_rate_limiter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed CORS origins from environment, default to localhost only
_CORS_ORIGINS = os.environ.get("COHEZION_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

app = FastAPI(
    title="Cohezion API",
    description="AI Research Lab API - Swarm workflows and MCP tools",
    version="1.0.2",
    docs_url="/docs" if os.environ.get("COHEZION_ENV") != "production" else None,
    redoc_url="/redoc" if os.environ.get("COHEZION_ENV") != "production" else None,
)

# CORS — restricted to configured origins with explicit methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Agent-Token"],
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else "unknown"
    result = limiter.check(client_ip, request.url.path)
    if not result.allowed:
        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(int(result.reset_after) + 1),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
            },
            content={"detail": "Rate limit exceeded"},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    return response


# Static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")


# Universe physics API (real HIHO engine state for the Anima Dashboard)
app.include_router(anima_router, prefix="/api/anima")
app.include_router(architecture_router, prefix="/api/architecture")
app.include_router(brand_router, prefix="/api/brand")
app.include_router(universe_router, prefix="/api/universe")


# Root redirect to UI
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


# Pydantic models
class DebateRequest(BaseModel):
    query: str
    perspectives: list[str] | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class DebateResponse(BaseModel):
    content: str
    confidence: float
    model_chain: list[str]
    processing_time_ms: float


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cohezion"}


# MCP Registry endpoints
@app.get("/mcp/servers")
async def list_servers():
    """List all available MCP servers."""
    registry = get_registry()
    return {"servers": [{"name": s.name, "type": s.type, "status": s.status} for s in registry.list_servers()]}


@app.get("/mcp/tools")
async def list_tools():
    """List all available MCP tools."""
    registry = get_registry()
    return {"tools": registry.list_tools()}


# Knowledge endpoints
@app.post("/knowledge/search")
async def search_knowledge(request: SearchRequest):
    """Search knowledge base."""
    server = get_knowledge_server()
    results = server.search_knowledge(request.query, request.limit)
    return {"results": results}


@app.get("/knowledge/skills")
async def list_skills():
    """List all skills."""
    server = get_knowledge_server()
    return {"skills": server.list_skills()}


@app.get("/knowledge/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get a specific skill."""
    server = get_knowledge_server()
    result = server.get_skill(skill_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Swarm endpoints
@app.post("/swarm/debate", response_model=DebateResponse)
async def run_debate(request: DebateRequest):
    """Run a multi-perspective debate."""
    server = get_swarm_server()
    try:
        result = server.run_debate(request.query, request.perspectives)
        return DebateResponse(
            content=result["content"],
            confidence=result["confidence"],
            model_chain=result["model_chain"],
            processing_time_ms=result["processing_time_ms"],
        )
    except Exception as e:
        logger.error(f"Debate failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/swarm/perspectives")
async def get_perspectives():
    """Get available analyst perspectives."""
    server = get_swarm_server()
    return {"perspectives": server.get_perspectives()}


@app.get("/swarm/metrics")
async def get_metrics():
    """Get swarm workflow metrics."""
    server = get_swarm_server()
    return {"metrics": server.get_metrics()}


# Notebook endpoints
@app.get("/notebooks")
async def list_notebooks():
    """List all research notebooks."""
    from pathlib import Path

    notebooks_dir = Path("docs/notebooks")
    if not notebooks_dir.exists():
        return {"notebooks": []}
    notebooks = [f.stem for f in notebooks_dir.glob("*.md")]
    return {"notebooks": notebooks}


@app.get("/notebooks/{name}")
async def get_notebook(name: str):
    """Get a specific notebook."""
    from pathlib import Path

    # Validate name: only allow alphanumeric, dash, underscore (prevent path traversal)
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise HTTPException(status_code=400, detail="Invalid notebook name")

    base_dir = Path("docs/notebooks").resolve()
    notebook_path = (base_dir / f"{name}.md").resolve()

    # Ensure resolved path stays within the base directory
    if not str(notebook_path).startswith(str(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"name": name, "content": notebook_path.read_text()}


# Simulation endpoints
@app.get("/simulations")
async def list_simulations():
    """List all physics simulations."""
    import json
    from pathlib import Path

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        return {"simulations": []}
    data = json.loads(sim_file.read_text())
    return {"simulations": [s["id"] for s in data.get("simulations", [])]}


@app.get("/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    """Get a specific simulation result."""
    import json
    from pathlib import Path

    sim_file = Path("src/cohezion/knowledge_graph/universe_nodes/physics_simulations.json")
    if not sim_file.exists():
        raise HTTPException(status_code=404, detail="No simulations found")
    data = json.loads(sim_file.read_text())
    for sim in data.get("simulations", []):
        if sim["id"] == sim_id:
            return sim
    raise HTTPException(status_code=404, detail=f"Simulation {sim_id} not found")


# Journey endpoints - Agent trajectory visualization
# NOTE: cohezion.swarm.journey_tracker was removed during refactor.
# The replacement is cohezion.compound.journey_tracker (12D FLUME API).
# These endpoints return 501 until updated to the new JourneyTracker API.
_JOURNEY_TRACKER_UNAVAILABLE = HTTPException(
    status_code=501,
    detail="Journey tracker endpoints are being migrated to the compound module. "
    "Use /compound/history for execution history.",
)


@app.get("/journeys")
async def list_journeys():
    """List recent agent journeys."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@app.get("/journeys/{journey_id}")
async def get_journey(journey_id: str):
    """Get a specific journey with full trajectory."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


@app.get("/journeys/{journey_id}/trajectory")
async def get_journey_trajectory(journey_id: str):
    """Get physics trajectory for visualization."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


# Demo journey endpoint
@app.post("/journeys/demo")
async def create_demo_journey():
    """Create a demo journey to showcase visualization."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


# Journey visualization endpoint
@app.get("/journeys/{journey_id}/visualize")
async def visualize_journey(journey_id: str):
    """Render an animated visualization of the journey trajectory."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


# Static image visualization
@app.get("/journeys/{journey_id}/plot")
async def plot_journey(journey_id: str):
    """Render a multi-panel 12D physics visualization of the journey."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


# ---------- Phase 2 Endpoints: Training & Templates ----------


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


class TemplateParseRequest(BaseModel):
    skill_name: str


class TemplateParseResponse(BaseModel):
    name: str
    domain_expertise: str
    concepts: dict[str, str]
    instructions: list[str]
    version: str
    see_also: list[str]
    agent_stub: str
    config_class: str


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


class RLTrainRequest(BaseModel):
    n_episodes: int = 100
    max_steps: int = 200
    lr: float = 3e-4
    gamma: float = 0.99


class RLTrainResponse(BaseModel):
    episodes_completed: int
    final_reward: float
    final_coherence: float
    mean_reward: float
    checkpoint_path: str


class RLPolicyResponse(BaseModel):
    exists: bool
    checkpoint_path: str | None = None
    parameters: int | None = None
    state_dim: int | None = None
    action_dim: int | None = None


@app.post("/flume/train", response_model=FlumeTrainResponse)
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
        logger.error(f"FLUME training failed: {e}", exc_info=True)
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


@app.get("/flume/status", response_model=FlumeStatusResponse)
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


_vae_trainer = None


def _get_vae():
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


def _compute_coherence(z: list[float], z_dim: int = 256) -> float:
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


@app.post("/flume/encode", response_model=FlumeEncodeResponse)
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


@app.post("/flume/decode", response_model=FlumeDecodeResponse)
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


@app.post("/flume/interpolate", response_model=FlumeInterpolateResponse)
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


@app.post("/templates/parse", response_model=TemplateParseResponse)
async def parse_template(request: TemplateParseRequest):
    """Parse a PRIME skill definition and return structured spec + generated code."""
    from cohezion.core.config_templates import ConfigTemplateManager

    manager = ConfigTemplateManager()

    try:
        spec = manager.engine.get_spec_by_name(request.skill_name)
    except Exception as e:
        logger.error(f"Template parse failed for {request.skill_name}: {e}")
        raise HTTPException(status_code=500, detail="Template parsing failed") from e

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


@app.post("/rl/train", response_model=RLTrainResponse)
async def train_rl(request: RLTrainRequest):
    """Trigger RL policy training on FlumeNav-v0."""
    from cohezion.rl.trainer import TrainingConfig, train

    config = TrainingConfig(
        n_episodes=request.n_episodes,
        max_steps=request.max_steps,
        lr=request.lr,
        gamma=request.gamma,
    )

    try:
        results = train(config)
    except Exception as e:
        logger.error(f"RL training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Training failed") from e

    final = results[-1]
    import numpy as np

    mean_reward = float(np.mean([r.total_reward for r in results]))
    checkpoint_dir = Path(config.output_dir)
    ckpt = checkpoint_dir / "policy_final.pt"

    return RLTrainResponse(
        episodes_completed=len(results),
        final_reward=final.total_reward,
        final_coherence=final.mean_coherence,
        mean_reward=mean_reward,
        checkpoint_path=str(ckpt) if ckpt.exists() else "",
    )


@app.get("/rl/policy/{agent_id}", response_model=RLPolicyResponse)
async def get_rl_policy(agent_id: str):
    """Inspect a trained RL policy checkpoint."""
    checkpoint_dir = Path("data/rl/checkpoints")
    ckpt_path = checkpoint_dir / f"policy_{agent_id}.pt"

    # Also check for the default final checkpoint
    if not ckpt_path.exists():
        ckpt_path = checkpoint_dir / "policy_final.pt"

    if not ckpt_path.exists():
        return RLPolicyResponse(exists=False)

    import torch

    try:
        state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        n_params = sum(v.numel() for v in state_dict.values())

        # Infer dimensions from the first linear layer
        state_dim = None
        action_dim = None
        if "shared.0.weight" in state_dict:
            state_dim = state_dict["shared.0.weight"].shape[1]
        if "mean_head.weight" in state_dict:
            action_dim = state_dict["mean_head.weight"].shape[0]

        return RLPolicyResponse(
            exists=True,
            checkpoint_path=str(ckpt_path),
            parameters=n_params,
            state_dim=state_dim,
            action_dim=action_dim,
        )
    except Exception as e:
        logger.warning(f"Failed to inspect policy checkpoint: {e}")
        return RLPolicyResponse(exists=True, checkpoint_path=str(ckpt_path))


# ---------- Phase 2 Endpoints: RL Inference ----------


class RlStepRequest(BaseModel):
    state: list[float]  # 256D state vector


class RlStepResponse(BaseModel):
    action: list[float]  # 256D action vector
    coherence: float


class RlEpisodeResponse(BaseModel):
    steps: int
    total_reward: float
    mean_coherence: float
    final_coherence: float
    trajectory: list[dict[str, Any]]


class RlPolicyInfoResponse(BaseModel):
    loaded: bool
    architecture: str | None = None
    state_dim: int | None = None
    action_dim: int | None = None
    hidden_dim: int | None = None
    parameters: int | None = None
    checkpoint_path: str | None = None
    training_metrics: list[dict[str, Any]] | dict[str, Any] | None = None


_rl_policy = None


def _get_rl_policy():
    """Lazy-load the trained RL policy singleton."""
    global _rl_policy
    if _rl_policy is None:
        import torch

        from cohezion.rl.trainer import PolicyNetwork

        _rl_policy = PolicyNetwork(state_dim=256, action_dim=256, hidden=128)
        ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
        if ckpt_path.exists():
            _rl_policy.load_state_dict(torch.load(ckpt_path, map_location="cpu", weights_only=True))
            _rl_policy.eval()
            logger.info("Loaded RL policy from %s", ckpt_path)
        else:
            logger.warning("No RL checkpoint at %s — using random policy", ckpt_path)
    return _rl_policy


@app.post("/rl/step", response_model=RlStepResponse)
async def rl_step(request: RlStepRequest):
    """Run a single RL step: state -> policy -> action + coherence."""
    import numpy as np

    if len(request.state) != 256:
        raise HTTPException(
            status_code=422,
            detail=f"State must be 256D, got {len(request.state)}D",
        )

    policy = _get_rl_policy()
    state = np.array(request.state, dtype=np.float32)
    action, _log_prob = policy.get_action(state)

    # Compute coherence of resulting state (state + scaled action)
    next_state = state + action * 0.01
    coherence = _compute_coherence(next_state.tolist(), 256)

    return RlStepResponse(
        action=action.tolist(),
        coherence=coherence,
    )


@app.post("/rl/episode", response_model=RlEpisodeResponse)
async def rl_episode():
    """Run a full RL episode (up to 200 steps) with the trained policy."""
    import gymnasium as gym
    import numpy as np

    import cohezion.rl.environment

    policy = _get_rl_policy()
    env = gym.make("cohezion/FlumeNav-v0", max_steps=200)

    try:
        obs, info = env.reset(seed=42)
        trajectory: list[dict[str, Any]] = []
        total_reward = 0.0
        coherences: list[float] = [info["coherence"]]

        for _step in range(200):
            action, _log_prob = policy.get_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)

            total_reward += reward
            coherences.append(info["coherence"])
            trajectory.append(
                {
                    "state_mean": float(np.mean(obs)),
                    "state_std": float(np.std(obs)),
                    "action_norm": float(np.linalg.norm(action)),
                    "reward": reward,
                    "coherence": info["coherence"],
                }
            )

            if terminated or truncated:
                break
    finally:
        env.close()

    return RlEpisodeResponse(
        steps=len(trajectory),
        total_reward=total_reward,
        mean_coherence=float(np.mean(coherences)),
        final_coherence=coherences[-1],
        trajectory=trajectory,
    )


@app.get("/rl/policy-info", response_model=RlPolicyInfoResponse)
async def rl_policy_info():
    """Return policy metadata: architecture, parameters, training metrics."""
    import json

    ckpt_path = Path("data/rl/checkpoints/policy_final.pt")
    if not ckpt_path.exists():
        return RlPolicyInfoResponse(loaded=False)

    policy = _get_rl_policy()
    n_params = sum(p.numel() for p in policy.parameters())

    # Load training metrics if available
    metrics_path = Path("data/rl/checkpoints/training_metrics.json")
    training_metrics = None
    if metrics_path.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            training_metrics = json.loads(metrics_path.read_text())

    return RlPolicyInfoResponse(
        loaded=True,
        architecture="PolicyNetwork(shared=[Linear+ReLU x2], mean_head=Linear, log_std=Parameter)",
        state_dim=256,
        action_dim=256,
        hidden_dim=128,
        parameters=n_params,
        checkpoint_path=str(ckpt_path),
        training_metrics=training_metrics,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)


# CALM vs LLM comparison visualization
@app.get("/compare/calm-vs-llm/{journey_id}")
async def compare_calm_llm(journey_id: str):
    """Compare CALM continuous trajectory vs standard LLM discrete steps."""
    raise _JOURNEY_TRACKER_UNAVAILABLE


# ---------------------------------------------------------------------------
# Skill-Agent-API Fabric endpoints
# ---------------------------------------------------------------------------


class SkillExecuteRequest(BaseModel):
    input_text: str
    config: dict[str, Any] = {}


class PlanStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float


class SkillExecuteResponse(BaseModel):
    skill_name: str
    agent_class: str
    result: str
    status: str
    plan_steps: list[PlanStepOut] | None = None
    total_tokens: int | None = None
    total_duration_ms: float | None = None


class CapabilityQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class CapabilityQueryResponse(BaseModel):
    agents: list[dict[str, Any]]
    query: str


@app.post("/skills/{skill_name}/execute", response_model=SkillExecuteResponse)
async def execute_skill(skill_name: str, request: SkillExecuteRequest):
    """Parse skill, expand instructions into a plan, and execute via PlanExecutor."""
    from cohezion.agents.factory import AgentFactory
    from cohezion.core.instruction_expander import InstructionExpander
    from cohezion.core.plan_executor import PlanExecutor
    from cohezion.swarm.compound_client import get_compound_client

    factory = AgentFactory()
    try:
        spec = factory._resolve_spec(skill_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_name}") from None

    class_name = f"{spec.name}Agent"

    # Expand instructions into a plan and execute
    try:
        expander = InstructionExpander()
        plan = expander.expand(spec)
        compound = get_compound_client()
        executor = PlanExecutor(token_client=compound)
        exec_result = await executor.execute(plan, request.input_text)

        step_outputs = [
            PlanStepOut(
                step_index=sr.step_index,
                operation=sr.operation,
                description=plan.steps[sr.step_index].description,
                output=sr.output,
                tokens_used=sr.tokens_used,
                duration_ms=sr.duration_ms,
            )
            for sr in exec_result.steps
        ]

        return SkillExecuteResponse(
            skill_name=skill_name,
            agent_class=class_name,
            result=exec_result.final_output,
            status="executed",
            plan_steps=step_outputs,
            total_tokens=exec_result.total_tokens,
            total_duration_ms=exec_result.total_duration_ms,
        )
    except Exception as exc:
        logger.exception("Skill execution failed: %s", skill_name)
        return SkillExecuteResponse(
            skill_name=skill_name,
            agent_class=class_name,
            result=str(exc),
            status="error",
        )


@app.post("/query/find-capable-agent", response_model=CapabilityQueryResponse)
async def find_capable_agent(request: CapabilityQueryRequest):
    """Use CapabilityRegistry to find best agents for a query."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    results = registry.find(request.query, top_k=request.top_k)
    return CapabilityQueryResponse(
        query=request.query,
        agents=[
            {
                "name": cap.name,
                "type": cap.type,
                "description": cap.description,
                "score": round(cap.score, 4),
                "path": cap.path,
            }
            for cap in results
        ],
    )


@app.get("/skills/list")
async def list_prime_skills():
    """List all available PRIME skills."""
    from cohezion.agents.factory import AgentFactory

    factory = AgentFactory()
    names = factory.list_available_skills()
    return {"count": len(names), "skills": names}


# ---------------------------------------------------------------------------
# Observability & Metrics endpoints (Phase 3D)
# ---------------------------------------------------------------------------


class AgentMetrics(BaseModel):
    name: str
    type: str
    description: str
    metrics: dict[str, Any] = {}


class AgentMetricsResponse(BaseModel):
    count: int
    agents: list[AgentMetrics]


class TrainingMetricsResponse(BaseModel):
    flume_vae: dict[str, Any]
    rl_policy: dict[str, Any]


class PipelineStageStatus(BaseModel):
    stage: str
    status: str
    detail: str = ""


class PipelineStatusResponse(BaseModel):
    stages: list[PipelineStageStatus]
    complete_count: int
    total_count: int


class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_percent: float
    ollama_available: bool
    ollama_models: list[str] = []


class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeQueryResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    count: int


@app.get("/metrics/agents", response_model=AgentMetricsResponse)
async def metrics_agents():
    """Return registered agent stats from CapabilityRegistry."""
    from cohezion.registry.capability_registry import CapabilityRegistry

    registry = CapabilityRegistry()
    caps = registry.find("agent", top_k=50)
    agents = [
        AgentMetrics(
            name=cap.name,
            type=cap.type,
            description=cap.description,
            metrics={"score": round(cap.score, 4), "path": cap.path},
        )
        for cap in caps
    ]
    return AgentMetricsResponse(count=len(agents), agents=agents)


@app.get("/metrics/training", response_model=TrainingMetricsResponse)
async def metrics_training():
    """Return training metrics from checkpoint files."""
    import json as _json

    flume_info: dict[str, Any] = {"status": "no_checkpoint"}
    rl_info: dict[str, Any] = {"status": "no_checkpoint"}

    # FLUME VAE
    flume_metrics = Path("data/flume/checkpoints/training_metrics.json")
    flume_ckpt = Path("data/flume/checkpoints/flume_vae_ep50.pt")
    if flume_metrics.exists():
        try:
            data = _json.loads(flume_metrics.read_text())
            flume_info = {
                "status": "trained",
                "epochs": len(data) if isinstance(data, list) else data.get("epochs", 0),
                "checkpoint": str(flume_ckpt) if flume_ckpt.exists() else None,
                "metrics": data if isinstance(data, dict) else {"epoch_data": data[-3:]},
            }
        except Exception:
            flume_info = {"status": "checkpoint_found", "path": str(flume_metrics)}
    elif flume_ckpt.exists():
        flume_info = {"status": "checkpoint_found", "path": str(flume_ckpt)}

    # RL Policy
    rl_metrics = Path("data/rl/checkpoints/training_metrics.json")
    rl_ckpt = Path("data/rl/checkpoints/policy_final.pt")
    if rl_metrics.exists():
        try:
            data = _json.loads(rl_metrics.read_text())
            rl_info = {
                "status": "trained",
                "episodes": len(data) if isinstance(data, list) else data.get("episodes", 0),
                "checkpoint": str(rl_ckpt) if rl_ckpt.exists() else None,
                "metrics": data if isinstance(data, dict) else {"episode_data": data[-3:]},
            }
        except Exception:
            rl_info = {"status": "checkpoint_found", "path": str(rl_metrics)}
    elif rl_ckpt.exists():
        rl_info = {"status": "checkpoint_found", "path": str(rl_ckpt)}

    return TrainingMetricsResponse(flume_vae=flume_info, rl_policy=rl_info)


@app.get("/metrics/pipeline", response_model=PipelineStatusResponse)
async def metrics_pipeline():
    """Return pipeline stage completion status."""
    stages: list[PipelineStageStatus] = []

    # Stage 1: Mass sim .npy export
    npy_dir = Path("data/mass_sim/artifacts")
    npy_files = list(npy_dir.glob("*.npy")) if npy_dir.exists() else []
    stages.append(
        PipelineStageStatus(
            stage="mass_sim_export",
            status="complete" if npy_files else "pending",
            detail=f"{len(npy_files)} .npy files" if npy_files else "No .npy exports found",
        )
    )

    # Stage 2: VAE training
    vae_ckpt = Path("data/flume/checkpoints/flume_vae_ep50.pt")
    stages.append(
        PipelineStageStatus(
            stage="vae_training",
            status="complete" if vae_ckpt.exists() else "pending",
            detail=str(vae_ckpt) if vae_ckpt.exists() else "No VAE checkpoint",
        )
    )

    # Stage 3: RL training
    rl_ckpt = Path("data/rl/checkpoints/policy_final.pt")
    stages.append(
        PipelineStageStatus(
            stage="rl_training",
            status="complete" if rl_ckpt.exists() else "pending",
            detail=str(rl_ckpt) if rl_ckpt.exists() else "No RL checkpoint",
        )
    )

    # Stage 4: Weight bridge
    # Check if pipeline has been run (script output or validation file)
    pipeline_ran = Path("data/pipeline_results")
    stages.append(
        PipelineStageStatus(
            stage="weight_bridge",
            status="complete" if pipeline_ran.exists() else "pending",
            detail="Weight bridge validated" if pipeline_ran.exists() else "Not yet executed",
        )
    )

    complete = sum(1 for s in stages if s.status == "complete")
    return PipelineStatusResponse(stages=stages, complete_count=complete, total_count=len(stages))


@app.get("/metrics/system", response_model=SystemMetricsResponse)
async def metrics_system():
    """Return system resource metrics."""
    import psutil

    mem = psutil.virtual_memory()

    # Check Ollama availability
    ollama_available = False
    ollama_models: list[str] = []
    try:
        import httpx as _httpx

        async with _httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                ollama_available = True
                models_data = resp.json().get("models", [])
                ollama_models = [m["name"] for m in models_data]
    except Exception as e:
        logger.debug("Ollama status check unavailable: %s", e)

    return SystemMetricsResponse(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_total_gb=round(mem.total / (1024**3), 2),
        memory_available_gb=round(mem.available / (1024**3), 2),
        memory_percent=mem.percent,
        ollama_available=ollama_available,
        ollama_models=ollama_models,
    )


@app.post("/knowledge/query", response_model=KnowledgeQueryResponse)
async def knowledge_query(request: KnowledgeQueryRequest):
    """Search the knowledge graph for relevant entries."""
    from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine

    engine = KnowledgeGraphQueryEngine()
    results = engine.search_knowledge(request.query, top_k=request.top_k)
    return KnowledgeQueryResponse(query=request.query, results=results, count=len(results))


# --- Token Efficiency Metrics ---


class TokenMetricsResponse(BaseModel):
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    tokens_saved: int = 0
    total_calls: int = 0
    model_usage: dict[str, int] = {}


@app.get("/metrics/tokens", response_model=TokenMetricsResponse)
async def metrics_tokens():
    """Return token efficiency metrics from the shared compound client."""
    from cohezion.swarm.compound_client import get_compound_client

    # Use a module-level override if set, otherwise the compound singleton
    client = getattr(metrics_tokens, "_client", None)
    if client is None:
        client = get_compound_client()
    return TokenMetricsResponse(**client.get_metrics())


def set_token_client(client: Any) -> None:
    """Register a TokenEfficientClient for the /metrics/tokens endpoint.

    Pass ``None`` to revert to the default compound client singleton.
    """
    metrics_tokens._client = client  # type: ignore[attr-defined]


# --- Swarm Execution ---


class SwarmExecuteRequest(BaseModel):
    intent: str
    max_agents: int = 4


class SwarmTaskResult(BaseModel):
    task_id: str = ""
    subject: str = ""
    status: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    tokens: int = 0


class SwarmExecuteResponse(BaseModel):
    report_id: str = ""
    plan_name: str = ""
    intent: str = ""
    status: str = ""
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    tasks: list[SwarmTaskResult] = []


@app.post("/swarm/execute", response_model=SwarmExecuteResponse)
async def swarm_execute(request: SwarmExecuteRequest):
    """Plan and execute a swarm from a natural language intent."""
    from cohezion.swarm.compound_client import get_compound_client
    from cohezion.swarm.execution_orchestrator import ExecutionOrchestrator
    from cohezion.swarm.team_orchestrator import TeamOrchestrator

    compound = get_compound_client()
    orchestrator_obj = TeamOrchestrator()
    plan = orchestrator_obj.plan_team(request.intent, max_agents=request.max_agents)
    executor = ExecutionOrchestrator(token_client=compound)
    report = await executor.execute(plan)

    report_dict = report.to_dict()
    return SwarmExecuteResponse(
        report_id=report_dict.get("report_id", ""),
        plan_name=report_dict.get("plan_name", ""),
        intent=report_dict.get("intent", ""),
        status=report_dict.get("status", ""),
        total_tokens=report_dict.get("total_tokens", 0),
        total_duration_ms=report_dict.get("total_duration_ms", 0.0),
        tasks=[SwarmTaskResult(**t) for t in report_dict.get("tasks", [])],
    )


# --- Compound Engineering Metrics ---


class CompoundMetricsResponse(BaseModel):
    total_learnings: int = 0
    top_compound_scores: list[dict[str, Any]] = []
    suggested_refinements: list[dict[str, Any]] = []
    total_executions: int = 0


@app.get("/metrics/compound", response_model=CompoundMetricsResponse)
async def metrics_compound():
    """Return compound engineering metrics from retrospection analysis."""
    from cohezion.compound.metrics import get_collector
    from cohezion.core.compound.retrospection import RetrospectionEngine

    engine = RetrospectionEngine()
    learnings = engine.analyze_learnings()
    scores = engine.calculate_compound_scores()
    refinements = engine.suggest_skill_refinements()

    top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    collector = get_collector()

    return CompoundMetricsResponse(
        total_learnings=len(learnings),
        top_compound_scores=[{"name": name, "score": score} for name, score in top_scores],
        suggested_refinements=[
            {
                "skill_name": r.skill_name,
                "reason": r.reason,
                "learning_count": len(r.suggested_additions),
            }
            for r in refinements
        ],
        total_executions=collector.total_executions,
    )


# ---------------------------------------------------------------------------
# Compound Execution & Feedback endpoints
# ---------------------------------------------------------------------------


class CompoundExecuteRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None


class CompoundStepOut(BaseModel):
    step_index: int
    operation: str
    description: str
    output: str
    tokens_used: int
    duration_ms: float
    model: str = ""


class CompoundExecuteResponse(BaseModel):
    skill_name: str
    final_output: str
    steps: list[CompoundStepOut] = []
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    model_usage: dict[str, int] = {}


@app.post("/compound/execute", response_model=CompoundExecuteResponse)
async def compound_execute(request: CompoundExecuteRequest):
    """Execute a PRIME skill with live Ollama models via CompoundExecutor."""
    from cohezion.compound.executor import get_executor

    executor = get_executor()
    try:
        result = await executor.execute_skill(
            request.skill_name,
            request.input_text,
            model=request.model,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_name}") from exc
    except Exception as exc:
        logger.exception("Compound execution failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail="Execution failed") from exc

    return CompoundExecuteResponse(
        skill_name=result.skill_name,
        final_output=result.final_output,
        steps=[
            CompoundStepOut(
                step_index=s["step_index"],
                operation=s["operation"],
                description=s["description"],
                output=s["output"],
                tokens_used=s["tokens_used"],
                duration_ms=s["duration_ms"],
                model=s.get("model", ""),
            )
            for s in result.steps
        ],
        total_tokens=result.total_tokens,
        total_duration_ms=result.total_duration_ms,
        model_usage=result.model_usage,
    )


class CompoundFeedbackRequest(BaseModel):
    skill_name: str
    input_text: str
    model: str | None = None
    cycles: int = 1


class CompoundFeedbackResponse(BaseModel):
    skill_name: str
    cycles_completed: int = 0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    total_refinements: int = 0
    compound_score_delta: float = 0.0
    patterns: list[str] = []


@app.post("/compound/feedback", response_model=CompoundFeedbackResponse)
async def compound_feedback(request: CompoundFeedbackRequest):
    """Run a compound feedback cycle: execute -> analyze -> refine."""
    from cohezion.compound.feedback_loop import CompoundFeedbackLoop

    loop = CompoundFeedbackLoop()
    try:
        if request.cycles > 1:
            report = await loop.run_multi_cycle(
                request.skill_name,
                request.input_text,
                cycles=request.cycles,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=report.skill_name,
                cycles_completed=report.total_cycles,
                total_tokens=report.total_tokens,
                total_duration_ms=report.total_duration_ms,
                total_refinements=report.total_refinements,
                compound_score_delta=report.final_compound_score_delta,
            )
        else:
            result = await loop.run_cycle(
                request.skill_name,
                request.input_text,
                model=request.model,
            )
            return CompoundFeedbackResponse(
                skill_name=result.skill_name,
                cycles_completed=1,
                total_tokens=result.execution_tokens,
                total_duration_ms=result.execution_duration_ms,
                total_refinements=result.refinements_applied,
                compound_score_delta=result.compound_score_delta,
                patterns=result.patterns,
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_name}") from exc
    except Exception as exc:
        logger.exception("Compound feedback failed: %s", request.skill_name)
        raise HTTPException(status_code=500, detail="Feedback cycle failed") from exc


class CompoundHealthResponse(BaseModel):
    total_executions: int = 0
    total_refinements: int = 0
    total_cycles: int = 0
    success_rate: float = 0.0
    total_tokens: int = 0
    model_usage: dict[str, int] = {}
    top_refined_skills: list[dict[str, Any]] = []
    compound_score_trend: list[dict[str, Any]] = []


@app.get("/compound/health", response_model=CompoundHealthResponse)
async def compound_health():
    """Return compound system health from the metrics collector."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    return CompoundHealthResponse(**collector.to_health_dict())


class CompoundHistoryResponse(BaseModel):
    skill_name: str
    executions: int = 0
    refinements: int = 0
    cycles: int = 0
    total_tokens: int = 0
    success_rate: float = 0.0
    latest_execution: float | None = None
    latest_refinement: float | None = None


@app.get(
    "/compound/history/{skill_name}",
    response_model=CompoundHistoryResponse,
)
async def compound_history(skill_name: str):
    """Return compound execution history for a specific skill."""
    from cohezion.compound.metrics import get_collector

    collector = get_collector()
    history = collector.skill_history(skill_name)
    return CompoundHistoryResponse(**history)


# Register research endpoints (late import to avoid circular dependencies)
try:
    from cohezion.api.research_endpoints import router as research_router

    app.include_router(research_router)
except ImportError:
    pass  # research module not available

# Register universe simulation endpoints
try:
    from cohezion.api.services.universe import universe_router

    app.include_router(universe_router, prefix="/api/universe")
except ImportError:
    pass  # universe module not available
