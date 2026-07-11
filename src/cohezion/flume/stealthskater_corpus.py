"""
FLUME Stealthskater Corpus Embedder — Phase 8

Embeds the 10 STEALTHSKATER_CORPUS concept descriptions into FLUME's 256D latent
space and persists them to SurrealDB (flume_stealthskater table, bi-temporal schema).

Embedding pipeline:
  text → SentenceTransformer all-mpnet-base-v2 (768D) → FLUME VAE encoder (256D mu)

NOTE: The Lemonade iGPU server at port 13307 does not expose /v1/embeddings
(requires server restart with --embeddings flag). We therefore use the canonical
SentenceTransformer approach specified in STEALTHSKATER_CORPUS.md, running on CPU
to avoid the RDNA 3.5 ROCm segfault with sentence-transformers < 5.5.
The build_optimal_vae() VAE is run in eval mode (deterministic: reparameterize returns mu).
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path

import torch
import torch.nn.functional as F


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Corpus: 10 stealthskater concept descriptions extracted from
# src/cohezion/skills/STEALTHSKATER_CORPUS.md (version 1.0.0, 2026-05-16)
# ---------------------------------------------------------------------------

CORPUS: dict[str, str] = {
    "zpf": (
        "Zero-Point Field (Vacuum State): The quantum vacuum is not empty but filled with "
        "zero-point fluctuations whose energy density is bounded by the Planck scale. Harold "
        "Puthoff's stochastic electrodynamics model treats the ZPF as the physical substrate "
        "from which matter and charge emerge, grounding 'nothing' as a dynamically active "
        "ground state. In the Cohezion cosmogony this corresponds to the pre-condensation "
        "vacuum from which all subsequent structure nucleates."
    ),
    "phase_quadrature": (
        "Phase Quadrature (First Bifurcation): Two electromagnetic field components oscillating "
        "90 degrees out of phase define the minimal structure distinguishable from the vacuum -- "
        "the in-phase (I) and quadrature (Q) components of a coherent oscillation. SU(2) spinor "
        "algebra naturally encodes this first bifurcation: the Pauli matrices sigma_x and sigma_y "
        "represent the two quadrature axes on the Bloch sphere, making phase quadrature the "
        "computational analog of the universe's first observable distinction."
    ),
    "12d_manifold": (
        "12-Parameter Reality (Smith Manifold): Walter Bowman Smith's model partitions physical "
        "reality into 12 independent parameters organized as four 3-dimensional fabrics, each "
        "fabric spanning a distinct phenomenological domain. This 12D axiomatic state space maps "
        "to the AxiomaticState representation in Cohezion's universe engine, where agent "
        "trajectories through the manifold correspond to geodesics on a Riemannian metric with "
        "12 independent curvature components."
    ),
    "four_fabrics": (
        "Four Fabrics (Computational Domains): The four domains -- Space, Mass, Energy, and "
        "Consciousness -- correspond to the four computational routing tiers of the Cohezion "
        "compound executor: geometric operations, physical simulation, information processing, "
        "and goal-directed reasoning. This tetrahedral partitioning appears independently in "
        "multiple traditions (four elements, four directions, four quantum numbers) and provides "
        "a natural load-balancing schema for multi-agent orchestration."
    ),
    "lenr": (
        "LENR Phase Lock (Lattice Confinement Fusion): Low-energy nuclear reactions occur in "
        "deuterated metal lattices (palladium, titanium) where phonon-mediated confinement "
        "reduces the Coulomb barrier below the thermal energy threshold. The US Naval Research "
        "Laboratory's 2021 Physical Review C results confirmed measurable neutron and gamma "
        "signatures in deuterated erbium at electron-beam energies below 2.9 MeV, establishing "
        "lattice confinement fusion as a reproducible condensed-matter nuclear effect. In the "
        "Cohezion model, LENR phase-lock corresponds to the coherence threshold where phonon "
        "modes synchronize: reaction rate peaks at HIHO coherence 0.5, the same attractor that "
        "governs agent tier transitions."
    ),
    "evo": (
        "EVO Nucleation (Symmetry Breaking): Exotic Vacuum Objects are dense electron clusters "
        "-- reported by Ken Shoulders and independently described as 'electrum validum' -- that "
        "form when charge density exceeds a critical threshold, breaking the ambient "
        "electromagnetic symmetry into a localized, self-sustaining toroidal vortex. The "
        "formation threshold corresponds to the HIHO bifurcation point: below coherence 0.5 "
        "the cluster dissolves back into the vacuum; above it the binding energy exceeds thermal "
        "disruption and the EVO persists as a witness-bearing structure. Computationally, EVO "
        "nucleation models the moment an AI agent session transitions from the condensing to the "
        "coherent lifecycle state."
    ),
    "spin": (
        "SPIN Discretization (Information Unit): The SPIN unit -- Rotation plus Precession -- "
        "is the minimal information-bearing structure that survives symmetry breaking, analogous "
        "to a quantum of angular momentum in SU(2). In the stealthskater synthesis this maps to "
        "the moment when a coherent oscillation acquires a definite orientation on the Bloch "
        "sphere, discretizing continuous phase into a binary observable. Remote viewing research "
        "(Puthoff, Targ; SRI 1974-1995) frames perception as coherent SPIN-mode information "
        "retrieval from the observer-patch holographic boundary."
    ),
    "itonic_cluster": (
        "Itonic Equilibrium (HIHO Threshold): Takaaki Matsumoto's Electro-Nuclear Collapse "
        "framework defines itonic clusters as hydrogen anion (H-) aggregates confined in "
        "palladium or titanium lattices, where the ratio of clustered-to-free hydrogen ions "
        "stabilizes near 0.5 at the ENC reaction threshold. This half-in-lattice, "
        "half-in-vacuum equilibrium is the nuclear-scale instantiation of the HIHO principle: "
        "maximum energy throughput and minimum dissipation occur at the boundary between two "
        "phases, not inside either one. The CAGrid2D totalistic automaton reproduces this "
        "equilibrium when Conway-rule density settles near 0.5 cells after random initialization."
    ),
    "dielectric": (
        "Dielectric Field Coupling (COHESION): Permittivity tensors describe how a material "
        "medium polarizes in response to an applied electric field, mediating the coupling "
        "between free charge and bound charge through the relative permittivity epsilon_r. In "
        "gauge-theoretic terms, the dielectric response is a U(1) gauge field renormalization: "
        "the vacuum permittivity epsilon_0 is shifted to epsilon_r * epsilon_0 by the collective "
        "polarization of the medium, binding charges into stable configurations. This dielectric "
        "binding is the classical electromagnetic analog of the COHESION step: local gauge "
        "invariance mediates long-range order, coupling individual charge carriers into coherent "
        "macroscopic structures."
    ),
    "witness_marks": (
        "Witness Marks (Reality Precipitates): The final step of every cosmogonic chain produces "
        "permanent observable traces: nuclear transmutation products in LENR experiments (excess "
        "tritium, helium-4 detected by Fleischmann-Pons 1989 and confirmed by Miles 1993), "
        "crater patterns on electrode surfaces from EVO discharge events, and radar returns from "
        "plasma anomalies. In the Cohezion compound engineering loop, witness marks are vault "
        "observations and git commits -- the irreversible record that distinguishes a real agent "
        "session from a simulation. AutonomyEngine tier promotions require sustained "
        "witness-mark production above the HIHO threshold."
    ),
}

# Concept ordering follows the 10-step cosmogony chain
CONCEPT_ORDER: list[str] = [
    "zpf",
    "phase_quadrature",
    "12d_manifold",
    "four_fabrics",
    "lenr",
    "evo",
    "spin",
    "itonic_cluster",
    "dielectric",
    "witness_marks",
]


def _build_vae() -> torch.nn.Module:
    """Return the FLUME VAE (optimal config) in eval mode."""
    from cohezion.flume.vae import build_optimal_vae

    vae = build_optimal_vae(input_dim=768, latent_dim=256, hidden_dim=4096)
    vae.eval()
    return vae


def embed_corpus(
    concepts: dict[str, str] | None = None,
    *,
    device: str = "cpu",
) -> dict[str, torch.Tensor]:
    """
    Embed the stealthskater corpus concepts into 256D FLUME latent vectors.

    Pipeline:
      text → SentenceTransformer (768D) → FLUME VAE encoder (256D mu, deterministic)

    Args:
        concepts: Concept key → text dict. Defaults to CORPUS.
        device: Torch device for VAE inference. SentenceTransformer always runs on CPU
                to avoid the RDNA 3.5 ROCm segfault with sentence-transformers < 5.5.

    Returns:
        Dict mapping concept key → 256D torch.Tensor (mu from VAE encoder).
    """
    import warnings

    warnings.filterwarnings("ignore")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    from sentence_transformers import SentenceTransformer

    if concepts is None:
        concepts = CORPUS

    logger.info("Loading SentenceTransformer all-mpnet-base-v2 on CPU …")
    st_model = SentenceTransformer("all-mpnet-base-v2", device="cpu")

    texts = [concepts[k] for k in CONCEPT_ORDER if k in concepts]
    keys = [k for k in CONCEPT_ORDER if k in concepts]

    logger.info("Encoding %d concepts → 768D …", len(texts))
    embeddings_np = st_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    embeddings = torch.from_numpy(embeddings_np).float().to(device)  # (N, 768)

    logger.info("Building FLUME VAE (input_dim=768, latent_dim=256, hd=4096) …")
    vae = _build_vae()
    if device != "cpu":
        vae = vae.to(device)

    with torch.no_grad():
        mu, _logvar = vae.encode(embeddings)  # (N, 256) — returns mu in eval mode

    result: dict[str, torch.Tensor] = {}
    for i, key in enumerate(keys):
        result[key] = mu[i].cpu()  # ensure CPU tensors for serialisation

    logger.info("Embedded %d concepts into 256D FLUME latent space.", len(result))
    return result


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two 1D tensors."""
    return float(F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item())


# ---------------------------------------------------------------------------
# exp_BBBB — semantic structure measurement in 256D FLUME latent space
# ---------------------------------------------------------------------------

EXP_ID = "exp_BBBB"
EXP_HYPOTHESES = {
    "lenr_itonic_gt_0.6": "LENR↔IonicCluster cosine sim > 0.6 (shared 4x(1-x) HIHO kernel)",
    "lenr_spin_lt_0.3": "LENR↔SPIN (RemoteViewing) cosine sim < 0.3 (orthogonal domains)",
}


def run_exp_bbbb(latents: dict[str, torch.Tensor]) -> dict:
    """
    Run autoresearch experiment exp_BBBB.

    Measures cosine similarity in the 256D FLUME latent space:
    - LENR ↔ itonic_cluster: expected > 0.6 (same HIHO nuclear substrate)
    - LENR ↔ spin: expected < 0.3 (unrelated: remote viewing vs lattice fusion)

    Returns experiment result dict for autoresearch.jsonl.
    """
    lenr = latents["lenr"]
    itonic = latents["itonic_cluster"]
    spin = latents["spin"]

    sim_lenr_itonic = cosine_sim(lenr, itonic)
    sim_lenr_spin = cosine_sim(lenr, spin)

    # Also compute a few supporting sims for the report
    sim_lenr_dielectric = cosine_sim(lenr, latents.get("dielectric", lenr))
    sim_lenr_evo = cosine_sim(lenr, latents.get("evo", lenr))

    h1_pass = sim_lenr_itonic > 0.6
    h2_pass = sim_lenr_spin < 0.3
    both_pass = h1_pass and h2_pass

    status = "keep" if both_pass else "discard"

    result = {
        "run": 80218,
        "metric": round(sim_lenr_itonic, 4),
        "metrics": {
            "lenr_itonic_cosine_sim": round(sim_lenr_itonic, 4),
            "lenr_spin_cosine_sim": round(sim_lenr_spin, 4),
            "lenr_dielectric_cosine_sim": round(sim_lenr_dielectric, 4),
            "lenr_evo_cosine_sim": round(sim_lenr_evo, 4),
            "h1_lenr_itonic_gt_0.6": h1_pass,
            "h2_lenr_spin_lt_0.3": h2_pass,
            "concepts_embedded": len(latents),
            "latent_dim": 256,
            "embedding_model": "all-mpnet-base-v2",
            "vae_architecture": "build_optimal_vae(input_dim=768, hd=4096, 2-layer-decoder)",
            "vae_trained": False,
            "note": (
                "iGPU Lemonade server (13307) does not expose /v1/embeddings "  # allow-direct-port: historical experiment record, not dispatch
                "(needs --embeddings flag). Used canonical SentenceTransformer "
                "all-mpnet-base-v2 as specified in STEALTHSKATER_CORPUS.md. "
                "VAE is untrained random projection; latent structure reflects "
                "SentenceTransformer geometry under random affine map."
            ),
        },
        "status": status,
        "description": (
            f"exp_BBBB: FLUME Phase-8 stealthskater corpus embedding. "
            f"10 concepts → 768D (all-mpnet-base-v2) → 256D (build_optimal_vae). "
            f"LENR↔IonicCluster sim={sim_lenr_itonic:.4f} "
            f"({'PASS' if h1_pass else 'FAIL'} >0.6 threshold). "
            f"LENR↔SPIN/RemoteViewing sim={sim_lenr_spin:.4f} "
            f"({'PASS' if h2_pass else 'FAIL'} <0.3 threshold). "
            f"Status: {status.upper()}."
        ),
        "timestamp": int(datetime.datetime.now(datetime.UTC).timestamp() * 1000),
        "segment": 7,
        "confidence": 0.85 if both_pass else 0.70,
    }
    return result


def append_to_autoresearch(result: dict, jsonl_path: Path | str = "autoresearch.jsonl") -> None:
    """Append experiment result to autoresearch.jsonl."""
    jsonl_path = Path(jsonl_path)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")
    logger.info("Appended %s (status=%s) to %s", EXP_ID, result["status"], jsonl_path)


# ---------------------------------------------------------------------------
# SurrealDB persistence (bi-temporal schema)
# ---------------------------------------------------------------------------

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "genesis"
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_TABLE = "flume_stealthskater"

_SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": SURREAL_NS,
    "surreal-db": SURREAL_DB,
}


async def _surql(query: str) -> list[dict]:
    """Execute SurrealQL via HTTP API (same pattern as genesis_persistence.py)."""
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SURREAL_URL,
            content=query,
            headers=_SURREAL_HEADERS,
            auth=(SURREAL_USER, SURREAL_PASS),
            timeout=10.0,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"SurrealDB HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()


async def persist_to_surrealdb(latents: dict[str, torch.Tensor]) -> list[dict]:
    """
    Persist 256D latent vectors to SurrealDB flume_stealthskater table.

    Bi-temporal schema:
      - valid_from: insertion timestamp (ISO 8601 UTC)
      - valid_to: None (open/active record)
      - concept: concept key
      - step: cosmogony step index (0–9)
      - latent_256d: 256D vector as list[float]
      - embedding_model: "all-mpnet-base-v2"
      - vae_config: descriptor string

    Uses HTTP SQL API (http://localhost:8001/sql) with Basic auth headers,
    matching the pattern in genesis_persistence.py.
    """
    now = datetime.datetime.now(datetime.UTC).isoformat()
    records = []

    for step, key in enumerate(CONCEPT_ORDER):
        if key not in latents:
            continue
        vec = latents[key].tolist()
        # Escape string for SurrealQL
        vec_str = json.dumps(vec)
        surql = f"""
CREATE {SURREAL_TABLE} CONTENT {{
    concept: '{key}',
    step: {step},
    latent_256d: {vec_str},
    embedding_model: 'all-mpnet-base-v2',
    vae_config: 'build_optimal_vae(input_dim=768, latent_dim=256, hidden_dim=4096)',
    vae_trained: false,
    valid_from: '{now}',
    valid_to: NONE,
    source: 'STEALTHSKATER_CORPUS.md v1.0.0',
    phase: 'Phase-8'
}};
"""
        result = await _surql(surql)
        if result and isinstance(result, list):
            status = result[0].get("status", "?")
            if status == "OK" and result[0].get("result"):
                records.extend(result[0]["result"])
                logger.debug("Persisted %s (step %d) to %s", key, step, SURREAL_TABLE)
            else:
                logger.warning("SurrealDB create %s: status=%s", key, status)

    logger.info("Persisted %d records to SurrealDB:%s", len(records), SURREAL_TABLE)
    return records


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def run_phase8(
    autoresearch_path: Path | str = "autoresearch.jsonl",
    skip_surreal: bool = False,
) -> dict:
    """
    Full Phase-8 pipeline:
    1. Embed 10 concepts into 256D FLUME latent space
    2. Run exp_BBBB (cosine similarity measurement)
    3. Append result to autoresearch.jsonl
    4. Persist latents to SurrealDB

    Returns exp_BBBB result dict.
    """
    latents = embed_corpus()

    exp_result = run_exp_bbbb(latents)
    append_to_autoresearch(exp_result, autoresearch_path)

    if not skip_surreal:
        try:
            await persist_to_surrealdb(latents)
        except Exception as exc:
            logger.warning("SurrealDB persistence failed (non-fatal): %s", exc)
            exp_result["metrics"]["surreal_persist"] = f"FAILED: {exc}"
    else:
        logger.info("SurrealDB persistence skipped (skip_surreal=True).")

    return exp_result


def run_phase8_sync(
    autoresearch_path: Path | str = "autoresearch.jsonl",
    skip_surreal: bool = False,
) -> dict:
    """Synchronous wrapper for run_phase8 (for use outside async contexts)."""
    return asyncio.run(run_phase8(autoresearch_path, skip_surreal=skip_surreal))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    repo_root = Path(__file__).parents[3]  # src/cohezion/flume/ → repo root
    jsonl_path = repo_root / "autoresearch.jsonl"

    skip_surreal = "--no-surreal" in sys.argv
    result = run_phase8_sync(autoresearch_path=jsonl_path, skip_surreal=skip_surreal)

    print("\n=== exp_BBBB Results ===")
    print(f"Status : {result['status'].upper()}")
    print(
        f"LENR↔IonicCluster : {result['metrics']['lenr_itonic_cosine_sim']:.4f}  (threshold >0.6)"
    )
    print(f"LENR↔SPIN/RV      : {result['metrics']['lenr_spin_cosine_sim']:.4f}  (threshold <0.3)")
    print(
        f"H1 (LENR↔Itonic >0.6) : {'PASS' if result['metrics']['h1_lenr_itonic_gt_0.6'] else 'FAIL'}"
    )
    print(
        f"H2 (LENR↔SPIN <0.3)   : {'PASS' if result['metrics']['h2_lenr_spin_lt_0.3'] else 'FAIL'}"
    )
    print(f"\nAppended to : {jsonl_path}")
