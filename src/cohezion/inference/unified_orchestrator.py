"""Unified Orchestrator — single dispatch surface for all Cohezion inference.

Merges the patterns from 5 previously separate orchestrators into one
composable class:

    1. TieredOrchestrator — tier escalation with QualityGate
    2. SiliconSwarm       — adaptive node routing + experience collection
    3. AutoHarness        — Thompson sampling verification
    4. LatentEngine       — COCONUT/SoftCoT/CoE latent-space reasoning
    5. TriComputeOrch.    — NPU/iGPU/CPU workload decomposition

The key insight: all five share the same core loop::

    classify → route → verify → dispatch → score → collect trace → escalate?

This module provides that loop once, with pluggable strategies for each
phase.  Every future feature (circuit breakers, DPO training, dashboards)
integrates at exactly one point.

Compound engineering value:
    - Single integration surface for all new features
    - Pluggable strategies via Protocol classes
    - Built-in experience collection (every call → training signal)
    - Latent-space deliberation auto-activates for complex prompts
    - AutoHarness verification gate slots in before dispatch

Usage::

    from cohezion.inference.unified_orchestrator import (
        UnifiedOrchestrator,
        create_default_orchestrator,
    )

    orch = create_default_orchestrator()
    await orch.start()

    # Simple prompt — auto-routed
    result = await orch.run("Summarize this PR diff")

    # Complex prompt — triggers LatentEngine + CoE scoring
    result = await orch.run("Prove that the Riemann Hypothesis implies GRH")

    # Batch dispatch — fan out across all nodes
    results = await orch.run_batch(["task A", "task B", "task C"])

    # Introspect
    print(orch.health_report())
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import httpx

from cohezion.config.defaults import (
    COMPLEXITY_THRESHOLD,
    CPU_SMALL_MODELS,
    LANE_MODELS,
    LANE_PORTS,
    MIN_QUALITY_ACCEPT,
    N_CPU_WORKERS,
    OLLAMA_BASE_URL,
    SCORE_WINDOW,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (reads from environment, falls back to sensible defaults)
# ---------------------------------------------------------------------------

OLLAMA_BASE = OLLAMA_BASE_URL
_MIN_QUALITY_ACCEPT = MIN_QUALITY_ACCEPT
_SCORE_WINDOW = SCORE_WINDOW
_COMPLEXITY_THRESHOLD = COMPLEXITY_THRESHOLD


# ---------------------------------------------------------------------------
# Enums & data types
# ---------------------------------------------------------------------------


class NodeKind(StrEnum):
    """Compute lane type."""

    NPU = "npu"
    IGPU = "igpu"
    CPU = "cpu"
    OLLAMA = "ollama"


class DispatchSource(StrEnum):
    """Which subsystem produced the result."""

    SWARM = "swarm"
    LATENT_ENGINE = "latent_engine"
    TIERED = "tiered"
    FALLBACK = "fallback"


@dataclass
class NodeMetrics:
    """Live metrics for a single compute node — sliding window."""

    node_id: str
    model: str
    kind: NodeKind
    latency_ms_window: deque = field(default_factory=lambda: deque(maxlen=SCORE_WINDOW))
    quality_window: deque = field(default_factory=lambda: deque(maxlen=SCORE_WINDOW))
    error_count: int = 0
    total_calls: int = 0
    consecutive_failures: int = 0
    last_error_at: float = 0.0
    circuit_open_until: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return (
            float(sum(self.latency_ms_window) / len(self.latency_ms_window))
            if self.latency_ms_window
            else 9999.0
        )

    @property
    def avg_quality(self) -> float:
        return (
            float(sum(self.quality_window) / len(self.quality_window))
            if self.quality_window
            else 0.0
        )

    @property
    def score(self) -> float:
        """Composite: quality / normalised latency.  Higher = better."""
        lat = max(self.avg_latency_ms, 1.0)
        return self.avg_quality / (lat / 1000.0 + 1.0)

    @property
    def circuit_is_open(self) -> bool:
        """True if node should be skipped (circuit breaker tripped)."""
        if self.consecutive_failures < 5:
            return False
        return time.time() < self.circuit_open_until

    def record_success(self, latency_ms: float, quality: float) -> None:
        """Record a successful call — resets circuit breaker."""
        self.latency_ms_window.append(latency_ms)
        self.quality_window.append(quality)
        self.total_calls += 1
        self.consecutive_failures = 0

    def record_error(self) -> None:
        """Record a failed call — may trip circuit breaker."""
        self.error_count += 1
        self.total_calls += 1
        self.consecutive_failures += 1
        self.last_error_at = time.time()
        self.quality_window.append(0.0)
        self.latency_ms_window.append(9999.0)
        if self.consecutive_failures >= 5:
            self.circuit_open_until = time.time() + 30.0
            logger.warning("Circuit breaker OPEN for node %s (30s cooldown)", self.node_id)


@dataclass
class UnifiedResult:
    """Result from any dispatch path — normalized interface."""

    text: str
    source: DispatchSource
    model: str = ""
    node_id: str = ""
    quality_score: float = 0.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    complexity: float = 0.0
    escalation_count: int = 0
    coe_assessment: dict[str, Any] | None = None
    error: str | None = None
    trace_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperienceTrace:
    """Trace emitted after each dispatch — feeds the evolution bridge."""

    trace_id: str
    prompt_digest: str
    source: str
    node_id: str
    model: str
    quality_score: float
    latency_ms: float
    complexity: float
    phi_score: float  # HIHO: 1 - |quality - 0.5| * 2
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Protocol interfaces — plug in custom strategies
# ---------------------------------------------------------------------------


@runtime_checkable
class QualityScorer(Protocol):
    """Scores response quality without a model call."""

    def score(
        self,
        text: str,
        prompt: str,
        *,
        text_trajectory: list[str] | None = None,
    ) -> float: ...


@runtime_checkable
class ActionVerifier(Protocol):
    """Validates an action before execution (AutoHarness pattern)."""

    def verify(self, action: str, context: dict[str, Any]) -> tuple[bool, str]: ...


# ---------------------------------------------------------------------------
# Built-in quality scorer (includes CoE integration)
# ---------------------------------------------------------------------------


class DefaultQualityScorer:
    """Compound quality scorer — heuristic + CoE geometric when available."""

    def score(
        self,
        text: str,
        prompt: str,
        *,
        text_trajectory: list[str] | None = None,
    ) -> float:
        """Score response quality [0.0, 1.0], <1ms, no model call."""
        if not text or len(text.strip()) < 3:
            return 0.0

        stripped = text.strip()

        # CoE path: geometric latent trajectory scoring
        if text_trajectory and len(text_trajectory) >= 2:
            try:
                from cohezion.flume.coe_evaluator import coe_quality_from_texts

                return coe_quality_from_texts(text_trajectory)
            except Exception:
                pass

        # Heuristic fallback
        target = max(20, len(prompt) * 0.2)
        length_score = min(1.0, len(stripped) / target)
        words = stripped.lower().split()
        diversity = len(set(words)) / max(len(words), 1)
        code_bonus = 0.1 if "```" in stripped and "code" in prompt.lower() else 0.0
        return min(1.0, 0.5 * length_score + 0.4 * diversity + code_bonus)


# ---------------------------------------------------------------------------
# Complexity classifier (determines latent-engine activation)
# ---------------------------------------------------------------------------


def classify_complexity(prompt: str) -> float:
    """Estimate task complexity [0, 1] — no model call, <0.1ms.

    Parameters
    ----------
    prompt : str
        The user's input prompt.

    Returns
    -------
    float
        Complexity score where >COMPLEXITY_THRESHOLD triggers LatentEngine.
    """
    length_score = min(1.0, len(prompt) / 1000.0)

    reasoning_keywords = {
        "prove",
        "derive",
        "explain why",
        "step by step",
        "reasoning",
        "compare",
        "contrast",
        "evaluate",
        "critique",
        "analyze",
        "analyse",
        "implement",
        "design",
        "architect",
        "optimize",
        "algorithm",
        "differential",
        "integral",
        "theorem",
        "proof",
    }
    lower_prompt = prompt.lower()
    keyword_score = min(1.0, sum(1 for k in reasoning_keywords if k in lower_prompt) / 4.0)
    question_score = min(1.0, prompt.count("?") * 0.2)
    code_score = 0.3 if "```" in prompt or "def " in prompt or "class " in prompt else 0.0

    return min(
        1.0,
        0.3 * length_score + 0.4 * keyword_score + 0.1 * question_score + 0.2 * code_score,
    )


# ---------------------------------------------------------------------------
# Adaptive Router — ranks nodes by live composite score
# ---------------------------------------------------------------------------


class AdaptiveRouter:
    """Thread-safe node ranking with built-in circuit breakers.

    Re-ranks nodes before every dispatch. Nodes that trip the circuit
    breaker are excluded until recovery timeout.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, NodeMetrics] = {}
        self._lock = asyncio.Lock()

    def register(self, node_id: str, model: str, kind: NodeKind) -> NodeMetrics:
        """Register a compute node."""
        if node_id not in self._metrics:
            self._metrics[node_id] = NodeMetrics(node_id=node_id, model=model, kind=kind)
        return self._metrics[node_id]

    async def record_success(self, node_id: str, latency_ms: float, quality: float) -> None:
        """Record successful dispatch."""
        async with self._lock:
            if node_id in self._metrics:
                self._metrics[node_id].record_success(latency_ms, quality)

    async def record_error(self, node_id: str) -> None:
        """Record failed dispatch — may trip circuit breaker."""
        async with self._lock:
            if node_id in self._metrics:
                self._metrics[node_id].record_error()

    def ranked_nodes(self, kind_filter: NodeKind | None = None) -> list[NodeMetrics]:
        """Return nodes best-first, excluding circuit-broken ones."""
        nodes = list(self._metrics.values())
        if kind_filter is not None:
            nodes = [n for n in nodes if n.kind == kind_filter]
        # Exclude circuit-broken and sustained-error nodes
        healthy = [
            n
            for n in nodes
            if not n.circuit_is_open and (n.avg_quality > 0.05 or n.total_calls < 3)
        ]
        return sorted(healthy, key=lambda n: n.score, reverse=True)

    def all_metrics(self) -> list[dict[str, Any]]:
        """Export all node metrics for dashboards."""
        return [
            {
                "node_id": m.node_id,
                "model": m.model,
                "kind": str(m.kind),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "avg_quality": round(m.avg_quality, 3),
                "score": round(m.score, 4),
                "total_calls": m.total_calls,
                "error_count": m.error_count,
                "circuit_open": m.circuit_is_open,
            }
            for m in sorted(self._metrics.values(), key=lambda n: n.score, reverse=True)
        ]


# ---------------------------------------------------------------------------
# Experience Collector — trace persistence + evolution bridge
# ---------------------------------------------------------------------------


class ExperienceCollector:
    """Buffers traces and flushes to EvolutionTrainingBridge.

    Every dispatch call automatically contributes a training signal.
    """

    def __init__(self, flush_every: int = 10) -> None:
        self._buffer: list[ExperienceTrace] = []
        self._flush_every = flush_every
        self._trace_dir = Path("execution_traces/unified")
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record(self, trace: ExperienceTrace) -> None:
        """Buffer a trace, flush if threshold reached."""
        async with self._lock:
            self._buffer.append(trace)
            self._persist(trace)
            if len(self._buffer) >= self._flush_every:
                await self._flush()

    def _persist(self, trace: ExperienceTrace) -> None:
        """Write trace as JSON for Meta-Harness auditing."""
        path = self._trace_dir / f"{int(trace.timestamp)}_{trace.trace_id[:8]}.json"
        try:
            path.write_text(
                json.dumps(
                    {
                        "trace_id": trace.trace_id,
                        "prompt_digest": trace.prompt_digest,
                        "source": trace.source,
                        "node_id": trace.node_id,
                        "model": trace.model,
                        "quality_score": trace.quality_score,
                        "latency_ms": trace.latency_ms,
                        "complexity": trace.complexity,
                        "phi_score": trace.phi_score,
                        "timestamp": trace.timestamp,
                    },
                    indent=2,
                )
            )
        except Exception as exc:
            logger.debug("Trace persist failed: %s", exc)

    async def _flush(self) -> None:
        """Push buffered traces to EvolutionTrainingBridge."""
        traces = list(self._buffer)
        self._buffer.clear()

        try:
            from cohezion.compound.evolution_training_bridge import (
                EvolutionTrainingBridge,
                EvolutionTrainingConfig,
            )
            from cohezion.compound.group_evolution import (
                ExperienceTrace as EvTrace,
            )
            from cohezion.compound.group_evolution import (
                TaskSuccessVector,
            )

            cfg = EvolutionTrainingConfig()
            bridge = EvolutionTrainingBridge(cfg)

            exp_traces = []
            for t in traces:
                sv = TaskSuccessVector(successes=[t.quality_score, t.phi_score])
                exp_traces.append(
                    EvTrace(
                        agent_id=t.node_id,
                        task_id=t.trace_id,
                        quality_score=t.quality_score,
                        success_vector=sv,
                        metadata={
                            "source": t.source,
                            "latency_ms": t.latency_ms,
                            "complexity": t.complexity,
                        },
                    )
                )

            if exp_traces:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: bridge.process_experience_traces(exp_traces)
                )
                logger.info(
                    "Unified: flushed %d traces to EvolutionBridge",
                    len(exp_traces),
                )
        except Exception as exc:
            logger.debug("Evolution bridge flush skipped: %s", exc)


# ---------------------------------------------------------------------------
# HTTP dispatch helpers
# ---------------------------------------------------------------------------


async def _call_lemonade(
    port: int,
    model_id: str,
    prompt: str,
    *,
    max_tokens: int = 512,
    timeout: float = 45.0,
) -> tuple[str, float]:
    """Dispatch to Lemonade/llama-server OpenAI-compat endpoint.

    Returns
    -------
    tuple[str, float]
        (completion_text, latency_ms)
    """
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)
    ) as client:
        resp = await client.post(f"http://localhost:{port}/v1/chat/completions", json=payload)
        resp.raise_for_status()
    latency_ms = (time.perf_counter() - t0) * 1000
    data = resp.json()
    text = data["choices"][0]["message"].get("content", "")
    if not text.strip():
        text = data["choices"][0]["message"].get("reasoning_content", "")
    return text, latency_ms


async def _call_ollama(
    model: str,
    prompt: str,
    *,
    max_tokens: int = 512,
    timeout: float = 60.0,
) -> tuple[str, float]:
    """Dispatch to local Ollama /api/generate.

    Returns
    -------
    tuple[str, float]
        (completion_text, latency_ms)
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=timeout, write=timeout, pool=timeout)
    ) as client:
        resp = await client.post(f"{OLLAMA_BASE}/api/generate", json=payload)
        resp.raise_for_status()
    latency_ms = (time.perf_counter() - t0) * 1000
    data = resp.json()
    return data.get("response", ""), latency_ms


# ---------------------------------------------------------------------------
# Main Unified Orchestrator
# ---------------------------------------------------------------------------


class UnifiedOrchestrator:
    """Single dispatch surface for all Cohezion inference.

    Lifecycle::

        orch = UnifiedOrchestrator()
        await orch.start()       # probe nodes
        result = await orch.run(prompt)
        await orch.stop()

    Parameters
    ----------
    cpu_models : list[str] | None
        Ollama models for CPU workers. Defaults to CPU_SMALL_MODELS.
    n_cpu_workers : int
        Max concurrent CPU workers.
    quality_scorer : QualityScorer | None
        Custom quality scorer. Defaults to DefaultQualityScorer.
    action_verifier : ActionVerifier | None
        AutoHarness verifier. If set, actions are verified before dispatch.
    complexity_threshold : float
        Prompts above this score activate LatentEngine deliberation.
    enable_latent : bool
        Whether to use LatentEngine for complex prompts.
    experience_flush_every : int
        Flush experience traces every N dispatches.
    """

    def __init__(
        self,
        *,
        cpu_models: list[str] | None = None,
        n_cpu_workers: int = N_CPU_WORKERS,
        quality_scorer: QualityScorer | None = None,
        action_verifier: ActionVerifier | None = None,
        complexity_threshold: float = COMPLEXITY_THRESHOLD,
        enable_latent: bool = True,
        experience_flush_every: int = 10,
    ) -> None:
        self._cpu_models = cpu_models or CPU_SMALL_MODELS
        self._n_cpu_workers = n_cpu_workers
        self._router = AdaptiveRouter()
        self._scorer = quality_scorer or DefaultQualityScorer()
        self._verifier = action_verifier
        self._complexity_threshold = complexity_threshold
        self._enable_latent = enable_latent
        self._collector = ExperienceCollector(flush_every=experience_flush_every)
        self._cpu_sem = asyncio.Semaphore(n_cpu_workers)
        self._running = False

        self._register_all_nodes()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _register_all_nodes(self) -> None:
        """Register all silicon lanes + Ollama CPU workers."""
        for lane_name, port in LANE_PORTS.items():
            kind = (
                NodeKind.NPU
                if lane_name == "npu"
                else (NodeKind.IGPU if "igpu" in lane_name else NodeKind.CPU)
            )
            model_id = LANE_MODELS[lane_name]
            self._router.register(f"lemonade:{lane_name}", model_id, kind)

        for model in self._cpu_models:
            self._router.register(f"ollama:{model}", model, NodeKind.OLLAMA)

    async def start(self) -> None:
        """Probe all nodes and mark unreachable ones."""
        self._running = True
        probes = []
        for lane_name, port in LANE_PORTS.items():
            probes.append(self._probe_lemonade(lane_name, port))
        probes.append(self._probe_ollama())
        await asyncio.gather(*probes, return_exceptions=True)
        logger.info("UnifiedOrchestrator started — probed %d groups", len(probes))

    async def stop(self) -> None:
        """Shutdown: flush pending traces."""
        self._running = False
        await self._collector._flush()

    async def _probe_lemonade(self, lane: str, port: int) -> None:
        """Liveness check via /v1/models."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://localhost:{port}/v1/models")
                if resp.status_code == 200:
                    logger.debug("Lane %s (%d) UP", lane, port)
                    return
        except Exception:
            pass
        logger.debug("Lane %s (%d) DOWN", lane, port)
        node_id = f"lemonade:{lane}"
        for _ in range(3):
            await self._router.record_error(node_id)

    async def _probe_ollama(self) -> None:
        """Check which Ollama models are available."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{OLLAMA_BASE}/api/tags")
                if resp.status_code != 200:
                    return
            data = resp.json()
            available = {m["name"] for m in data.get("models", [])}
            for model in self._cpu_models:
                base = model.split(":")[0]
                hit = any(base in a for a in available)
                if not hit:
                    node_id = f"ollama:{model}"
                    for _ in range(3):
                        await self._router.record_error(node_id)
        except Exception as exc:
            logger.debug("Ollama probe failed: %s", exc)

    # ------------------------------------------------------------------
    # Core dispatch loop
    # ------------------------------------------------------------------

    async def run(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        prefer_kind: NodeKind | None = None,
        timeout: float = 60.0,
    ) -> UnifiedResult:
        """Unified dispatch: classify → route → verify → dispatch → score.

        Parameters
        ----------
        prompt : str
            User prompt.
        max_tokens : int
            Max tokens for generation.
        prefer_kind : NodeKind | None
            Restrict to a specific compute lane.
        timeout : float
            Per-node timeout in seconds.

        Returns
        -------
        UnifiedResult
            Normalized result with quality, trace, and source metadata.
        """
        t_start = time.perf_counter()
        trace_id = str(uuid4())[:12]
        prompt_digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        complexity = classify_complexity(prompt)

        # Phase 1: AutoHarness verification (if configured)
        if self._verifier is not None:
            ok, reason = self._verifier.verify(prompt, {"complexity": complexity})
            if not ok:
                return UnifiedResult(
                    text="",
                    source=DispatchSource.FALLBACK,
                    error=f"AutoHarness rejected: {reason}",
                    trace_id=trace_id,
                    complexity=complexity,
                )

        # Phase 2: Latent-space deliberation for complex prompts
        if self._enable_latent and complexity >= self._complexity_threshold:
            latent_result = await self._dispatch_latent(
                prompt, max_tokens=max_tokens, trace_id=trace_id
            )
            if latent_result is not None:
                latent_result.complexity = complexity
                latent_result.latency_ms = (time.perf_counter() - t_start) * 1000
                await self._record_trace(latent_result, prompt_digest, complexity)
                return latent_result

        # Phase 3: Adaptive swarm dispatch (standard path)
        result = await self._dispatch_swarm(
            prompt,
            max_tokens=max_tokens,
            prefer_kind=prefer_kind,
            timeout=timeout,
            trace_id=trace_id,
        )
        result.complexity = complexity
        result.latency_ms = (time.perf_counter() - t_start) * 1000
        await self._record_trace(result, prompt_digest, complexity)
        return result

    async def run_batch(
        self,
        prompts: list[str],
        *,
        max_tokens: int = 512,
        timeout: float = 90.0,
    ) -> list[UnifiedResult]:
        """Fan out multiple prompts, bounded by CPU semaphore.

        Parameters
        ----------
        prompts : list[str]
            Prompts to dispatch independently.
        max_tokens : int
            Max tokens per generation.
        timeout : float
            Per-prompt timeout.

        Returns
        -------
        list[UnifiedResult]
            Results in same order as prompts.
        """

        async def _bounded(p: str) -> UnifiedResult:
            async with self._cpu_sem:
                return await self.run(p, max_tokens=max_tokens, timeout=timeout)

        return list(await asyncio.gather(*[_bounded(p) for p in prompts]))

    # ------------------------------------------------------------------
    # Dispatch strategies
    # ------------------------------------------------------------------

    async def _dispatch_swarm(
        self,
        prompt: str,
        *,
        max_tokens: int,
        prefer_kind: NodeKind | None,
        timeout: float,
        trace_id: str,
    ) -> UnifiedResult:
        """Dispatch via adaptive routing — escalate until quality passes."""
        ranked = self._router.ranked_nodes(kind_filter=prefer_kind)
        if not ranked:
            ranked = self._router.ranked_nodes()

        best_text = ""
        best_quality = 0.0
        best_node = "none"
        best_model = ""
        escalation_count = 0

        for node in ranked:
            text, quality, latency_ms = await self._call_node(
                node, prompt, max_tokens=max_tokens, timeout=timeout
            )
            escalation_count += 1

            if quality > best_quality:
                best_quality = quality
                best_text = text
                best_node = node.node_id
                best_model = node.model

            if quality >= MIN_QUALITY_ACCEPT:
                break  # Good enough

        return UnifiedResult(
            text=best_text,
            source=DispatchSource.SWARM,
            model=best_model,
            node_id=best_node,
            quality_score=best_quality,
            escalation_count=escalation_count,
            trace_id=trace_id,
        )

    async def _dispatch_latent(
        self,
        prompt: str,
        *,
        max_tokens: int,
        trace_id: str,
    ) -> UnifiedResult | None:
        """Dispatch via LatentEngine for complex prompts.

        Returns None if LatentEngine is unavailable (graceful degradation).
        """
        try:
            from cohezion.flume.latent_engine import LatentEngine

            engine = LatentEngine(
                small_model="qwen3:1.7b",
                medium_model="phi4-mini",
            )
            result = await engine.reason(
                prompt,
                use_soft_cot=True,
                use_coconut=True,
                use_recurrent=False,
                max_tokens=max_tokens,
            )
            return UnifiedResult(
                text=result.final_answer,
                source=DispatchSource.LATENT_ENGINE,
                model="latent_engine",
                quality_score=result.confidence,
                coe_assessment=result.coe_assessment,
                trace_id=trace_id,
                metadata={
                    "coconut_bfs_explored": result.coconut_bfs_explored,
                    "soft_prefix_used": result.soft_prefix_used,
                    "state_depth": len(result.state_trajectory),
                },
            )
        except ImportError:
            logger.debug("LatentEngine unavailable — falling back to swarm")
            return None
        except Exception as exc:
            logger.warning("LatentEngine error: %s — falling back to swarm", exc)
            return None

    async def _call_node(
        self,
        node: NodeMetrics,
        prompt: str,
        *,
        max_tokens: int,
        timeout: float,
    ) -> tuple[str, float, float]:
        """Dispatch to a specific node with circuit breaker.

        Returns
        -------
        tuple[str, float, float]
            (text, quality_score, latency_ms)
        """
        # Circuit breaker check
        if node.circuit_is_open:
            logger.debug("Skipping %s — circuit breaker open", node.node_id)
            return "", 0.0, 9999.0

        try:
            if node.kind == NodeKind.OLLAMA:
                text, latency_ms = await _call_ollama(
                    node.model, prompt, max_tokens=max_tokens, timeout=timeout
                )
            else:
                lane = node.node_id.split(":", 1)[1]
                port = LANE_PORTS.get(lane, 13309)
                text, latency_ms = await _call_lemonade(
                    port,
                    node.model,
                    prompt,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )

            quality = self._scorer.score(text, prompt)
            await self._router.record_success(node.node_id, latency_ms, quality)
            return text, quality, latency_ms

        except Exception as exc:
            logger.warning("Node %s failed: %s", node.node_id, exc)
            await self._router.record_error(node.node_id)
            return "", 0.0, 9999.0

    # ------------------------------------------------------------------
    # Experience collection
    # ------------------------------------------------------------------

    async def _record_trace(
        self,
        result: UnifiedResult,
        prompt_digest: str,
        complexity: float,
    ) -> None:
        """Emit an experience trace for every dispatch."""
        phi = 1.0 - abs(result.quality_score - 0.5) * 2
        trace = ExperienceTrace(
            trace_id=result.trace_id,
            prompt_digest=prompt_digest,
            source=str(result.source),
            node_id=result.node_id,
            model=result.model,
            quality_score=result.quality_score,
            latency_ms=result.latency_ms,
            complexity=complexity,
            phi_score=phi,
        )
        await self._collector.record(trace)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def health_report(self) -> dict[str, Any]:
        """Full orchestrator health snapshot.

        Returns
        -------
        dict[str, Any]
            Includes node metrics, healthy count, top node, averages.
        """
        metrics = self._router.all_metrics()
        healthy = [m for m in metrics if m["avg_quality"] > 0.2]
        return {
            "total_nodes": len(metrics),
            "healthy_nodes": len(healthy),
            "circuit_open_nodes": sum(1 for m in metrics if m.get("circuit_open")),
            "top_node": metrics[0]["node_id"] if metrics else "none",
            "avg_quality": round(
                sum(m["avg_quality"] for m in healthy) / max(len(healthy), 1),
                3,
            ),
            "avg_latency_ms": round(
                sum(m["avg_latency_ms"] for m in healthy) / max(len(healthy), 1),
                1,
            ),
            "nodes": metrics,
        }

    def node_report(self) -> list[dict[str, Any]]:
        """Export live metrics for all nodes."""
        return self._router.all_metrics()


# ---------------------------------------------------------------------------
# Singleton + factory
# ---------------------------------------------------------------------------

_instance: UnifiedOrchestrator | None = None
_instance_lock = asyncio.Lock()


async def get_orchestrator(
    *,
    cpu_models: list[str] | None = None,
    n_cpu_workers: int = N_CPU_WORKERS,
) -> UnifiedOrchestrator:
    """Return process-level UnifiedOrchestrator singleton (lazy-init).

    Parameters
    ----------
    cpu_models : list[str] | None
        Override default CPU models.
    n_cpu_workers : int
        Override CPU worker count.

    Returns
    -------
    UnifiedOrchestrator
        Initialized and probed orchestrator.
    """
    global _instance
    if _instance is None:
        async with _instance_lock:
            if _instance is None:
                _instance = UnifiedOrchestrator(
                    cpu_models=cpu_models,
                    n_cpu_workers=n_cpu_workers,
                )
                await _instance.start()
    return _instance


def create_default_orchestrator(**kwargs: Any) -> UnifiedOrchestrator:
    """Factory — create a fresh (non-singleton) orchestrator.

    Parameters
    ----------
    **kwargs
        Forwarded to UnifiedOrchestrator constructor.

    Returns
    -------
    UnifiedOrchestrator
        Fresh orchestrator instance (call .start() before use).
    """
    return UnifiedOrchestrator(**kwargs)


# ---------------------------------------------------------------------------
# Convenience one-liners (mirror distributed_swarm API)
# ---------------------------------------------------------------------------


async def unified_dispatch(prompt: str, **kwargs: Any) -> UnifiedResult:
    """One-liner: dispatch via global orchestrator.

    Parameters
    ----------
    prompt : str
        User prompt.
    **kwargs
        Forwarded to UnifiedOrchestrator.run().

    Returns
    -------
    UnifiedResult
        Normalized result.
    """
    orch = await get_orchestrator()
    return await orch.run(prompt, **kwargs)


async def unified_batch(prompts: list[str], **kwargs: Any) -> list[UnifiedResult]:
    """One-liner: batch dispatch via global orchestrator.

    Parameters
    ----------
    prompts : list[str]
        Prompts to dispatch.
    **kwargs
        Forwarded to UnifiedOrchestrator.run_batch().

    Returns
    -------
    list[UnifiedResult]
        Results in same order.
    """
    orch = await get_orchestrator()
    return await orch.run_batch(prompts, **kwargs)
