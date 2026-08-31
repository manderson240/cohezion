"""Unified Hybrid Router for Cohezion.

Implements 3-tier model routing (Tier 1 Local -> Tier 2 Ollama Cloud -> Tier 3 Premium API)
gated by Expected Value of Intervention (EVI > 0.75).
"""

from __future__ import annotations

# reconcile 2026-08-26: imports needed by branch-preserved code
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cohezion.core.event_bus import Event, EventBus, get_event_bus
from cohezion.inference.delegation_logger import DelegationEvent, DelegationLogger
from cohezion.inference.lemonade_health import LemonadeHealth, probe_lemonade
from cohezion.reliability import get_circuit
from cohezion.reliability.oom_guard import OOMGuard


# --- reconcile 2026-08-26: top-level symbols preserved from the branch ---
LEMONADE_BASE = "http://localhost:13305"


LEMONADE_URL = f"{LEMONADE_BASE}/v1/chat/completions"


OLLAMA_URL = "http://localhost:11434/api/generate"


VRAM_SATURATION_THRESHOLD: float = 0.90


class TaskClass(StrEnum):
    """Hard-pinned task classes for lane routing."""

    REASONING = "reasoning"
    DEEP_REASONING = "deep_reasoning"
    CODING = "coding"
    CODING_TOOLS = "coding_tools"
    VISION = "vision"
    RESEARCH = "research"
    SCIENCE_FRONTIER = "science_frontier"
    FAST_QA = "fast_qa"
    ULTRA_FAST_DRAFT = "ultra_fast_draft"
    SUB_BILLION_EDGE = "sub_billion_edge"
    EXTREME_COMPACT = "extreme_compact"
    LONG_CONTEXT_ANALYSIS = "long_context_analysis"
    CREATIVE_SYNTHESIS = "creative_synthesis"
    EMBEDDINGS = "embeddings"
    GENERAL = "general"


_TIER1_PINS: dict[TaskClass, str] = {
    TaskClass.REASONING: "deepseek-r1-0528-8b-FLM",
    TaskClass.DEEP_REASONING: "DeepSeek-Qwen3-8B-GGUF",
    TaskClass.CODING: "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    TaskClass.CODING_TOOLS: "waslmedia-qwen3-4b-Q4_K_M",
    TaskClass.VISION: "qwen3vl-it-4b-FLM",
    TaskClass.RESEARCH: "qwen3.6-moe-35b-a3b-FLM",
    TaskClass.SCIENCE_FRONTIER: "deepseek-r1-0528-8b-FLM",
    TaskClass.FAST_QA: "qwen3-4b-FLM",
    TaskClass.ULTRA_FAST_DRAFT: "llama3.2-1b-FLM",
    TaskClass.SUB_BILLION_EDGE: "Qwen3-0.6B-GGUF",
    TaskClass.EXTREME_COMPACT: "Bonsai-1.7B-gguf",
    TaskClass.LONG_CONTEXT_ANALYSIS: "qwen3.6-moe-35b-a3b-FLM",
    TaskClass.CREATIVE_SYNTHESIS: "qwen3.6-moe-35b-a3b-FLM",
    TaskClass.EMBEDDINGS: "embed-gemma-300m-FLM",
    TaskClass.GENERAL: "qwen3.6-moe-35b-a3b-FLM",
}


_TIER2_PINS: dict[TaskClass, str] = {
    TaskClass.REASONING: "deepseek-v4-pro:cloud",  # 1.6T MoE Top Reasoning & Formal Logic
    TaskClass.DEEP_REASONING: "kimi-k3:cloud",  # Kimi K3 Autonomous Deep Reasoning
    TaskClass.CODING: "qwen3.5:397b-cloud",  # 397B Multi-File System Refactors
    TaskClass.CODING_TOOLS: "kimi-k2.7-code:cloud",  # Agentic Tool Use & Precise Patch Gen
    TaskClass.VISION: "glm-5.2:cloud",  # Multimodal Geometry, Category Theory & Diagram Parsing
    TaskClass.RESEARCH: "nemotron-3-ultra:cloud",  # Frontier Enterprise Knowledge Synthesis
    TaskClass.SCIENCE_FRONTIER: "nemotron-3-super:cloud",  # Frontier Physics, Science & Math Verification
    TaskClass.FAST_QA: "deepseek-v4-flash:cloud",  # Ultra-Fast High-Throughput Retrieval
    TaskClass.ULTRA_FAST_DRAFT: "deepseek-v4-flash:0731-cloud",  # Sub-Second Low-Latency Draft Generation
    TaskClass.SUB_BILLION_EDGE: "deepseek-v4-flash:0731-cloud",  # Fast edge fallback
    TaskClass.CREATIVE_SYNTHESIS: "minimax-m3:cloud",  # Nuanced Narrative, PRD & Creative Synthesis
    TaskClass.EMBEDDINGS: "gemma4:31b-cloud",  # Dense Multilingual Semantic Vectors
    TaskClass.GENERAL: "gpt-oss:120b-cloud",  # Transparent Broad General Intelligence
}


_TIER3_PINS: dict[TaskClass, str] = {
    TaskClass.REASONING: "gemini-3.7-flash-high",
    TaskClass.DEEP_REASONING: "claude-opus-4-6-thinking",
    TaskClass.CODING: "claude-sonnet-4-6",
    TaskClass.CODING_TOOLS: "gemini-3.7-flash-high",
    TaskClass.VISION: "gemini-3.1-pro-high",
    TaskClass.RESEARCH: "gemini-3.7-flash-medium",
    TaskClass.SCIENCE_FRONTIER: "gemini-3.1-pro-high",
    TaskClass.FAST_QA: "gemini-3.7-flash-low",
    TaskClass.ULTRA_FAST_DRAFT: "gemini-3.7-flash-low",
    TaskClass.SUB_BILLION_EDGE: "gemini-3.7-flash-low",
    TaskClass.EXTREME_COMPACT: "gemini-3.7-flash-low",
    TaskClass.LONG_CONTEXT_ANALYSIS: "gemini-3.1-pro-high",
    TaskClass.CREATIVE_SYNTHESIS: "claude-opus-4-6-thinking",
    TaskClass.EMBEDDINGS: "embed-gemma-300m-FLM",
    TaskClass.GENERAL: "gpt-oss-120b-medium",
}


@dataclass(frozen=True, slots=True)
class HybridRouteResponse:
    """Result of a routed inference call.

    Parameters
    ----------
    content : str
        The text content returned by the model.
    tier_used : str
        Human-readable label for the tier that served the request.
    model_name : str
        The exact model identifier used.
    latency_ms : float
        Elapsed round-trip latency in milliseconds.
    verified : bool
        ``True`` if the response came from a verified local/cloud model;
        ``False`` if served by synthetic fallback.
    task_class : TaskClass
        The task class used for routing.
    evi_score : float
        Estimated Value of Inference score at routing time (0-1).
    """

    content: str
    tier_used: str  # "Tier 0 (NPU)", "Tier 1 (NPU MoE / iGPU)", "Tier 2 (Ollama Cloud)"
    model_name: str
    latency_ms: float
    verified: bool
    task_class: TaskClass = TaskClass.GENERAL
    evi_score: float = 1.0


logger = logging.getLogger(__name__)

# Default cost units per tier escalation
TIER_COSTS = {
    (1, 2): 0.25,  # Escalation Tier 1 -> Tier 2 (Ollama Cloud)
    (2, 3): 1.00,  # Escalation Tier 2 -> Tier 3 (Premium API)
    (1, 3): 1.25,  # Escalation Tier 1 -> Tier 3
}

# Roster mappings
TIER_1_ROSTER = {
    "reasoning": "deepseek-r1-0528-8b-FLM",
    "coding": "Qwen3-Coder-30B",
    "coding_small": "qwen3-4b-FLM",
    "vision": "qwen3vl-it-4b-FLM",
    "research": "qwen3.6-moe-35b-a3b-FLM",
    "fast_qa": "llama3.2-1b-FLM",
    "embedding": "embed-gemma-300m-FLM",
    "cpu_parallel": "Phi-4-mini-3.8B-CPU-32T",
}

TIER_2_ROSTER = {
    "reasoning": "deepseek-v4-pro:cloud",
    "coding": "qwen3.5:397b-cloud",
    "research": "glm-5.2:cloud",
    "general": "deepseek-v4-pro:cloud",
}

TIER_3_ROSTER = {
    "architecture": "gemini-3-pro",
    "coding": "claude-3-5-sonnet",
    "general": "gemini-3-pro",
}


@dataclass
class RoutingResult:
    """Result of hybrid router decision."""

    selected_tier: int
    model_name: str
    evi_score: float
    escalated: bool
    reason: str


class UnifiedHybridRouter:
    """3-Tier Hybrid Router with EVI Gating (default EVI > 0.75)."""

    DEFAULT_EVI_THRESHOLD: float = 0.75

    def __init__(
        self,
        logger_instance: DelegationLogger | None = None,
        evi_threshold: float | None = None,
        *,
        npu_model: str = "qwen3.6-moe-35b-a3b-FLM",
        cloud_model: str = "deepseek-v4-pro:cloud",
        prefer_local: bool = True,
        lemonade_port: int = 13305,
    ) -> None:
        self.logger = logger_instance or DelegationLogger()
        # reconcile 2026-08-26: the branch's capability-routing state (route_by_capability /
        # route_query / aquery_* below) lives alongside main's EVI routing.
        self.npu_model = npu_model
        self.cloud_model = cloud_model
        self.prefer_local = prefer_local
        self.lemonade_port = lemonade_port
        self._lemonade_url = f"http://localhost:{lemonade_port}/v1/chat/completions"
        if evi_threshold is not None:
            self.evi_threshold = float(evi_threshold)
        else:
            env_val = os.getenv("COHEZION_EVI_THRESHOLD")
            self.evi_threshold = float(env_val) if env_val else self.DEFAULT_EVI_THRESHOLD

    def compute_evi(
        self,
        quality_gap: float,
        task_importance: float,
        source_tier: int,
        target_tier: int,
    ) -> float:
        """Compute Expected Value of Intervention (EVI).

        EVI = (quality_gap * task_importance) / escalation_cost
        """
        cost = TIER_COSTS.get((source_tier, target_tier), 1.0)
        return (quality_gap * task_importance) / max(cost, 1e-4)

    def route(
        self,
        task_type: str,
        task_importance: float = 0.5,
        estimated_tier1_quality: float = 0.8,
        target_quality_required: float = 0.9,
        tier1_saturated: bool = False,
        context_tokens: int = 4096,
        force_tier: int | None = None,
        prompt: str | None = None,
    ) -> RoutingResult:
        """Determine model and execution tier.

        Parameters:
        -----------
        task_type: str
            Category of task ('coding', 'reasoning', 'research', 'vision', 'fast_qa', 'architecture')
        task_importance: float
            Priority weight (0.0 to 1.0)
        estimated_tier1_quality: float
            Expected quality from local model (0.0 to 1.0)
        target_quality_required: float
            Required quality threshold (0.0 to 1.0)
        tier1_saturated: bool
            Whether Tier 1 NPU/iGPU VRAM > 90%
        context_tokens: int
            Input context size in tokens
        force_tier: Optional[int]
            Explicit override tier (1, 2, or 3)
        prompt: Optional[str]
            Optional task prompt encoded into FLUME 256D VAE latent space for geometric correspondence
        """
        if force_tier in (1, 2, 3):
            model = self._select_model_for_tier(force_tier, task_type)
            res = RoutingResult(
                selected_tier=force_tier,
                model_name=model,
                evi_score=1.0,
                escalated=False,
                reason=f"Explicit force_tier={force_tier} specified",
            )
            return res

        # Compute quality gap — geometrically derived via FLUME VAE if prompt provided
        if prompt:
            try:
                from cohezion.governance.flume_bridge import encode_prompt, flume_route_similarity

                prompt_z = encode_prompt(prompt)
                # Compute geometric correspondence against benchmark reference for task_type
                ref_capability = f"high quality {task_type} execution and deterministic reasoning"
                sim = flume_route_similarity(prompt_z, ref_capability)
                # Dynamic manifold quality gap derived from latent space distance
                quality_gap = max(0.0, 1.0 - sim)
            except Exception as exc:
                logger.debug("FLUME geometric correspondence fallback: %s", exc)
                quality_gap = max(0.0, target_quality_required - estimated_tier1_quality)
        else:
            quality_gap = max(0.0, target_quality_required - estimated_tier1_quality)

        # Baseline: Start at Tier 1 if not saturated and context fits Tier 1
        current_tier = 1
        selected_model = self._select_model_for_tier(1, task_type)

        # Check Tier 1 capability constraints
        tier1_capable = (not tier1_saturated) and (context_tokens <= 32768)

        if not tier1_capable or quality_gap > 0.1:
            # Evaluate escalation to Tier 2
            evi_1_to_2 = self.compute_evi(quality_gap, task_importance, 1, 2)

            if not tier1_capable or evi_1_to_2 > self.evi_threshold:
                # Escalate to Tier 2
                current_tier = 2
                selected_model = self._select_model_for_tier(2, task_type)

                # Check if Tier 2 is sufficient or if Tier 3 escalation is warranted
                if context_tokens > 100000 or (
                    task_type == "architecture" and task_importance > 0.85
                ):
                    evi_2_to_3 = self.compute_evi(quality_gap, task_importance, 2, 3)
                    if evi_2_to_3 > self.evi_threshold:
                        current_tier = 3
                        selected_model = self._select_model_for_tier(3, task_type)
                        reason = f"Tier 3 escalation (EVI={evi_2_to_3:.2f} > {self.evi_threshold:.2f}, high context/importance)"
                    else:
                        reason = (
                            f"Tier 2 escalation (EVI={evi_1_to_2:.2f} > {self.evi_threshold:.2f})"
                        )
                else:
                    reason = f"Tier 2 escalation (EVI={evi_1_to_2:.2f} > {self.evi_threshold:.2f})"
            else:
                reason = (
                    f"Tier 1 selected (EVI 1->2 = {evi_1_to_2:.2f} <= {self.evi_threshold:.2f})"
                )
        else:
            reason = "Tier 1 selected (quality gap minimal, capacity OK)"

        escalated = current_tier > 1
        result = RoutingResult(
            selected_tier=current_tier,
            model_name=selected_model,
            evi_score=self.compute_evi(quality_gap, task_importance, 1, current_tier)
            if current_tier > 1
            else 0.0,
            escalated=escalated,
            reason=reason,
        )

        # Log delegation event
        event = DelegationEvent(
            task_name=task_type,
            task_importance=task_importance,
            quality_gap=quality_gap,
            escalation_cost=TIER_COSTS.get((1, current_tier), 0.0),
            evi_score=result.evi_score,
            source_tier=1,
            target_tier=current_tier,
            escalated=escalated,
            model_selected=result.model_name,
            reason=result.reason,
        )
        self.logger.log_delegation(event)

        return result

    def _select_model_for_tier(self, tier: int, task_type: str) -> str:
        """Map task type to specific model in tier roster."""
        if tier == 1:
            return TIER_1_ROSTER.get(task_type, TIER_1_ROSTER["coding"])
        elif tier == 2:
            return TIER_2_ROSTER.get(task_type, TIER_2_ROSTER["general"])
        elif tier == 3:
            return TIER_3_ROSTER.get(task_type, TIER_3_ROSTER["general"])
        return "qwen3-4b-FLM"

    # --- reconcile 2026-08-26: methods preserved from the branch (worktree-virtual-soaring-shamir) ---
    async def route_by_capability(
        self,
        prompt: str,
        task_class: TaskClass = TaskClass.GENERAL,
        evi_score: float = 1.0,
        force_cloud: bool = False,
    ) -> HybridRouteResponse:
        """Route a prompt to the best available model based on task class.

        Routing logic:
        1. Preflight: probe Lemonade fleet health.
        2. If Tier-1 healthy & not saturated & ``prefer_local`` -> try Tier-1 pin.
        3. Fall through to Tier-2 Ollama cloud if Tier-1 is down/saturated.
        4. If all backends fail, return a synthetic Tier-0 fallback.

        Parameters
        ----------
        prompt : str
            The user prompt to route.
        task_class : TaskClass
            Task classification for lane selection.
        evi_score : float
            Estimated Value of Inference score (0-1). Values < 0.75 are
            logged as low-confidence decisions.
        force_cloud : bool
            Skip Tier-1 silicon and go directly to Tier-2 cloud.

        Returns
        -------
        HybridRouteResponse
            The response from the winning tier.
        """
        t0 = time.perf_counter()

        if evi_score < 0.75:
            logger.warning(
                "route_by_capability: low EVI score %.3f for task=%s; proceeding with caution",
                evi_score,
                task_class,
            )

        # --- preflight: Lemonade fleet health -------------------------
        tier1_available = False
        health: LemonadeHealth | None = None
        if self.prefer_local and not force_cloud:
            try:
                circuit = get_circuit(
                    "lemonade_preflight", failure_threshold=3, recovery_timeout=20.0
                )
                if circuit.allow_request():
                    health = await probe_lemonade(port=self.lemonade_port, timeout=2.0)
                    if health.ok:
                        tier1_available = True
                        circuit.record_success()
                    else:
                        circuit.record_failure()
                        logger.warning(
                            "Lemonade preflight failed (%s); falling to Tier-2",
                            health.summary,
                        )
            except Exception as exc:
                logger.warning("Lemonade preflight probe raised: %s", exc)

        # --- memory guard: if VRAM saturated force Tier-2 -------------
        mem = OOMGuard.get_memory_state()
        vram_saturated = (mem.used_gb / max(mem.total_gb, 1.0)) >= VRAM_SATURATION_THRESHOLD
        if not mem.is_safe or vram_saturated:
            tier1_available = False
            logger.warning(
                "OOMGuard: memory saturated/unsafe (%.1f/%.1f GiB used, saturated=%s); routing to Tier-2",
                mem.used_gb,
                mem.total_gb,
                vram_saturated,
            )

        # --- Special Handling: Embeddings ----------------------------
        if task_class == TaskClass.EMBEDDINGS:
            chosen_tier1_model = _TIER1_PINS.get(TaskClass.EMBEDDINGS, "embed-gemma-300m-FLM")
            if tier1_available:
                emb_res = await self.aquery_embedding(prompt, chosen_tier1_model)
                if emb_res is not None:
                    dt_ms = (time.perf_counter() - t0) * 1000.0
                    resp = HybridRouteResponse(
                        content=json.dumps(emb_res),
                        tier_used="Tier 1 (NPU Embedding)",
                        model_name=chosen_tier1_model,
                        latency_ms=round(dt_ms, 2),
                        verified=True,
                        task_class=task_class,
                        evi_score=evi_score,
                    )
                    await self._publish_routing_event(resp, "tier1_embedding_success")
                    return resp

            # Tier-2 fallback for embedding
            chosen_tier2_model = _TIER2_PINS.get(
                TaskClass.EMBEDDINGS, "nomic-embed-text-v2-moe-GGUF"
            )
            emb_res = await self.aquery_embedding(prompt, chosen_tier2_model)
            if emb_res is not None:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                resp = HybridRouteResponse(
                    content=json.dumps(emb_res),
                    tier_used="Tier 2 (iGPU Embedding Fallback)",
                    model_name=chosen_tier2_model,
                    latency_ms=round(dt_ms, 2),
                    verified=True,
                    task_class=task_class,
                    evi_score=evi_score,
                )
                await self._publish_routing_event(resp, "tier2_embedding_fallback")
                return resp

        # --- Tier-1: hard-pinned Lemonade model -----------------------
        chosen_tier1_model = _TIER1_PINS.get(task_class, self.npu_model)
        tier_label = "Tier 1 (Local NPU MoE)"
        if task_class == TaskClass.CODING:
            tier_label = "Tier 1 (iGPU Coder)"
        elif task_class == TaskClass.GENERAL:
            tier_label = "Tier 1 (iGPU General)"

        if tier1_available:
            local_res = await self.aquery_lemonade_local(prompt, chosen_tier1_model)
            if local_res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                resp = HybridRouteResponse(
                    content=local_res,
                    tier_used=tier_label,
                    model_name=chosen_tier1_model,
                    latency_ms=round(dt_ms, 2),
                    verified=True,
                    task_class=task_class,
                    evi_score=evi_score,
                )
                await self._publish_routing_event(resp, "tier1_success")
                return resp

        # --- Tier-2: Ollama cloud fallback ----------------------------
        chosen_tier2_model = _TIER2_PINS.get(task_class, self.cloud_model)
        cloud_res = await self.aquery_ollama_cloud(prompt, chosen_tier2_model)
        if cloud_res:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            resp = HybridRouteResponse(
                content=cloud_res,
                tier_used="Tier 2 (Ollama Cloud)",
                model_name=chosen_tier2_model,
                latency_ms=round(dt_ms, 2),
                verified=True,
                task_class=task_class,
                evi_score=evi_score,
            )
            await self._publish_routing_event(resp, "tier2_fallback")
            return resp

        # --- Tier-0: synthetic fallback (unverified) ------------------
        dt_ms = (time.perf_counter() - t0) * 1000.0
        fallback_model = "llama3.2-1b-FLM"
        resp = HybridRouteResponse(
            content=(
                f"[Local Silicon & Cloud Standby] Backends offline or busy. "
                f"Memory headroom: {mem.available_gb:.1f} GiB."
            ),
            tier_used="Tier 0 (Unverified Fallback)",
            model_name=fallback_model,
            latency_ms=round(dt_ms, 2),
            verified=False,
            task_class=task_class,
            evi_score=evi_score,
        )
        await self._publish_routing_event(resp, "tier0_fallback")
        return resp

    def route_query(self, prompt: str, force_cloud: bool = False) -> HybridRouteResponse:
        """Route query across Local Silicon -> Ollama Cloud -> Fallback.

        Parameters
        ----------
        prompt : str
            User prompt to route.
        force_cloud : bool
            Skip local silicon and go directly to cloud.

        Returns
        -------
        HybridRouteResponse
            Routing result.
        """
        t0 = time.perf_counter()

        # Step 1: Preflight Memory Headroom Safety Check
        mem = OOMGuard.get_memory_state()
        vram_saturated = (mem.used_gb / max(mem.total_gb, 1.0)) >= VRAM_SATURATION_THRESHOLD

        # Step 2: Try Local NPU / iGPU Silicon first if memory safe
        if self.prefer_local and not force_cloud and mem.is_safe and not vram_saturated:
            local_res = self.query_lemonade_local(prompt, self.npu_model)
            if local_res:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                return HybridRouteResponse(
                    content=local_res,
                    tier_used="Tier 1 (Local NPU MoE)",
                    model_name=self.npu_model,
                    latency_ms=round(dt_ms, 2),
                    verified=True,
                )

        # Step 3: Try Ollama Cloud Overflow
        cloud_res = self.query_ollama_cloud(prompt, self.cloud_model)
        if cloud_res:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            return HybridRouteResponse(
                content=cloud_res,
                tier_used="Tier 2 (Ollama Cloud)",
                model_name=self.cloud_model,
                latency_ms=round(dt_ms, 2),
                verified=True,
            )

        # Step 4: Fallback response (Unverified when backends fail)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return HybridRouteResponse(
            content=(
                f"[Local Silicon & Cloud Standby] Backends offline or busy."
                f" Memory headroom: {mem.available_gb} GiB."
            ),
            tier_used="Tier 0 (Unverified Fallback)",
            model_name="llama3.2-1b-FLM",
            latency_ms=round(dt_ms, 2),
            verified=False,
        )

    def query_lemonade_local(self, prompt: str, model: str) -> str | None:
        """Synchronous wrapper for aquery_lemonade_local."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self.aquery_lemonade_local(prompt, model)
                    ).result()
        except RuntimeError:
            pass
        return asyncio.run(self.aquery_lemonade_local(prompt, model))

    def query_ollama_cloud(self, prompt: str, model: str) -> str | None:
        """Synchronous wrapper for aquery_ollama_cloud."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run, self.aquery_ollama_cloud(prompt, model)
                    ).result()
        except RuntimeError:
            pass
        return asyncio.run(self.aquery_ollama_cloud(prompt, model))

    async def aquery_lemonade_local(self, prompt: str, model: str) -> str | None:
        """Attempt local NPU/iGPU inference via Lemonade (:13305) asynchronously with model-aligned options.

        Parameters
        ----------
        prompt : str
            The user prompt.
        model : str
            Lemonade model identifier (e.g. ``"deepseek-r1-0528-8b-FLM"``).

        Returns
        -------
        str | None
            Model response text, or ``None`` if the call fails.
        """
        import httpx

        # Model-aligned architectural parameters for Local Silicon (NPU/iGPU/CPU)
        temp = 0.2
        top_p = 0.95
        max_tokens = 2048

        if "deepseek-r1" in model or "Thinking" in model:
            # Deep reasoning local model: unhurried token allowance & low entropy
            temp = 0.1
            top_p = 0.90
            max_tokens = 4096
        elif "Coder" in model:
            # Deterministic code synthesis on iGPU
            temp = 0.05
            top_p = 0.85
            max_tokens = 4096
        elif "moe" in model:
            # NPU Mixture of Experts: balanced routing
            temp = 0.15
            top_p = 0.92
            max_tokens = 2048
        elif "1b" in model or "4b" in model:
            # Ultra-fast draft / fast QA on CPU/NPU
            temp = 0.2
            top_p = 0.90
            max_tokens = 1024

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temp,
            "top_p": top_p,
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(self._lemonade_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    msg = data["choices"][0]["message"]
                    raw = (msg.get("content") or msg.get("reasoning_content") or "").strip()
                    if "</think>" in raw:
                        raw = raw.split("</think>")[-1].strip()
                    return raw
        except Exception as exc:
            logger.debug("Local Lemonade query bypassed: %s", exc)

        return None

    async def aquery_embedding(
        self, text: str, model: str = "embed-gemma-300m-FLM"
    ) -> list[float] | None:
        """Fetch real embedding vector via Lemonade /v1/embeddings endpoint.

        Parameters
        ----------
        text : str
            Input text to embed.
        model : str
            Embedding model identifier.

        Returns
        -------
        list[float] | None
            Embedding float vector, or None on failure.
        """
        import httpx

        payload = {"model": model, "input": text}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post("http://localhost:13305/v1/embeddings", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    embedding: list[float] = data["data"][0]["embedding"]
                    return embedding
        except Exception as exc:
            logger.debug("Local Lemonade embedding bypassed: %s", exc)

        return None

    async def aquery_ollama_cloud(self, prompt: str, model: str) -> str | None:
        """Attempt Ollama Cloud model inference via Ollama (:11434) asynchronously with model-aligned options.

        Parameters
        ----------
        prompt : str
            The user prompt.
        model : str
            Ollama cloud model identifier (e.g. ``"deepseek-v4-pro:cloud"``).

        Returns
        -------
        str | None
            Model response text, or ``None`` if the call fails.
        """
        import httpx

        # Circuit breaker protection against cloud timeout storms
        from cohezion.reliability import get_circuit

        circuit = get_circuit("ollama_cloud", failure_threshold=3, recovery_timeout=20.0)
        if not circuit.allow_request():
            logger.warning("Ollama Cloud circuit breaker OPEN; bypassing to prevent timeout stall")
            return None

        # Model-aligned architectural options to maximize strengths & eliminate weaknesses
        options: dict[str, Any] = {"temperature": 0.2, "top_p": 0.95}
        if "deepseek-v4-pro" in model or "nemotron-3-super" in model:
            # High-precision reasoning & formal logic
            options = {"temperature": 0.1, "top_p": 0.9}
        elif "minimax-m3" in model or "creative" in model:
            # Nuanced creative & narrative synthesis
            options = {"temperature": 0.7, "top_p": 0.98}
        elif "qwen3.5:397b" in model or "kimi-k2.7" in model:
            # Deterministic code synthesis & refactoring
            options = {"temperature": 0.05, "top_p": 0.85}
        elif "flash" in model:
            # High-throughput low-latency retrieval
            options = {"temperature": 0.2, "top_p": 0.9}

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(OLLAMA_URL, json=payload)
                if res.status_code == 200:
                    circuit.record_success()
                    data = res.json()
                    raw = (data.get("response") or data.get("thinking") or "").strip()
                    if "</think>" in raw:
                        raw = raw.split("</think>")[-1].strip()
                    return raw
                circuit.record_failure()
                return None
        except Exception as exc:
            circuit.record_failure()
            logger.debug("Ollama Cloud query bypassed: %s", exc)
            return None

    async def _publish_routing_event(
        self,
        resp: HybridRouteResponse,
        decision: str,
    ) -> None:
        """Publish a routing decision event to the EventBus.

        Parameters
        ----------
        resp : HybridRouteResponse
            The completed routing response.
        decision : str
            Short label for the routing decision (e.g. ``"tier1_success"``).
        """
        try:
            bus: EventBus = await get_event_bus()
            event = Event.agent_complete(
                agent_name="UnifiedHybridRouter",
                result=decision,
                duration_ms=resp.latency_ms,
                tier=resp.tier_used,
                model=resp.model_name,
                task_class=str(resp.task_class),
                evi_score=resp.evi_score,
                verified=resp.verified,
            )
            await bus.publish(event)
        except Exception as exc:
            logger.debug("EventBus publish failed (non-critical): %s", exc)
