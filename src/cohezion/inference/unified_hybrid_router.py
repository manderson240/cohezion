r"""Unified Hybrid Silicon & Ollama Cloud Router Engine
=====================================================
Orchestrates inference across local silicon (NPU, iGPU, CPU) and Ollama Cloud models.

Routing Hierarchy:
  - Tier 0 (NPU Local): `llama3.2-1b-FLM` (TTFT ~24ms) for ultra-fast routing & drafts
  - Tier 1 (NPU MoE / iGPU Local): `qwen3.6-moe-35b-a3b-FLM`, `Qwen3-Coder-30B` for heavy local reasoning
  - Tier 2 (Ollama Cloud Overflow): `deepseek-v4-pro:cloud`, `glm-5.2:cloud`, `qwen3.5:397b-cloud` for ultra-large models
  - Tier 3 (Kanban Fallback): Persistent work item registration

Lane Pins (hard-pinned, 2026-08):
  Reasoning/planning     -> deepseek-r1-0528-8b-FLM   (NPU, port 13305)
  Coding/multi-file      -> Qwen3-Coder-30B            (iGPU, port 13305)
  Coding+tools small-ctx -> qwen3-4b-FLM               (NPU, port 13305)
  Vision/diagram         -> qwen3vl-it-4b-FLM          (NPU, port 13305)
  Research summary       -> qwen3.6-moe-35b-a3b-FLM   (NPU MoE, port 13305, pinned)
  Fast Q&A               -> llama3.2-1b-FLM            (NPU, port 13305, pre-warmed)
  Embeddings             -> embed-gemma-300m-FLM        (NPU, port 13305)

Tier-2 Ollama cloud fallback:
  Deep reasoning/math    -> deepseek-v4-pro:cloud
  Advanced coding        -> qwen3.5:397b-cloud
  Science/frontier       -> glm-5.2:cloud
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cohezion.core.event_bus import Event, EventBus, get_event_bus
from cohezion.inference.lemonade_health import LemonadeHealth, probe_lemonade
from cohezion.reliability import get_circuit
from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)

LEMONADE_BASE = "http://localhost:13305"
LEMONADE_URL = f"{LEMONADE_BASE}/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/generate"

# VRAM saturation threshold — above this we fall through to Tier 2
VRAM_SATURATION_THRESHOLD: float = 0.90


class TaskClass(StrEnum):
    """Hard-pinned task classes for lane routing."""

    REASONING = "reasoning"
    CODING = "coding"
    CODING_TOOLS = "coding_tools"
    VISION = "vision"
    RESEARCH = "research"
    FAST_QA = "fast_qa"
    EMBEDDINGS = "embeddings"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Tier-1 (Lemonade / local silicon) lane pins
# ---------------------------------------------------------------------------
_TIER1_PINS: dict[TaskClass, str] = {
    TaskClass.REASONING: "Gemma-4-26B-A4B-ThinkingCoder",
    TaskClass.CODING: "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    TaskClass.CODING_TOOLS: "Qwen3.6-35B-A3B-MTP-GGUF",
    TaskClass.VISION: "qwen3vl-it-4b-FLM",
    TaskClass.RESEARCH: "Gemma-4-31B-it-GGUF",
    TaskClass.FAST_QA: "gpt-oss-20b",
    TaskClass.EMBEDDINGS: "embed-gemma-300m-FLM",
    TaskClass.GENERAL: "Qwen3.8-27B-GGUF-Q5_K_M",
}

# ---------------------------------------------------------------------------
# Tier-2 (Ollama cloud) fallback pins
# ---------------------------------------------------------------------------
_TIER2_PINS: dict[TaskClass, str] = {
    TaskClass.REASONING: "deepseek-v4-pro:cloud",
    TaskClass.CODING: "qwen3.5:397b-cloud",
    TaskClass.CODING_TOOLS: "kimi-k2.7-code:cloud",
    TaskClass.VISION: "glm-5.2:cloud",
    TaskClass.RESEARCH: "nemotron-3-ultra:cloud",
    TaskClass.FAST_QA: "deepseek-v4-flash:cloud",
    TaskClass.EMBEDDINGS: "deepseek-v4-pro:cloud",
    TaskClass.GENERAL: "gpt-oss:120b-cloud",
}


@dataclass(frozen=True, slots=True)
class HybridRouteResponse:
    """Result of a routed inference call.

    Parameters
    ----------
    content : str
        The text content returned by the model.
    tier_used : str
        Routing tier label, e.g. ``"Tier 1 (Local NPU MoE)"``.
    model_name : str
        Model identifier that served the request.
    latency_ms : float
        Wall-clock latency in milliseconds.
    verified : bool
        True when the response came from a live model (not a synthetic fallback).
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


class UnifiedHybridRouter:
    """Hybrid silicon + cloud orchestrator enforcing quality & local priority.

    Parameters
    ----------
    npu_model : str
        Default NPU/iGPU model to use when no task class is specified.
    cloud_model : str
        Default Ollama cloud model to fall back to.
    prefer_local : bool
        If ``True`` (default), Tier-1 silicon is attempted before Tier-2 cloud.
    lemonade_port : int
        Port for the Lemonade OmniRouter.  Default 13305.
    """

    def __init__(
        self,
        npu_model: str = "qwen3.6-moe-35b-a3b-FLM",
        cloud_model: str = "deepseek-v4-pro:cloud",
        prefer_local: bool = True,
        lemonade_port: int = 13305,
    ) -> None:
        self.npu_model = npu_model
        self.cloud_model = cloud_model
        self.prefer_local = prefer_local
        self.lemonade_port = lemonade_port
        self._lemonade_url = f"http://localhost:{lemonade_port}/v1/chat/completions"

    # ------------------------------------------------------------------
    # Public: capability-aware routing
    # ------------------------------------------------------------------

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
        if not mem.is_safe:
            tier1_available = False
            logger.warning(
                "OOMGuard: memory unsafe (%.1f GiB free); routing to Tier-2",
                mem.available_gb,
            )

        # --- Tier-1: hard-pinned Lemonade model -----------------------
        chosen_tier1_model = _TIER1_PINS.get(task_class, self.npu_model)
        tier_label = "Tier 1 (Local NPU MoE)"
        if task_class == TaskClass.CODING:
            tier_label = "Tier 1 (iGPU Coder)"

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

    # ------------------------------------------------------------------
    # Public: legacy route_query (preserved for backwards compat)
    # ------------------------------------------------------------------

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

        # Step 2: Try Local NPU / iGPU Silicon first if memory safe
        if self.prefer_local and not force_cloud and mem.is_safe:
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

    # ------------------------------------------------------------------
    # Low-level transport helpers
    # ------------------------------------------------------------------

    def query_lemonade_local(self, prompt: str, model: str) -> str | None:
        """Synchronous wrapper for aquery_lemonade_local."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.aquery_lemonade_local(prompt, model)).result()
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
                    return pool.submit(asyncio.run, self.aquery_ollama_cloud(prompt, model)).result()
        except RuntimeError:
            pass
        return asyncio.run(self.aquery_ollama_cloud(prompt, model))

    async def aquery_lemonade_local(self, prompt: str, model: str) -> str | None:
        """Attempt local NPU/iGPU inference via Lemonade (:13305) asynchronously.

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
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self._lemonade_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    msg = data["choices"][0]["message"]
                    return (msg.get("content") or msg.get("reasoning_content") or "").strip()
        except Exception as exc:
            logger.debug("Local Lemonade query bypassed: %s", exc)

        return None

    async def aquery_embedding(self, text: str, model: str = "embed-gemma-300m-FLM") -> list[float] | None:
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
                    return data["data"][0]["embedding"]
        except Exception as exc:
            logger.debug("Local Lemonade embedding bypassed: %s", exc)

        return None

    async def aquery_ollama_cloud(self, prompt: str, model: str) -> str | None:
        """Attempt Ollama Cloud model inference via Ollama (:11434) asynchronously.

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
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(OLLAMA_URL, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("response", "").strip()
        except Exception as exc:
            logger.debug("Ollama Cloud query bypassed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
