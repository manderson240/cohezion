"""Marimo Walkthroughs MCP Server — expose walkthrough analysis as MCP tools.

FastMCP bridge that makes the three interactive walkthrough notebooks
callable programmatically from Claude Code or any MCP client.

Tools exposed:
  • compound_loop_metrics  — compute compound loop KPIs over N cycles
  • flume_latent_summary   — report latent space geometry for given params
  • thermodynamic_gravity  — evaluate ThermodynamicGravity at given ε
  • lemonade_walkthrough_chat — ask a context-aware local agent about any walkthrough

Usage (stdio):
    uv run python -m cohezion.mcp.marimo_walkthroughs_mcp

Register in mcp_servers.json:
    "marimo-walkthroughs": {
        "command": "/path/to/.venv/bin/python",
        "args": ["-m", "cohezion.mcp.marimo_walkthroughs_mcp"],
        "env": {"LEMONADE_URL": "http://localhost:13305"}
    }
"""

from __future__ import annotations

import logging
import math
import os
import random
import sys

import httpx
from fastmcp import FastMCP


logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("marimo-walkthroughs-mcp")

app = FastMCP("marimo-walkthroughs")

_LEMONADE_URL = os.getenv("LEMONADE_URL", "http://localhost:13305")


# ── helpers ───────────────────────────────────────────────────────────────────


def _lemonade_base() -> str:
    return os.getenv("LEMONADE_URL", _LEMONADE_URL).rstrip("/")


async def _lemonade_chat(system: str, user: str, model: str, max_tokens: int = 600) -> str:
    """Call Lemonade chat completions endpoint."""
    url = f"{_lemonade_base()}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"[Lemonade error: {exc}]"


# ── Tool 1: compound loop metrics ─────────────────────────────────────────────


@app.tool()
async def compound_loop_metrics(
    n_cycles: int = 50,
    seed: int = 42,
) -> dict:
    """Compute compound loop KPIs over N execution cycles.

    Simulates the Cohezion compound engineering loop (ExecutionOrchestrator →
    RetrospectionEngine → SkillRefiner) and returns statistics on quality score,
    semantic cache hit rate, tier latency, and SkillRefiner confidence.

    Args:
        n_cycles: Number of simulated cycles (10–500).
        seed: Random seed for reproducibility.

    Returns:
        Dictionary with mean/std for each metric, plus the full time series.
    """
    n_cycles = max(10, min(500, n_cycles))
    random.seed(seed)

    quality, cache_hits, latency_ms, confidence = [], [], [], []
    q = random.uniform(0.2, 0.8)
    tier_weights = [(0.7, 24.0), (0.2, 200.0), (0.1, 800.0)]

    for i in range(n_cycles):
        # Quality: mean-reversion to HIHO 0.5
        q = q + 0.03 * (0.5 - q) + random.gauss(0, 0.04)
        quality.append(max(0.0, min(1.0, q)))

        # Cache: exponential ramp
        cache_hits.append(
            min(0.95, 0.1 + 0.85 * (1 - math.exp(-i / (n_cycles * 0.3))) + random.gauss(0, 0.02))
        )

        # Latency: probabilistic tier selection
        r = random.random()
        cumulative = 0.0
        for w, base in tier_weights:
            cumulative += w
            if r < cumulative:
                latency_ms.append(base + random.gauss(0, base * 0.1))
                break

        # Confidence: climbs with accumulated data
        confidence.append(min(0.95, 0.4 + 0.55 * (i / n_cycles) + random.gauss(0, 0.03)))

    def _stats(series: list[float]) -> dict:
        n = len(series)
        mean = sum(series) / n
        std = math.sqrt(sum((x - mean) ** 2 for x in series) / n)
        return {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "min": round(min(series), 4),
            "max": round(max(series), 4),
        }

    return {
        "n_cycles": n_cycles,
        "seed": seed,
        "quality_score": _stats(quality),
        "cache_hit_rate": _stats(cache_hits),
        "latency_ms": _stats(latency_ms),
        "skill_confidence": _stats(confidence),
        "hiho_equilibrium": 0.5,
        "final_quality": round(quality[-1], 4),
        "final_cache_rate": round(cache_hits[-1], 4),
    }


# ── Tool 2: FLUME latent space summary ────────────────────────────────────────


@app.tool()
async def flume_latent_summary(
    n_points: int = 200,
    n_clusters: int = 4,
    latent_dim: int = 256,
    beta: float = 0.010,
) -> dict:
    """Summarise FLUME latent space geometry for given hyperparameters.

    Samples synthetic latent vectors with cluster structure and computes
    intra-cluster cohesion, inter-cluster separation, and posterior health
    indicators (KL collapse risk based on β threshold).

    Args:
        n_points: Number of sample points.
        n_clusters: Number of semantic clusters.
        latent_dim: Dimensionality of the latent space (default 256).
        beta: KL weight (β). Collapse risk if β > 0.015.

    Returns:
        Dict with geometry statistics and collapse risk assessment.
    """
    random.seed(7)
    D = latent_dim
    K = n_clusters
    N = n_points

    centers = [[random.gauss(0, 2.0) for _ in range(D)] for _ in range(K)]
    vectors_by_cluster: list[list[list[float]]] = [[] for _ in range(K)]

    for i in range(N):
        k = i % K
        vec = [centers[k][d] + random.gauss(0, 0.6) for d in range(D)]
        norm = math.sqrt(sum(v**2 for v in vec)) or 1.0
        vectors_by_cluster[k].append([v / norm for v in vec])

    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(ai * bi for ai, bi in zip(a, b))
        na = math.sqrt(sum(ai**2 for ai in a)) or 1.0
        nb = math.sqrt(sum(bi**2 for bi in b)) or 1.0
        return dot / (na * nb)

    # Intra-cluster cohesion: mean pairwise cosine within each cluster
    cohesion_per_cluster = []
    for k in range(K):
        vecs = vectors_by_cluster[k][:20]  # sample for speed
        if len(vecs) < 2:
            continue
        sims = [
            _cosine(vecs[i], vecs[j]) for i in range(len(vecs)) for j in range(i + 1, len(vecs))
        ]
        cohesion_per_cluster.append(sum(sims) / len(sims))

    mean_cohesion = sum(cohesion_per_cluster) / len(cohesion_per_cluster)

    # Inter-cluster separation: mean cosine between cluster centroids
    centroids = [
        [sum(v[d] for v in vectors_by_cluster[k]) / len(vectors_by_cluster[k]) for d in range(D)]
        for k in range(K)
    ]
    sep_sims = [_cosine(centroids[i], centroids[j]) for i in range(K) for j in range(i + 1, K)]
    mean_separation = 1.0 - (sum(sep_sims) / len(sep_sims))  # higher = more separated

    collapse_risk = beta > 0.015
    kl_health = "COLLAPSED" if beta >= 0.020 else ("RISK" if collapse_risk else "HEALTHY")

    return {
        "latent_dim": D,
        "n_clusters": K,
        "n_points": N,
        "beta": beta,
        "kl_health": kl_health,
        "collapse_risk": collapse_risk,
        "optimal_beta_max": 0.010,
        "collapse_threshold": 0.020,
        "mean_intra_cluster_cosine": round(mean_cohesion, 4),
        "mean_inter_cluster_separation": round(mean_separation, 4),
        "harness_invariant_A3": beta <= 0.010,
    }


# ── Tool 3: thermodynamic gravity ─────────────────────────────────────────────


@app.tool()
async def thermodynamic_gravity(
    epsilon: float = 0.0,
    temperature: float = 1.0,
    n_legs: int = 3,
) -> dict:
    """Evaluate the ThermodynamicGravity model at given Lorentz violation parameter ε.

    Implements the analytic approximation from Isichei & Magueijo 2026
    (arXiv:2511.22221). GR corresponds to ε = 0 (degenerate Otto cycle);
    ε > 0 generates late-time cosmic acceleration.

    Args:
        epsilon: Lorentz violation parameter (0.0 = standard GR, 1.0 = maximal).
        temperature: Temperature in natural units.
        n_legs: Number of work-producing legs in the Otto cycle.

    Returns:
        Dict with acceleration term, entropy gain, GR status, and harness check.
    """
    epsilon = max(0.0, min(1.0, epsilon))

    # Try to use the real cohezion module
    try:
        _src = __import__("pathlib").Path(__file__).parent.parent.parent
        if str(_src) not in sys.path:
            sys.path.insert(0, str(_src))
        from cohezion.physics.thermodynamic_gravity import (
            OttoWorkLeg as _OWL,
        )
        from cohezion.physics.thermodynamic_gravity import (  # type: ignore[import]
            ThermodynamicGravity as _TG,
        )

        legs = [
            _OWL(lorentz_violation=epsilon, entropy_flux=math.sin(math.pi * (i + 1) / n_legs) * 0.5)
            for i in range(n_legs)
        ]
        model = _TG(temperature=temperature, work_legs=legs)
        accel = model.acceleration_term()
        measured_eps = model.lorentz_violation_parameter()
        is_gr = model.is_standard_gr()
        source = "cohezion.physics"
    except Exception:
        # Analytic fallback
        accel = sum(epsilon * math.sin(math.pi * (i + 1) / n_legs) * 0.5 for i in range(n_legs))
        measured_eps = epsilon
        is_gr = epsilon < 1e-9
        source = "analytic"

    return {
        "epsilon": epsilon,
        "temperature": temperature,
        "n_legs": n_legs,
        "acceleration_term": round(accel, 8),
        "entropy_gain": round(accel / temperature, 8),
        "is_standard_gr": is_gr,
        "lorentz_violation_parameter": round(measured_eps, 6),
        "harness_invariant_LV1": measured_eps == 0.0,
        "source": source,
        "cosmogony_step": "Step3→4: SO(12)→FabricDifferentiation" if epsilon > 0 else "GR baseline",
    }


# ── Tool 4: walkthrough chat ──────────────────────────────────────────────────


@app.tool()
async def lemonade_walkthrough_chat(
    question: str,
    topic: str = "compound_loop",
    model: str = "llama3.2-1b-FLM",
) -> str:
    """Ask the local Lemonade agent a question about any Cohezion walkthrough topic.

    Runs on the AMD local stack ($0). Routes to the appropriate system prompt
    based on the topic.

    Args:
        question: The question to ask.
        topic: One of "compound_loop", "flume", "thermodynamic_gravity".
        model: Lemonade model ID (default: llama3.2-1b-FLM, 42 TPS on XDNA2).

    Returns:
        The agent's response string.
    """
    system_prompts = {
        "compound_loop": (
            "You are an expert in Cohezion compound AI engineering loops. "
            "Answer concisely with reference to HIHO (Half-In-Half-Out) "
            "equilibrium, semantic cache, and tiered AMD inference."
        ),
        "flume": (
            "You are an expert in β-VAE latent space geometry, FLUME "
            "(Fluid Latent Understanding through Manifold Encoding), "
            "and KL regularisation. Key invariants: β ≤ 0.01, 2-layer decoder, hd=4096."
        ),
        "thermodynamic_gravity": (
            "You are an expert in thermodynamic gravity and the Isichei-Magueijo 2026 "
            "PRL paper (arXiv:2511.22221). Explain ε Lorentz violation → late-time "
            "acceleration via non-degenerate Otto cycles. Connect to Cohezion cosmogony "
            "Step 3→4: SO(12) vacuum → Fabric Differentiation."
        ),
    }
    system = system_prompts.get(topic, system_prompts["compound_loop"])
    return await _lemonade_chat(system, question, model)


# ── entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run()
