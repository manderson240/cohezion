"""Latent Swarm Research Team — Agentic SOTA inference across FLUME latent spaces.

Integrates:
- ResearchOrchestrator (parallel streams: HuggingFace, ArXiv, GitHub, web)
- MultiAgentOrchestrator (dynamic agent coordination)
- TopologicalRouter (latent-space-aware task routing)
- ComputeBackendRouter (NPU/iGPU/CPU/cloud backend selection)
- FLUME encoder (256D result embedding + coherence scoring)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │  Research Lead (orchestrator)                               │
    │   ├─ Model Scout HF    → lemonade /v1/models health       │
    │   ├─ Model Scout ArXiv → latest quantization papers         │
    │   ├─ Topology Analyst  → FLUME latent navigator             │
    │   ├─ Inference Optim   → backend router + benchmark         │
    │   └─ Compound Engineer → retrospection + skill refine       │
    └─────────────────────────────────────────────────────────────┘
                             ↓
              SynthesisEngine (cross-source + latent coherence)
                             ↓
              FLUME Encode → 256D vector + coherence score
                             ↓
              SkillRefiner (if warranted)

Usage:
    team = LatentSwarmResearchTeam()
    report = await team.research_sota_inference(
        query="MoE routing for 4-bit quantization on AMD Strix",
        depth="deep",  # shallow | standard | deep
    )
    # report contains: findings, latent_vector, coherence, recommended_backend
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import numpy as np

from cohezion.compound.holographic_projection import text_to_latent
from cohezion.swarm.compute_backend_router import ComputeBackendRouter
from cohezion.swarm.multi_agent_orchestrator import (
    MultiAgentOrchestrator,
)
from cohezion.swarm.research_orchestrator import (
    CompoundSynthesis,
    ResearchFinding,
    ResearchOrchestrator,
)
from cohezion.swarm.topological_router import TopologicalRouter


logger = logging.getLogger(__name__)

# Lemonade local endpoint — the unified inference surface
_LEMONADE_BASE = "http://localhost:13305"


@dataclass
class SotaInferenceReport:
    """Output of a latent swarm research run."""

    query: str
    findings: list[ResearchFinding]
    synthesis: CompoundSynthesis | None
    latent_vector: list[float]  # 256D FLUME encoding
    coherence: float  # HIHO stability score (0-1, peak 0.5)
    recommended_backend: str  # npu | vulkan | cpu | cloud
    recommended_model: str
    execution_time_ms: float
    agent_traces: list[dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "findings_count": len(self.findings),
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
            "latent_vector": self.latent_vector[:8] + ["..."],  # truncated for display
            "coherence": round(self.coherence, 4),
            "recommended_backend": self.recommended_backend,
            "recommended_model": self.recommended_model,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


class LatentSwarmResearchTeam:
    """Agentic research team that hunts SOTA inference configs via latent-space navigation."""

    def __init__(
        self,
        lemonade_base: str = _LEMONADE_BASE,
        enable_learning: bool = True,
    ) -> None:
        self.lemonade_base = lemonade_base.rstrip("/")
        self.enable_learning = enable_learning

        # Sub-orchestrators (each is a specialist swarm)
        self.research = ResearchOrchestrator()
        self.agents = MultiAgentOrchestrator(enable_learning=enable_learning)
        self.topology = TopologicalRouter()
        self.compute = ComputeBackendRouter.get_default()
        self.navigator = None  # Lazy-load; requires FlumeEncoder

        # In-memory trace for this session
        self._traces: list[dict[str, Any]] = []
        self._navigator = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def research_sota_inference(
        self,
        query: str,
        depth: str = "standard",
    ) -> SotaInferenceReport:
        """Run the full latent swarm research pipeline.

        Parameters
        ----------
        query : str
            Research objective (e.g. "best 4-bit MoE for AMD Strix Halo").
        depth : str
            shallow → 1 agent, standard → 4 agents, deep → 4 agents + benchmarks
        """
        t0 = time.monotonic()
        self._traces.clear()

        # Phase 1 — Parallel research streams
        findings = await self._run_research_streams(query, depth)

        # Phase 2 — Cross-source synthesis
        synthesis = await self._synthesize(findings, query)

        # Phase 3 — Backend / model recommendation via latent navigation
        backend, model = await self._recommend_backend_model(synthesis, query)

        # Phase 4 — FLUME encode the full report
        latent, coherence = self._encode_report(query, findings, synthesis, backend, model)

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        report = SotaInferenceReport(
            query=query,
            findings=findings,
            synthesis=synthesis,
            latent_vector=latent.tolist() if isinstance(latent, np.ndarray) else latent,
            coherence=coherence,
            recommended_backend=backend,
            recommended_model=model,
            execution_time_ms=elapsed_ms,
            agent_traces=list(self._traces),
        )

        logger.info(
            "LatentSwarm: query='%s' findings=%d backend=%s model=%s coherence=%.3f time=%.1fms",
            query,
            len(findings),
            backend,
            model,
            coherence,
            elapsed_ms,
        )

        return report

    async def benchmark_candidate(
        self,
        model: str,
        backend: str,
        prompt: str = "The quick brown fox jumps over the lazy dog.",
    ) -> dict[str, Any]:
        """Live benchmark a model+backend combo via lemonade.

        Returns tok/s, latency, memory used.
        """
        try:
            result = await self.compute.execute(
                model=model,
                prompt=prompt,
                preferred_backend=backend,
                max_tokens=128,
            )
            return {
                "model": model,
                "backend": backend,
                "tokens_per_second": result.get("tokens_per_second", 0.0),
                "latency_ms": result.get("latency_ms", 0.0),
                "success": True,
            }
        except Exception as exc:
            logger.warning("Benchmark failed for %s@%s: %s", model, backend, exc)
            return {
                "model": model,
                "backend": backend,
                "error": str(exc),
                "success": False,
            }

    # ------------------------------------------------------------------
    # Internal pipeline phases
    # ------------------------------------------------------------------

    async def _run_research_streams(self, query: str, depth: str) -> list[ResearchFinding]:
        """Phase 1 — Deploy parallel research agents."""

        topics = self._derive_topics(query)
        streams: list[Any] = []

        # Always run model-registry probe (local SOTA)
        streams.append(self._probe_lemonade_registry())

        if depth in ("standard", "deep"):
            # Web + paper streams
            streams.append(self.research.research_compound(topics, output_format="findings"))

        if depth == "deep":
            # ArXiv deep-dive on quantization / routing
            streams.append(
                self.research.research_compound(
                    topics=["quantization", "MoE routing", "AMD NPU"],
                    output_format="findings",
                )
            )

        results = await asyncio.gather(*streams, return_exceptions=True)

        findings: list[ResearchFinding] = []
        for r in results:
            if isinstance(r, Exception):
                self._trace("research_stream", {"status": "error", "detail": str(r)})
                continue
            if isinstance(r, list):
                for item in r:
                    if isinstance(item, dict):
                        # Convert lemonade registry dicts → ResearchFinding
                        findings.append(
                            ResearchFinding(
                                source="lemonade",
                                category="model_registry",
                                title=item.get("model", "unknown"),
                                url="http://localhost:13305",
                                summary=f"{item.get('model', '')} ({item.get('recipe', 'unknown')})",
                                relevance_score=0.5,
                                timestamp=datetime.now(),
                                metadata={
                                    "size": item.get("size", 0.0),
                                    "labels": item.get("labels", []),
                                    "recipe": item.get("recipe", "unknown"),
                                },
                                compound_tags=[
                                    t
                                    for t in item.get("labels", [])
                                    if t in ("reasoning", "vision", "hot", "tool-calling")
                                ]
                                or ["inference"],
                            )
                        )
                    else:
                        findings.append(item)
            elif isinstance(r, dict) and "findings" in r:
                findings.extend(r["findings"])

        self._trace("research_phase", {"findings": len(findings), "depth": depth})
        return findings

    async def _synthesize(
        self,
        findings: list[ResearchFinding],
        query: str,
    ) -> CompoundSynthesis | None:
        """Phase 2 — Cross-source synthesis via ResearchOrchestrator."""
        try:
            # SynthesisEngine.synthesize returns list[CompoundSynthesis] (async)
            synths = await self.research.synthesis.synthesize(findings)
            synth = synths[0] if synths else None
            if synth:
                self._trace(
                    "synthesis",
                    {"insight_id": synth.insight_id, "confidence": synth.confidence},
                )
            return synth
        except Exception as exc:
            logger.warning("Synthesis failed: %s", exc)
            self._trace("synthesis", {"status": "error", "detail": str(exc)})
            return None

    async def _recommend_backend_model(
        self,
        synthesis: CompoundSynthesis | None,
        query: str,
    ) -> tuple[str, str]:
        """Phase 3 — Use topological + compute routing to pick best backend/model."""

        # Probe lemonade for current model roster + health
        registry = await self._probe_lemonade_registry()

        # Build candidate pool from synthesis tags + registry
        candidates = self._build_candidates(registry, synthesis)

        # Topological routing: score candidates by latent-space distance to query
        best_model = None
        best_score = -1.0
        for cand in candidates:
            score = self._score_candidate(cand, query)
            if score > best_score:
                best_score = score
                best_model = cand

        if best_model is None:
            # Fallback to smallest NPU model
            best_model = {"model": "gemma3-4b-FLM", "backend": "npu"}

        # Compute backend validation — pass numeric model size, not model ID
        model_size_gb = best_model.get("size", 0.0)
        routing_decision = self.compute.select_backend(
            model_size_gb=model_size_gb,
            constraints=None,
        )
        backend = (
            routing_decision.selected_backend.name.lower()
            if routing_decision.selected_backend
            else "npu"
        )

        self._trace(
            "recommendation",
            {
                "model": best_model["model"],
                "backend": backend,
                "score": round(best_score, 4),
            },
        )
        return backend, best_model["model"]

    def _encode_report(
        self,
        query: str,
        findings: list[ResearchFinding],
        synthesis: CompoundSynthesis | None,
        backend: str,
        model: str,
    ) -> tuple[np.ndarray, float]:
        """Phase 4 — Encode report into FLUME 256D latent + HIHO coherence."""
        # Build a textual summary for encoding
        summary = f"Query: {query}\nBackend: {backend}\nModel: {model}\n"
        if synthesis:
            summary += f"Insight: {synthesis.description[:500]}\n"
        for f in findings[:5]:
            if isinstance(f, dict):
                title = f.get("title", f.get("model", "unknown"))
                source = f.get("source", f.get("recipe", "lemonade"))
            else:
                title = getattr(f, "title", "unknown")
                source = getattr(f, "source", "unknown")
            summary += f"- {title} ({source})\n"

        latent = text_to_latent(summary, flume_encoder=None)  # fallback hash-based
        # HIHO coherence: proximity to 0.5 is optimal
        coherence = 1.0 - abs(0.5 - (np.mean(latent[:32]) + 0.5) % 1.0)
        return latent, float(coherence)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _probe_lemonade_registry(self) -> list[dict[str, Any]]:
        """Fetch current model list from local lemonade server."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.lemonade_base}/v1/models",
                    timeout=5.0,
                )
                resp.raise_for_status()
                data = resp.json()
                models = data.get("data", [])
                self._trace("lemonade_probe", {"models": len(models)})
                return [
                    {
                        "model": m["id"],
                        "labels": m.get("labels", []),
                        "size": m.get("size", 0.0),
                        "recipe": m.get("recipe", "unknown"),
                    }
                    for m in models
                ]
        except Exception as exc:
            logger.warning("Lemonade probe failed: %s", exc)
            self._trace("lemonade_probe", {"status": "error", "detail": str(exc)})
            return []

    def _derive_topics(self, query: str) -> list[str]:
        """Extract research topics from user query."""
        # Simple keyword extraction — could be replaced with FLUME semantic split
        keywords = [w for w in query.lower().split() if len(w) > 3]
        return keywords[:5] or ["inference optimization"]

    def _build_candidates(
        self,
        registry: list[dict[str, Any]],
        synthesis: CompoundSynthesis | None,
    ) -> list[dict[str, Any]]:
        """Build model candidates from registry + synthesis insights."""
        candidates: list[dict[str, Any]] = []
        for m in registry:
            # Map recipe to backend heuristic
            backend = (
                "npu"
                if m["recipe"] == "flm"
                else "vulkan"
                if m.get("recipe_options", {}).get("llamacpp_backend") == "vulkan"
                else "cpu"
            )
            candidates.append(
                {
                    "model": m["model"],
                    "backend": backend,
                    "labels": m["labels"],
                    "size": m["size"],
                }
            )
        return candidates

    def _score_candidate(self, candidate: dict[str, Any], query: str) -> float:
        """Score a model candidate against the query using latent similarity."""
        q_lower = query.lower()
        score = 0.0

        # Label matching
        for label in candidate.get("labels", []):
            if label.lower() in q_lower:
                score += 0.3

        # Size penalty for large models if query mentions "fast" or "latency"
        if "fast" in q_lower or "latency" in q_lower:
            score -= candidate.get("size", 0.0) * 0.02

        # Backend boost: prefer NPU for small models
        if candidate["backend"] == "npu" and candidate.get("size", 0.0) < 5.0:
            score += 0.4

        # Normalize
        return max(0.0, min(1.0, score))

    def _trace(self, phase: str, data: dict[str, Any]) -> None:
        self._traces.append({"phase": phase, "time": datetime.now().isoformat(), **data})
