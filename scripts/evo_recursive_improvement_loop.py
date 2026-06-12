#!/usr/bin/env python3
"""EVO Recursive Learning Improvement Loop — Cohezion continuous self-improvement.

Iterates over a curated set of PRIME skills, runs EVO physics traces for each,
stores ExperientialVoyage records in SurrealDB (evo_journey table), and calls
SkillRefiner on voyages that meet the Constitution phi ≥ 0.3 gate.

Architecture per voyage:
  AgenticEVO.hiho_step()           — HIHO physics (256D latent convergence)
  >> TraceMonad pipeline           — immutable state threading
  >> modality dispatch             — text + audio (kokoro) + image (SD-Turbo)
  >> JourneyTracker.track_evo_step — 12D FLUME trajectory point
  complete_journey()               — SurrealDB + Obsidian vault dual-write
  SkillRefiner.refine()            — PRIME skill update (phi ≥ 0.3 gate)

Skill taxonomy (arxiv:2606.05405 — ALE, Agents' Last Exam):
  Skill journeys map to the GCUA 5-layer model:
    Brain  — LLM reasoning/planning          (Near-Term:    3 steps)
    Eyes   — visual/latent-space perception  (Full-Spectrum: 5 steps)
    Body   — orchestration/control flow      (Full-Spectrum: 5 steps)
    Hands  — structured tool invocation      (Full-Spectrum: 5 steps)
    Feet   — runtime substrate/physics       (Last-Exam:    8 steps)
    Full-GCUA — all 5 layers integrated      (Last-Exam:    8 steps)

  ALE gate-and-score maps exactly to: phi ≥ 0.3 gate → phi_distribution continuous score.

Usage:
    uv run python scripts/evo_recursive_improvement_loop.py
    uv run python scripts/evo_recursive_improvement_loop.py --rounds 3 --steps 5
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("evo_loop")

# ── SurrealDB helper ──────────────────────────────────────────────────────────
_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}


def _surql(query: str) -> list:
    import base64

    auth = base64.b64encode(b"root:root").decode()
    req = urllib.request.Request(
        _SURREAL_URL,
        data=query.encode(),
        headers={**_SURREAL_HEADERS, "Authorization": f"Basic {auth}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.load(resp)


def _ensure_evo_journey_table() -> None:
    """Create evo_journey table if it doesn't exist (schema-flexible SurrealDB)."""
    _surql("""
        DEFINE TABLE IF NOT EXISTS evo_journey SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS voyage_id    ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS agent_id     ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS journey_id   ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS skill_id     ON evo_journey TYPE string;
        DEFINE FIELD IF NOT EXISTS phi_score    ON evo_journey TYPE float;
        DEFINE FIELD IF NOT EXISTS modalities   ON evo_journey TYPE array;
        DEFINE FIELD IF NOT EXISTS step_count   ON evo_journey TYPE int;
        DEFINE FIELD IF NOT EXISTS duration_s   ON evo_journey TYPE float;
        DEFINE FIELD IF NOT EXISTS refined      ON evo_journey TYPE bool;
        DEFINE FIELD IF NOT EXISTS valid_from   ON evo_journey TYPE datetime;
        DEFINE FIELD IF NOT EXISTS valid_to     ON evo_journey TYPE option<datetime>;
        DEFINE FIELD IF NOT EXISTS latent_snap  ON evo_journey TYPE array;
        DEFINE FIELD IF NOT EXISTS gate_prob   ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist              ON evo_journey TYPE option<object>;
        DEFINE FIELD IF NOT EXISTS phi_dist.bins         ON evo_journey TYPE option<array>;
        DEFINE FIELD IF NOT EXISTS phi_dist.probs        ON evo_journey TYPE option<array>;
        DEFINE FIELD IF NOT EXISTS phi_dist.point_estimate ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist.gate_prob    ON evo_journey TYPE option<float>;
        DEFINE FIELD IF NOT EXISTS phi_dist.expected_phi ON evo_journey TYPE option<float>;
    """)
    logger.info("evo_journey table ready")


def _query_phi_trend(skill_id: str, n_recent: int = 10) -> float | None:
    """Return mean φ across the last n_recent voyages for skill_id.

    Used to adapt σ: skills already in healthy φ range get tighter perturbations;
    skills near the gate floor get wider ones.  Returns None when SurrealDB is
    unavailable or the skill has no history yet.
    """
    try:
        results = _surql(
            f"SELECT phi_score, valid_from FROM evo_journey "
            f"WHERE skill_id = '{skill_id}' "
            f"ORDER BY valid_from DESC LIMIT {n_recent};"
        )
        rows = results[0].get("result", [])
        if rows:
            phis = [float(r["phi_score"]) for r in rows if "phi_score" in r]
            if phis:
                return sum(phis) / len(phis)
    except Exception:
        pass
    return None


def _load_cerebellum_context(skill_id: str) -> str:
    """Return most-recent insight from vault cerebellum notes for this skill.

    Cerebellum notes are written by SkillRefiner → KnowledgeBridge after each
    refined voyage.  Feeding the insight back into step_desc closes the
    write-only vault loop: the next trace step sees what the previous voyage
    learned.

    Returns a compact string like '[prev: HIHO coherence above median]' or ''
    if no note exists yet.
    """
    cerebellum_dir = _VAULT_ROOT / "cerebellum"
    # KnowledgeBridge writes with underscores: 2026-06-12-skill-refinement-npu_tier_optimization_prime.md
    skill_slug = skill_id.lower()
    matches = sorted(cerebellum_dir.glob(f"*-skill-refinement-{skill_slug}.md"))
    if not matches:
        return ""
    try:
        text = matches[-1].read_text()
        for line in text.splitlines():
            if "Insight:" in line:
                after = line.split("Insight:", 1)[1]
                insight = after.split("Coherence:")[0].strip().rstrip(".")
                if insight:
                    return f"[prev: {insight[:80]}]"
    except Exception:
        pass
    return ""


def _store_voyage(voyage, skill_id: str, refined: bool, step_count: int) -> None:
    """Write voyage to SurrealDB evo_journey table."""
    phi_dist_json = "NONE"
    gate_prob_val = "NONE"
    if voyage.phi_distribution is not None:
        phi_dist_json = json.dumps(voyage.phi_distribution.as_dict())
        gate_prob_val = f"{voyage.phi_distribution.gate_probability():.6f}"
    q = f"""
        CREATE evo_journey SET
            voyage_id  = '{voyage.voyage_id}',
            agent_id   = '{voyage.agent_id}',
            journey_id = '{voyage.journey_id}',
            skill_id   = '{skill_id}',
            phi_score  = {voyage.phi_score:.6f},
            modalities = {json.dumps(voyage.modalities_used)},
            step_count = {step_count},
            duration_s = {voyage.duration_seconds:.4f},
            refined    = {str(refined).lower()},
            valid_from = time::now(),
            valid_to   = NONE,
            latent_snap = {json.dumps(voyage.latent_snapshot[:8])},
            gate_prob  = {gate_prob_val},
            phi_dist   = {phi_dist_json};
    """
    _surql(q)


# ── Obsidian vault write ──────────────────────────────────────────────────────
_VAULT_ROOT = Path.home() / "vaults" / "cohezion-vault"


def _vault_write_voyage(
    voyage,
    skill_id: str,
    refined: bool,
    steps_summary: list[dict],
    ale_layer: str = "—",
    ale_tier: str = "—",
    research_full: str = "",
) -> None:
    """Write ExperientialVoyage to Obsidian vault as a structured experiment note.

    Writes to vault/experiments/evo/ — vault MCP is unavailable in this session so
    we write directly. This is an intentional exception: the user explicitly requested
    vault storage and the alternative is no storage at all.
    """
    exp_dir = _VAULT_ROOT / "experiments" / "evo"
    exp_dir.mkdir(parents=True, exist_ok=True)

    date_str = time.strftime("%Y-%m-%d")
    fname = f"{date_str}-{skill_id.lower().replace('_', '-')}-{voyage.voyage_id[:8]}.md"
    fpath = exp_dir / fname

    lines = [
        "---",
        f"type: evo_voyage",
        f"voyage_id: {voyage.voyage_id}",
        f"agent_id: {voyage.agent_id}",
        f"journey_id: {voyage.journey_id}",
        f"skill_id: {skill_id}",
        f"phi_score: {voyage.phi_score:.4f}",
        f"modalities: {voyage.modalities_used}",
        f"refined: {str(refined).lower()}",
        f"duration_s: {voyage.duration_seconds:.3f}",
        f"date: {date_str}",
        f"ale_layer: {ale_layer}",
        f"ale_tier: {ale_tier}",
        "surreal_table: evo_journey",
        "---",
        "",
        f"# EVO Voyage — {skill_id}",
        "",
        f"**φ score:** {voyage.phi_score:.4f}  {'✓ above gate' if not voyage.is_degenerate else '⚠ degenerate (< 0.3)'}",
        f"**Modalities:** {', '.join(voyage.modalities_used) or 'none'}",
        f"**Refined:** {'Yes — PRIME skill updated' if refined else 'No'}",
        f"**Duration:** {voyage.duration_seconds:.3f}s",
        "",
        "## Trace Steps",
        "",
    ]
    for i, s in enumerate(steps_summary):
        step_line = (
            f"- Step {i}: coherence {s['coherence_before']:.3f}→{s['coherence_after']:.3f} "
            f"φ={s['phi']:.3f} Δ={s['latent_delta']:.5f} ({s['latency_ms']:.1f}ms)"
        )
        if s.get("synthesis"):
            step_line += f"\n  > _{s['synthesis']}_"
        lines.append(step_line)

    lines += [
        "",
        "## Latent Snapshot (first 8 dims)",
        "",
        f"`{[round(x, 4) for x in voyage.latent_snapshot[:8]]}`",
        "",
    ]
    if research_full:
        lines += [research_full, ""]
    lines += [
        "## Links",
        "",
        f"- [[HIHO_STABILITY_PRIME]] — φ = 4·c·(1-c) kernel",
        f"- [[COMPOUND_SELF_IMPROVEMENT_PRIME]] — recursive loop",
        f"- [[JOURNEY_TRACKING_PRIME]] — 12D trajectory",
        "",
    ]

    fpath.write_text("\n".join(lines))
    logger.info("vault → %s", fpath)


# ── Research grounding — arXiv / HuggingFace / Semantic Scholar ──────────────
#
# Each EVO step description is prefixed with a compact SOTA summary (≤240 chars)
# so TextModality's prompt[:500] window sees current research before the skill desc.
# Full abstracts go to the Obsidian vault note only.
_ARXIV_API = "https://export.arxiv.org/api/query"
_HF_PAPERS_API = "https://huggingface.co/api/papers"
_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_RESEARCH_CACHE: dict[str, tuple[str, str]] = {}
_RESEARCH_TIMEOUT = 8  # seconds per source — fail-soft if slow
_ARXIV_NS = "http://www.w3.org/2005/Atom"

_SKILL_RESEARCH_QUERIES: dict[str, dict[str, str]] = {
    "COMPOUND_SELF_IMPROVEMENT_PRIME": {
        "arxiv": "recursive self-improvement language model agent autonomous",
        "hf": "self-improving LLM autonomous recursive agent",
        "s2": "recursive self-improvement language model agent",
    },
    "FLUME_METHODOLOGY_PRIME": {
        "arxiv": "variational autoencoder latent manifold disentangled representation 2026",
        "hf": "VAE latent space disentanglement representation learning",
        "s2": "variational autoencoder latent disentangled representation",
    },
    "JOURNEY_TRACKING_PRIME": {
        "arxiv": "agent trajectory temporal knowledge graph state tracking memory",
        "hf": "agent state memory temporal graph tracking",
        "s2": "agent trajectory state tracking temporal memory",
    },
    "GROUP_EVOLVING_AGENTS_PRIME": {
        "arxiv": "multi-agent coordination experience sharing tool calling cross-agent",
        "hf": "multi-agent tool use collaborative experience sharing",
        "s2": "multi-agent coordination tool calling collaboration",
    },
    "HIHO_STABILITY_PRIME": {
        "arxiv": "speculative decoding hardware efficient inference AMD NPU accelerator",
        "hf": "speculative decoding hardware accelerated efficient inference",
        "s2": "speculative decoding efficient inference hardware acceleration",
    },
    "AUTONOMIC_EVOLUTION_PRIME": {
        "arxiv": "generalist computer use agent multimodal autonomous benchmark",
        "hf": "computer use agent autonomous multimodal evaluation benchmark",
        "s2": "computer use generalist agent multimodal autonomous",
    },
    # ── AMD Strix Halo compound engineering ───────────────────────────────────
    "NPU_TIER_OPTIMIZATION_PRIME": {
        "arxiv": "XDNA2 NPU inference scheduling LLM heterogeneous compute AMD 2025",
        "hf": "NPU neural processing unit LLM inference heterogeneous hardware routing 2025",
        "s2": "NPU inference optimization scheduling heterogeneous CPU GPU 2025",
    },
    "IGPU_ROCWMMA_COMPOUND_PRIME": {
        "arxiv": "speculative decoding heterogeneous draft verifier hardware acceleration ROCm 2025",
        "hf": "speculative decoding GPU ROCM hardware-aware draft model acceptance 2025",
        "s2": "speculative decoding acceptance rate hardware-aware mixed precision 2025",
    },
    "UNIFIED_MEMORY_TOPOLOGY_PRIME": {
        "arxiv": "unified memory LLM KV cache paging heterogeneous APU CPU GPU 2025",
        "hf": "unified memory large model KV cache paging scheduling APU 2025",
        "s2": "unified memory LLM inference KV cache heterogeneous memory architecture 2025",
    },
    "TRIUNE_ROUTER_COMPOUND_PRIME": {
        "arxiv": "cascaded LLM routing quality escalation small large model compound AI 2025",
        "hf": "tiered LLM routing quality gate cost compound AI system 2025",
        "s2": "compound AI tiered routing quality cost local cloud escalation 2025",
    },
    "COMPOUND_LOOP_LATENCY_PRIME": {
        "arxiv": "self-improving LLM skill refinement evolutionary compound loop latency 2025",
        "hf": "compound AI self-improving loop skill synthesis latency optimization 2025",
        "s2": "compound AI system latency self-improvement skill refinement pipeline 2025",
    },
}


def _fetch_arxiv_papers(query: str, max_results: int = 2) -> list[dict]:
    """Fetch recent arXiv papers sorted by last-updated; fail-soft (returns [] on any error)."""
    try:
        params = urllib.parse.urlencode(
            {
                "search_query": f"all:{query}",
                "max_results": max_results,
                "sortBy": "lastUpdatedDate",
                "sortOrder": "descending",
            }
        )
        url = f"{_ARXIV_API}?{params}"
        with urllib.request.urlopen(url, timeout=_RESEARCH_TIMEOUT) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        papers = []
        for entry in root.findall(f"{{{_ARXIV_NS}}}entry"):
            id_url = (entry.findtext(f"{{{_ARXIV_NS}}}id") or "").strip()
            # "http://arxiv.org/abs/2606.05405v1" → "2606.05405"
            id_parts = id_url.split("/abs/")
            raw_id = id_parts[-1] if len(id_parts) > 1 else id_url
            arxiv_id = raw_id.split("v")[0] if "v" in raw_id else raw_id
            title = (entry.findtext(f"{{{_ARXIV_NS}}}title") or "").strip().replace("\n", " ")
            abstract = (
                (entry.findtext(f"{{{_ARXIV_NS}}}summary") or "").strip().replace("\n", " ")[:400]
            )
            updated = (entry.findtext(f"{{{_ARXIV_NS}}}updated") or "")[:10]
            papers.append(
                {
                    "id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "updated": updated,
                    "source": "arxiv",
                }
            )
        return papers
    except Exception as exc:
        logger.debug("arXiv fetch failed (non-blocking): %s", exc)
        return []


def _fetch_hf_papers(query: str, max_results: int = 2) -> list[dict]:
    """Fetch trending HuggingFace papers by query; fail-soft."""
    try:
        params = urllib.parse.urlencode({"q": query, "limit": max_results})
        url = f"{_HF_PAPERS_API}?{params}"
        with urllib.request.urlopen(url, timeout=_RESEARCH_TIMEOUT) as resp:
            data = json.load(resp)
        papers = []
        for p in (data if isinstance(data, list) else [])[:max_results]:
            papers.append(
                {
                    "id": p.get("id", ""),
                    "title": (p.get("title") or "").strip(),
                    "abstract": (p.get("summary") or "")[:400],
                    "upvotes": p.get("upvotes", 0),
                    "source": "hf",
                }
            )
        return papers
    except Exception as exc:
        logger.debug("HF Papers fetch failed (non-blocking): %s", exc)
        return []


def _fetch_semantic_scholar(query: str, max_results: int = 2) -> list[dict]:
    """Fetch Semantic Scholar papers ranked by relevance; fail-soft."""
    try:
        params = urllib.parse.urlencode(
            {
                "query": query,
                "fields": "title,abstract,year,citationCount",
                "limit": max_results,
            }
        )
        url = f"{_S2_API}?{params}"
        with urllib.request.urlopen(url, timeout=_RESEARCH_TIMEOUT) as resp:
            data = json.load(resp)
        papers = []
        for p in data.get("data", []):
            papers.append(
                {
                    "id": p.get("paperId", ""),
                    "title": (p.get("title") or "").strip(),
                    "abstract": (p.get("abstract") or "")[:400],
                    "year": p.get("year", ""),
                    "citations": p.get("citationCount", 0),
                    "source": "s2",
                }
            )
        return papers
    except Exception as exc:
        logger.debug("Semantic Scholar fetch failed (non-blocking): %s", exc)
        return []


def _fetch_research_context(skill_id: str, ale_layer: str) -> tuple[str, str]:
    """Fetch SOTA papers for a skill; return (compact ≤240 chars, full with abstracts).

    Results are cached per run (keyed by skill_id) — each skill is only fetched once
    regardless of how many rounds are run. Compact form is prepended to step descriptions;
    full form goes to the Obsidian vault note.
    """
    cache_key = f"{skill_id}:{ale_layer}"
    if cache_key in _RESEARCH_CACHE:
        return _RESEARCH_CACHE[cache_key]

    queries = _SKILL_RESEARCH_QUERIES.get(
        skill_id,
        {
            "arxiv": f"{ale_layer} agent AI reasoning 2026",
            "hf": f"{ale_layer.lower()} agent AI",
            "s2": f"{ale_layer} agent AI reasoning",
        },
    )

    arxiv_papers = _fetch_arxiv_papers(queries.get("arxiv", ""))
    hf_papers = _fetch_hf_papers(queries.get("hf", ""))
    s2_papers = _fetch_semantic_scholar(queries.get("s2", ""))

    # Compact form: up to 3 paper titles, total ≤240 chars
    compact_parts: list[str] = []
    seen_titles: set[str] = set()
    for p in (arxiv_papers + hf_papers + s2_papers)[:5]:
        title = (p.get("title") or "")[:45]
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        if p.get("source") == "arxiv" and p.get("id"):
            tag = f"arXiv:{p['id']}"
        elif p.get("source") == "hf":
            tag = "HF"
        else:
            tag = f"S2/{p.get('year', '')}"
        compact_parts.append(f'"{title}"({tag})')
        if sum(len(x) + 1 for x in compact_parts) > 220:
            compact_parts.pop()
            break

    compact = f"SOTA:{';'.join(compact_parts)}" if compact_parts else ""
    if len(compact) > 240:
        compact = compact[:237] + "…"

    # Full form: titles + abstracts for vault
    full_lines: list[str] = [f"## Research Context — {skill_id}", ""]
    for p in arxiv_papers:
        full_lines += [
            f"**[arXiv:{p.get('id', '')}]** {p.get('title', '')} ({p.get('updated', '')})",
            f"> {p.get('abstract', '')[:300]}",
            "",
        ]
    for p in hf_papers:
        full_lines += [
            f"**[HF:{p.get('id', '')}]** {p.get('title', '')} (↑{p.get('upvotes', 0)})",
            f"> {p.get('abstract', '')[:300]}",
            "",
        ]
    for p in s2_papers:
        full_lines += [
            f"**[S2]** {p.get('title', '')} ({p.get('year', '')} | {p.get('citations', 0)} citations)",
            f"> {p.get('abstract', '')[:300]}",
            "",
        ]
    full = "\n".join(full_lines)

    result = (compact, full)
    _RESEARCH_CACHE[cache_key] = result
    if compact:
        logger.info("  research: %d paper(s) for %s", len(seen_titles), skill_id)
    else:
        logger.debug("  no research context available (all sources offline or rate-limited)")
    return result


# ── Skills to traverse — GCUA 5-layer taxonomy (ALE arxiv:2606.05405) ─────────
#
# ALE gate-and-score maps to: phi ≥ 0.3 gate (binary) → phi_distribution (continuous).
# Tier step counts match ALE difficulty: Near-Term=3, Full-Spectrum=5, Last-Exam=8.
SKILL_JOURNEYS = [
    # ── Brain: LLM reasoning/planning ── Near-Term ──────────────────────────────
    {
        "skill_id": "COMPOUND_SELF_IMPROVEMENT_PRIME",
        "description": (
            "Reason about the recursive compound improvement cycle: how does each EVO voyage "
            "update the PRIME skill's latent embedding? Derive the convergence criterion "
            "that distinguishes a healthy phi trajectory from a degenerate plateau."
        ),
        "modalities": ["text"],
        "steps": 3,
        "ale_layer": "Brain",
        "ale_tier": "Near-Term",
    },
    # ── Eyes: visual/latent-space perception ── Full-Spectrum ───────────────────
    {
        "skill_id": "FLUME_METHODOLOGY_PRIME",
        "description": (
            "Encode a 256D latent vector at the FLUME VAE's current attractor basin. "
            "Identify which dimensions carry coherence signal vs. noise. "
            "Generate a 2D projection image of the latent trajectory across this voyage."
        ),
        "modalities": ["text", "image"],
        "steps": 5,
        "ale_layer": "Eyes",
        "ale_tier": "Full-Spectrum",
    },
    # ── Body: orchestration/control flow ── Full-Spectrum ───────────────────────
    {
        "skill_id": "JOURNEY_TRACKING_PRIME",
        "description": (
            "Orchestrate the 12D compound trajectory dual-write pipeline across SurrealDB "
            "and Obsidian vault. Determine optimal batch size for concurrent writes and "
            "synthesize the bi-temporal validity range strategy for partial failure recovery."
        ),
        "modalities": ["text", "image"],
        "steps": 5,
        "ale_layer": "Body",
        "ale_tier": "Full-Spectrum",
    },
    # ── Hands: structured tool invocation ── Full-Spectrum ──────────────────────
    {
        "skill_id": "GROUP_EVOLVING_AGENTS_PRIME",
        "description": (
            "Design the GEA cross-agent experience-sharing protocol: agent A's EVO voyage "
            "phi distribution informs agent B's hiho_delta_scale. Specify the MCP tool "
            "invocation sequence that carries latent snapshots between local inference agents."
        ),
        "modalities": ["text", "audio"],
        "steps": 5,
        "ale_layer": "Hands",
        "ale_tier": "Full-Spectrum",
    },
    # ── Feet: runtime substrate / physics ── Last-Exam ──────────────────────────
    {
        "skill_id": "HIHO_STABILITY_PRIME",
        "description": (
            "Characterize the HIHO attractor at full depth: derive the bifurcation diagram "
            "for logistic map r=4 (Feigenbaum onset FD~1.5), map how the 256D latent trajectory "
            "approaches the fixed point at coherence=0.5, and quantify the basin-of-attraction "
            "boundary across AMD Strix Halo 128GB unified memory geometry."
        ),
        "modalities": ["text"],
        "steps": 8,
        "ale_layer": "Feet",
        "ale_tier": "Last-Exam",
    },
    # ── Full-GCUA: all 5 layers integrated ── Last-Exam ─────────────────────────
    {
        "skill_id": "AUTONOMIC_EVOLUTION_PRIME",
        "description": (
            "Execute a full GCUA lifecycle: plan the self-modification strategy (Brain), "
            "observe latent space shift after each step via image synthesis (Eyes), "
            "orchestrate the Constitution gate decision (Body), invoke SkillRefiner with "
            "gate_probability weighting (Hands), verify updated skill persists in PRIME "
            "registry (Feet). Synthesize cross-layer insights for the recursive loop."
        ),
        "modalities": ["text", "audio", "video"],
        "steps": 8,
        "ale_layer": "Full-GCUA",
        "ale_tier": "Last-Exam",
    },
    # ── AMD Strix Halo compound engineering journeys ────────────────────────────
    # focus="compound_amd" — selectable via --focus compound_amd
    {
        "skill_id": "NPU_TIER_OPTIMIZATION_PRIME",
        "description": (
            "Optimize the XDNA2 NPU tier (llama3.2-1b-FLM, 42 TPS baseline) for compound "
            "loop routing: derive the classifier overhead budget (1–106µs measured range) "
            "that preserves 42 TPS throughput, specify task_classifier gate conditions under "
            "which NPU escalates to iGPU, and quantify the per-token cost delta that justifies "
            "local escalation vs cloud fallback on Strix Halo 128GB unified memory."
        ),
        "modalities": ["text"],
        "steps": 5,
        "ale_layer": "Feet",
        "ale_tier": "Full-Spectrum",
        "focus": "compound_amd",
    },
    {
        "skill_id": "IGPU_ROCWMMA_COMPOUND_PRIME",
        "description": (
            "Design the iGPU RDNA 3.5 compound inference pipeline: specify ROCwMMA tile sizes "
            "optimal for Gemma-4-E4B-it-GGUF batch inference, derive the ctx_size bound "
            "(≤16384) that avoids KV cache OOM when NPU is co-resident in unified memory, "
            "and synthesize the CLaSp speculative decoding acceptance-rate curve for the "
            "E4B draft / E2B verify pair on the AMD iGPU lane at :13307."
        ),
        "modalities": ["text", "image"],
        "steps": 5,
        "ale_layer": "Feet",
        "ale_tier": "Full-Spectrum",
        "focus": "compound_amd",
    },
    {
        "skill_id": "UNIFIED_MEMORY_TOPOLOGY_PRIME",
        "description": (
            "Map the 128GB Strix Halo unified memory topology for concurrent compound AI: "
            "derive allocation bounds for simultaneous NPU (llama3.2-1b @ ctx=16384, ~2GB), "
            "iGPU (Gemma-4-E4B @ ctx=16384, ~5GB), and CPU (Qwen3.6-35B @ ctx=16384, ~22GB) "
            "tiers without triggering GTT aperture OOM (N3 invariant). Specify MemorySnapshot "
            "gate thresholds for Omni-Dense (36GB) and Omni-Lite (12GB) tier selection. "
            "Derive the free-memory floor that guarantees safe concurrent three-tier load."
        ),
        "modalities": ["text"],
        "steps": 8,
        "ale_layer": "Feet",
        "ale_tier": "Last-Exam",
        "focus": "compound_amd",
    },
    {
        "skill_id": "TRIUNE_ROUTER_COMPOUND_PRIME",
        "description": (
            "Synthesize the router-centric :13305 compound topology: derive the LRU eviction "
            "policy that allows NPU + iGPU + CPU tiers to coexist without auto-load at "
            "ctx_size=0. Specify the exact POST :13305/api/v1/load sequence (ctx_size=16384, "
            "save_options=true) that hardens the three-tier compound loop against the N3 OOM "
            "crasher. Quantify TTFT improvement: warm-cache (393ms) vs cold-load (583ms) vs "
            "router on-demand paths across all three tier models."
        ),
        "modalities": ["text", "audio"],
        "steps": 5,
        "ale_layer": "Brain",
        "ale_tier": "Full-Spectrum",
        "focus": "compound_amd",
    },
    {
        "skill_id": "COMPOUND_LOOP_LATENCY_PRIME",
        "description": (
            "Characterize the full compound loop latency budget on Strix Halo: break down "
            "the per-step cost — task_classifier (1–106µs), semantic cache lookup (6ms via "
            "nomic-embed-text-v2-moe), NPU inference (24ms / 42 TPS), iGPU inference (~200ms), "
            "SurrealDB write (vault dual-write ~5ms). Derive the optimal batch size for "
            "asyncio.gather() that achieves the 3.44x throughput lift (exp_OOOO) without "
            "saturating unified memory bandwidth. Specify the DegradationDetector threshold "
            "configuration that triggers iGPU escalation before latency SLA breach."
        ),
        "modalities": ["text", "image"],
        "steps": 8,
        "ale_layer": "Full-GCUA",
        "ale_tier": "Last-Exam",
        "focus": "compound_amd",
    },
]


# ── Main loop ─────────────────────────────────────────────────────────────────


def run_evo_loop(
    rounds: int = 1,
    steps_override: int | None = None,
    use_research: bool = True,
    tick_expansion: int = 0,
    focus: str | None = None,
) -> list[dict]:
    """Run the EVO recursive improvement loop for the given number of rounds.

    tick_expansion: additional steps added per round (0 = no expansion).
                    Round N runs base_steps + N * tick_expansion.
    focus:          if set, only run journeys whose "focus" field matches this value.
                    Use "compound_amd" to run only AMD Strix Halo engineering skills.
    """
    from cohezion.compound.journey_tracker import JourneyTracker
    from cohezion.compound.skill_refiner import SkillRefiner
    from cohezion.evo.recursive_tracer import RecursiveTracer
    from cohezion.universe.agentic_evo_swift import AgenticEVO

    _ensure_evo_journey_table()

    all_results = []
    total_voyages = 0
    total_refined = 0

    active_journeys = SKILL_JOURNEYS
    if focus:
        active_journeys = [j for j in SKILL_JOURNEYS if j.get("focus") == focus]
        if not active_journeys:
            logger.warning("No journeys match focus=%r — running all", focus)
            active_journeys = SKILL_JOURNEYS
        logger.info("focus=%s → %d journey(s) selected", focus, len(active_journeys))

    for round_num in range(rounds):
        tick_extra = round_num * tick_expansion
        logger.info(
            "═══ Round %d/%d (tick_expansion=+%d steps) ═══", round_num + 1, rounds, tick_extra
        )

        for journey_spec in active_journeys:
            skill_id = journey_spec["skill_id"]
            description = journey_spec["description"]
            modalities = journey_spec["modalities"]
            n_steps = (steps_override or journey_spec["steps"]) + tick_extra
            ale_layer = journey_spec.get("ale_layer", "—")
            ale_tier = journey_spec.get("ale_tier", "—")
            # Per-skill delta scale: AMD compound skills use larger perturbations to
            # reliably escape the HIHO unstable fixed point at coherence=0.0817
            hiho_delta_scale = journey_spec.get("hiho_delta_scale", 0.02)

            logger.info(
                "▶ [%s/%s] %s (%d steps, mods=%s)",
                ale_layer,
                ale_tier,
                skill_id,
                n_steps,
                modalities,
            )

            # Research grounding: fetch SOTA once per skill per run (cached)
            research_compact, research_full = ("", "")
            if use_research:
                research_compact, research_full = _fetch_research_context(skill_id, ale_layer)

            # Vault cerebellum context: last insight written for this skill (write-loop closure).
            cerebellum_ctx = _load_cerebellum_context(skill_id)

            # Fresh agent per skill — σ scales with run depth so c_final stays above gate.
            # Gate: φ = 4c(1-c) ≥ 0.3 requires c ∈ [0.0818, 0.9182]. Decay ≈ 0.924/step.
            # σ_needed = 0.0850 / (√(2/π) × 0.924^n_steps); floor at 0.25, cap at 1.25.
            # Cap at 1.25 keeps c₀ = σ × 0.7979 < 1.0 so φ₀ > 0 (valid range) for n ≤ 28.
            agent_id = f"evo-loop-r{round_num:02d}-{skill_id[:12].lower()}"
            _sigma_base = min(1.25, max(0.25, 0.0850 / (0.7979 * pow(0.924, n_steps))))
            # Adapt σ from SurrealDB φ trend (last 10 voyages for this skill).
            # Healthy φ > 0.6 → tighten (0.85×); gate zone φ < 0.35 → widen (1.20×).
            phi_trend = _query_phi_trend(skill_id)
            if phi_trend is not None:
                if phi_trend > 0.6:
                    _sigma_factor = 0.85
                elif phi_trend >= 0.45:
                    _sigma_factor = 1.0
                elif phi_trend >= 0.3:
                    _sigma_factor = 1.15
                else:
                    _sigma_factor = 1.25
                _sigma = min(1.25, max(0.25, _sigma_base * _sigma_factor))
                logger.debug(
                    "φ-trend=%.3f → σ_factor=%.2f (base %.3f → %.3f)",
                    phi_trend,
                    _sigma_factor,
                    _sigma_base,
                    _sigma,
                )
            else:
                _sigma = _sigma_base
            initial_latent = np.random.default_rng().standard_normal(256) * _sigma + 0.5
            logger.debug("agent σ=%.3f for %d steps (E[c]≈%.3f)", _sigma, n_steps, _sigma * 0.7979)
            agent = AgenticEVO(agent_id=agent_id, initial_latent=initial_latent)

            # JourneyTracker without MCP client — vault write handled by _vault_write_voyage()
            tracker = JourneyTracker()
            refiner = SkillRefiner()
            tracer = RecursiveTracer(agent, tracker, skill_refiner=refiner)

            journey_id = f"evo-loop-{round_num}-{skill_id}-{int(time.time())}"

            # Run trace steps
            steps_summary = []
            for step_i in range(n_steps):
                # Build context prefix (fits in TextModality prompt[:500] window):
                # SOTA compact (≤240 chars) + cerebellum insight (≤86 chars) + core desc.
                ctx_parts: list[str] = []
                if research_compact:
                    ctx_parts.append(research_compact)
                if cerebellum_ctx:
                    ctx_parts.append(cerebellum_ctx)
                core = f"[R{round_num}] {description} — step {step_i + 1}/{n_steps}"
                step_desc = f"{' '.join(ctx_parts)} {core}".strip() if ctx_parts else core
                try:
                    result = tracer.trace_step(
                        task_description=step_desc,
                        modalities=modalities,
                        operation_type="transform",
                        hiho_delta_scale=hiho_delta_scale,
                        hiho_damping=0.05,
                    )
                    steps_summary.append(
                        {
                            "coherence_before": result.coherence_before,
                            "coherence_after": result.coherence_after,
                            "phi": result.phi,
                            "latent_delta": result.latent_delta,
                            "latency_ms": result.latency_ms,
                            "synthesis": result.synthesis_text,
                        }
                    )
                    logger.info(
                        "  step %d/%d: c=%.3f→%.3f φ=%.3f Δ=%.5f (%.0fms)",
                        step_i + 1,
                        n_steps,
                        result.coherence_before,
                        result.coherence_after,
                        result.phi,
                        result.latent_delta,
                        result.latency_ms,
                    )
                except RuntimeError as e:
                    if "OOM guard" in str(e):
                        logger.error("OOM guard fired for %s — skipping remaining steps", skill_id)
                        break
                    raise

            if tracer.step_count == 0:
                logger.warning("No steps completed for %s, skipping complete_journey()", skill_id)
                continue

            # Close voyage — dual-write SurrealDB + SkillRefiner
            voyage = tracer.complete_journey(
                journey_id=journey_id,
                skill_id=skill_id,
                operation_type="transform",
            )

            refined = len(voyage.skill_refinements) > 0
            total_voyages += 1
            if refined:
                total_refined += 1

            logger.info(
                "  ✓ voyage done: φ=%.3f %s refined=%s modalities=%s",
                voyage.phi_score,
                "✓ healthy" if not voyage.is_degenerate else "⚠ degenerate",
                refined,
                voyage.modalities_used,
            )

            # Store in SurrealDB
            try:
                _store_voyage(voyage, skill_id, refined, len(steps_summary))
                logger.info(
                    "  → SurrealDB: evo_journey recorded (voyage_id=%s)", voyage.voyage_id[:8]
                )
            except Exception as e:
                logger.warning("  SurrealDB write failed (non-blocking): %s", e)

            # Store in Obsidian vault
            try:
                _vault_write_voyage(
                    voyage,
                    skill_id,
                    refined,
                    steps_summary,
                    ale_layer=ale_layer,
                    ale_tier=ale_tier,
                    research_full=research_full,
                )
            except Exception as e:
                logger.warning("  Vault write failed (non-blocking): %s", e)

            all_results.append(
                {
                    "round": round_num,
                    "skill_id": skill_id,
                    "voyage_id": voyage.voyage_id,
                    "phi_score": voyage.phi_score,
                    "is_degenerate": voyage.is_degenerate,
                    "refined": refined,
                    "modalities": voyage.modalities_used,
                    "steps": len(steps_summary),
                    "duration_s": voyage.duration_seconds,
                    "ale_layer": ale_layer,
                    "ale_tier": ale_tier,
                }
            )

    # Summary
    logger.info("")
    logger.info("═══ Loop Complete ═══")
    logger.info(
        "Total voyages: %d | Refined: %d | Degenerate: %d",
        total_voyages,
        total_refined,
        sum(1 for r in all_results if r["is_degenerate"]),
    )

    phis = [r["phi_score"] for r in all_results]
    if phis:
        logger.info(
            "φ scores: min=%.3f max=%.3f mean=%.3f", min(phis), max(phis), sum(phis) / len(phis)
        )

    return all_results


def main() -> None:
    parser = argparse.ArgumentParser(description="EVO recursive improvement loop")
    parser.add_argument("--rounds", type=int, default=1, help="Number of loop rounds")
    parser.add_argument("--steps", type=int, default=None, help="Override step count per skill")
    parser.add_argument(
        "--no-research",
        action="store_true",
        help="Disable SOTA research grounding (faster, offline-safe)",
    )
    parser.add_argument(
        "--tick-expansion",
        type=int,
        default=2,
        metavar="N",
        help="Additional steps added per round (default: 2)",
    )
    parser.add_argument(
        "--focus",
        type=str,
        default="compound_amd",
        help="Filter to journeys with this focus tag (default: compound_amd)",
    )
    args = parser.parse_args()

    results = run_evo_loop(
        rounds=args.rounds,
        steps_override=args.steps,
        use_research=not args.no_research,
        tick_expansion=args.tick_expansion,
        focus=args.focus,
    )

    print("\n── Results ──")
    for r in results:
        gate = "✓" if not r["is_degenerate"] else "⚠"
        ref = "↑" if r["refined"] else " "
        layer = r.get("ale_layer", "—")
        tier = r.get("ale_tier", "—")
        print(
            f"  {gate}{ref} [{layer:<8}/{tier:<13}] {r['skill_id'][:35]:<35} "
            f"φ={r['phi_score']:.3f} mods={','.join(r['modalities'])} steps={r['steps']}"
        )


if __name__ == "__main__":
    main()
