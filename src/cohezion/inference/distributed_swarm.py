"""Distributed Silicon Swarm Executor.

Treats ALL local compute (NPU XDNA2, iGPU ROCWMMA, CPU Zen5 AVX-VNNI) as a
single, dynamically adaptive neural network.  Sub-tasks fan out across nodes in
parallel, results are aggregated/voted, and every execution produces an
ExperienceTrace that feeds the EvolutionTrainingBridge for online learning.

Core architecture (compound engineering — each piece makes the next easier):

    ┌─────────────────────────────────────────────────────────┐
    │                 SiliconSwarm (entry point)               │
    │                                                          │
    │  TaskDecomposer ──► SwarmNode pool ──► ResultAggregator │
    │       │                  │                  │            │
    │       │            [NPU, iGPU,            vote /         │
    │       │            CPU×N workers]         merge          │
    │       │                  │                  │            │
    │       └──────────────────┴──────────────────┘            │
    │                          │                               │
    │              ExperienceCollector                          │
    │         (traces → EvolutionBridge → learning)            │
    └─────────────────────────────────────────────────────────┘

Design constraints
------------------
- Zero blocking I/O in the hot path — all Ollama calls are async via httpx.
- CPU workers use asyncio semaphores to bound concurrency to N_CPU_WORKERS.
- Each node self-reports latency/quality; a live AdaptiveRouter re-ranks nodes
  after every batch so hot-path routing evolves without a restart.
- Graceful degradation: if a lane is down, the router skips it silently.
- Thread safety: all mutable shared state lives in asyncio-safe structures.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from cohezion.config.defaults import (
    CPU_SMALL_MODELS,
    LANE_PORTS,
    MIN_QUALITY_ACCEPT,
    N_CPU_WORKERS,
    OLLAMA_BASE_URL,
    SCORE_WINDOW,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & enums  (centralised in cohezion.config.defaults)
# ---------------------------------------------------------------------------

# Re-alias for internal use — values come from the central config module.
_LANE_PORTS = LANE_PORTS
_OLLAMA_BASE = OLLAMA_BASE_URL
_SCORE_WINDOW = SCORE_WINDOW
_MIN_QUALITY_ACCEPT = MIN_QUALITY_ACCEPT


class NodeKind(StrEnum):
    NPU = "npu"
    IGPU = "igpu"
    CPU = "cpu"
    OLLAMA = "ollama"  # CPU-side Ollama small models


class AggregationStrategy(StrEnum):
    FIRST_PASS = "first_pass"  # Return first accepted response
    MAJORITY_VOTE = "majority_vote"  # Best-of-N for short outputs
    WEIGHTED_BLEND = "weighted_blend"  # Score-weighted concatenation


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class NodeMetrics:
    """Live metrics for a single swarm node — updated after each call."""

    node_id: str
    model: str
    kind: NodeKind
    latency_ms_window: deque = field(default_factory=lambda: deque(maxlen=_SCORE_WINDOW))
    quality_window: deque = field(default_factory=lambda: deque(maxlen=_SCORE_WINDOW))
    error_count: int = 0
    total_calls: int = 0
    last_error_at: float = 0.0

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
        """Composite score: quality / normalised_latency.  Higher = better."""
        lat = max(self.avg_latency_ms, 1.0)
        return self.avg_quality / (lat / 1000.0 + 1.0)

    def record(self, latency_ms: float, quality: float) -> None:
        self.latency_ms_window.append(latency_ms)
        self.quality_window.append(quality)
        self.total_calls += 1

    def record_error(self) -> None:
        self.error_count += 1
        self.total_calls += 1
        self.last_error_at = time.time()
        self.quality_window.append(0.0)
        self.latency_ms_window.append(9999.0)


@dataclass
class SwarmResult:
    """Aggregated result from a swarm dispatch."""

    task_id: str
    prompt: str
    text: str
    strategy: AggregationStrategy
    node_results: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    winning_node: str = ""
    quality_score: float = 0.0
    error: str | None = None


@dataclass
class SwarmExperienceTrace:
    """Trace emitted after each swarm execution — fed to evolution bridge."""

    trace_id: str
    task_id: str
    prompt_digest: str  # sha256[:16] of prompt
    strategy: str
    node_count: int
    winning_node: str
    latency_ms: float
    quality_score: float
    per_node_metrics: list[dict[str, Any]]
    timestamp: float = field(default_factory=time.time)
    phi_score: float = 0.0  # Composite HIHO alignment (0-1)


# ---------------------------------------------------------------------------
# Adaptive Router
# ---------------------------------------------------------------------------


class AdaptiveRouter:
    """Ranks available nodes by their live composite score.

    Called before each batch dispatch to produce an ordered candidate list.
    Thread-safe: all state is in asyncio-compatible data structures.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, NodeMetrics] = {}
        self._lock = asyncio.Lock()

    def register(self, node_id: str, model: str, kind: NodeKind) -> NodeMetrics:
        if node_id not in self._metrics:
            self._metrics[node_id] = NodeMetrics(node_id=node_id, model=model, kind=kind)
        return self._metrics[node_id]

    async def update(self, node_id: str, latency_ms: float, quality: float) -> None:
        async with self._lock:
            if node_id in self._metrics:
                self._metrics[node_id].record(latency_ms, quality)

    async def record_error(self, node_id: str) -> None:
        async with self._lock:
            if node_id in self._metrics:
                self._metrics[node_id].record_error()

    def ranked_nodes(self, kind_filter: NodeKind | None = None) -> list[NodeMetrics]:
        """Return nodes sorted best-first by composite score."""
        nodes = list(self._metrics.values())
        if kind_filter is not None:
            nodes = [n for n in nodes if n.kind == kind_filter]
        # Exclude nodes with sustained high error rates (>70% recent errors)
        healthy = [n for n in nodes if n.avg_quality > 0.05 or n.total_calls < 3]
        return sorted(healthy, key=lambda n: n.score, reverse=True)

    def all_metrics(self) -> list[dict[str, Any]]:
        return [
            {
                "node_id": m.node_id,
                "model": m.model,
                "kind": m.kind,
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "avg_quality": round(m.avg_quality, 3),
                "score": round(m.score, 4),
                "total_calls": m.total_calls,
                "error_count": m.error_count,
            }
            for m in sorted(self._metrics.values(), key=lambda n: n.score, reverse=True)
        ]


# ---------------------------------------------------------------------------
# Node dispatch helpers
# ---------------------------------------------------------------------------


async def _call_lemonade(
    port: int,
    model_id: str,
    prompt: str,
    *,
    max_tokens: int = 512,
    timeout: float = 45.0,
) -> tuple[str, float]:
    """Dispatch to a Lemonade/llama-server OpenAI-compat endpoint.

    Returns (completion_text, latency_ms).  Raises on failure.
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
    # Reasoning models may put CoT in reasoning_content
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
    """Dispatch to local Ollama /api/generate endpoint.

    Returns (completion_text, latency_ms).  Raises on failure.
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
        resp = await client.post(f"{_OLLAMA_BASE}/api/generate", json=payload)
        resp.raise_for_status()
    latency_ms = (time.perf_counter() - t0) * 1000
    data = resp.json()
    return data.get("response", ""), latency_ms


def _quality_score(
    text: str,
    prompt: str,
    min_chars: int = 20,
    *,
    text_trajectory: list[str] | None = None,
) -> float:
    """Quality scorer — no additional model call, <1ms.

    When a ``text_trajectory`` (multi-step reasoning trace) is provided,
    uses **Chain-of-Embedding (CoE) geometric scoring** from arXiv:2410.13640:
    measures M (magnitude change) and A (angle change) between adjacent
    latent state approximations — more principled than text heuristics.

    Falls back to the compound heuristic for single-step responses:
    - Empty → 0.0
    - Length saturation relative to prompt complexity
    - Word diversity ratio (penalises repetition)
    - Code block bonus

    Returns a [0.0, 1.0] score suitable for AdaptiveRouter updates.
    """
    if not text or len(text.strip()) < 3:
        return 0.0

    stripped = text.strip()

    # CoE path: use geometric latent trajectory scoring when available
    if text_trajectory and len(text_trajectory) >= 2:
        try:
            from cohezion.flume.coe_evaluator import coe_quality_from_texts

            coe_score = coe_quality_from_texts(text_trajectory)
            logger.debug(
                "_quality_score: CoE geometric score=%.4f (n_steps=%d)",
                coe_score,
                len(text_trajectory),
            )
            return coe_score
        except Exception as exc:
            logger.debug("CoE scoring failed (%s) — falling back to heuristic", exc)

    # Heuristic fallback for single-step responses
    target = max(min_chars, len(prompt) * 0.2)
    length_score = min(1.0, len(stripped) / target)

    # Diversity: unique words / total words (penalises repetition)
    words = stripped.lower().split()
    diversity = len(set(words)) / max(len(words), 1)

    # Code block bonus
    code_bonus = 0.1 if "```" in stripped and "code" in prompt.lower() else 0.0

    return min(1.0, (0.5 * length_score + 0.4 * diversity + code_bonus))


# ---------------------------------------------------------------------------
# Experience Collector (feeds the evolution bridge)
# ---------------------------------------------------------------------------


class ExperienceCollector:
    """Accumulates SwarmExperienceTraces and periodically flushes them to the
    EvolutionTrainingBridge for online learning.

    The HIHO coherence rule applies: phi_score targets 0.5 for max stability.
    """

    def __init__(self, flush_every: int = 10) -> None:
        self._buffer: list[SwarmExperienceTrace] = []
        self._flush_every = flush_every
        self._trace_dir = Path("execution_traces/swarm")
        self._trace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def record(self, trace: SwarmExperienceTrace) -> None:
        """Buffer a trace and flush if threshold is reached."""
        async with self._lock:
            self._buffer.append(trace)
            self._persist_trace(trace)
            if len(self._buffer) >= self._flush_every:
                await self._flush()

    def _persist_trace(self, trace: SwarmExperienceTrace) -> None:
        """Write trace as JSON for Meta-Harness auditing."""
        path = self._trace_dir / f"{int(trace.timestamp)}_{trace.trace_id[:8]}.json"
        try:
            path.write_text(
                json.dumps(
                    {
                        "trace_id": trace.trace_id,
                        "task_id": trace.task_id,
                        "prompt_digest": trace.prompt_digest,
                        "strategy": trace.strategy,
                        "node_count": trace.node_count,
                        "winning_node": trace.winning_node,
                        "latency_ms": trace.latency_ms,
                        "quality_score": trace.quality_score,
                        "phi_score": trace.phi_score,
                        "per_node_metrics": trace.per_node_metrics,
                        "timestamp": trace.timestamp,
                    },
                    indent=2,
                )
            )
        except Exception as exc:
            logger.debug("Trace persist failed: %s", exc)

    async def _flush(self) -> None:
        """Push buffered traces into the EvolutionTrainingBridge (if available)."""
        traces = list(self._buffer)
        self._buffer.clear()

        try:
            from cohezion.compound.evolution_training_bridge import (
                EvolutionTrainingBridge,
                EvolutionTrainingConfig,
            )
            from cohezion.compound.group_evolution import (
                ExperienceTrace,
                TaskSuccessVector,
            )

            cfg = EvolutionTrainingConfig()
            bridge = EvolutionTrainingBridge(cfg)

            # Map swarm traces to ExperienceTrace objects the bridge understands
            exp_traces = []
            for t in traces:
                sv = TaskSuccessVector(successes=[t.quality_score, t.phi_score])
                exp_traces.append(
                    ExperienceTrace(
                        agent_id=t.winning_node,
                        task_id=t.task_id,
                        quality_score=t.quality_score,
                        success_vector=sv,
                        metadata={
                            "swarm_trace_id": t.trace_id,
                            "node_count": t.node_count,
                            "latency_ms": t.latency_ms,
                            "strategy": t.strategy,
                        },
                    )
                )

            if exp_traces:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: bridge.process_experience_traces(exp_traces)
                )
                logger.info("Swarm: flushed %d traces to EvolutionBridge", len(exp_traces))
        except Exception as exc:
            logger.debug("Evolution bridge flush skipped: %s", exc)


# ---------------------------------------------------------------------------
# Per-node circuit breaker
# ---------------------------------------------------------------------------


class NodeCircuitBreaker:
    """Simple per-node circuit breaker for swarm dispatch.

    Tracks consecutive failures per node.  After ``failure_threshold``
    consecutive failures the circuit *opens* and the node is skipped for
    ``recovery_timeout`` seconds (half-open window).  A single success
    resets the counter.

    Parameters
    ----------
    failure_threshold : int
        Number of consecutive failures before opening the circuit.
    recovery_timeout : float
        Seconds to wait before allowing a half-open probe.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        # node_id -> consecutive failure count
        self._failures: dict[str, int] = {}
        # node_id -> timestamp when the circuit opened
        self._opened_at: dict[str, float] = {}

    def is_open(self, node_id: str) -> bool:
        """Return True if the circuit is open (node should be skipped).

        If the recovery timeout has elapsed the circuit moves to *half-open*
        (returns False) so the caller can attempt a single probe.
        """
        failures = self._failures.get(node_id, 0)
        if failures < self._failure_threshold:
            return False
        opened = self._opened_at.get(node_id, 0.0)
        if time.time() - opened >= self._recovery_timeout:
            # Half-open: allow one probe attempt
            return False
        return True

    def record_success(self, node_id: str) -> None:
        """Reset the failure counter on a successful call."""
        self._failures.pop(node_id, None)
        self._opened_at.pop(node_id, None)

    def record_failure(self, node_id: str) -> None:
        """Increment consecutive failure count; open circuit if threshold met."""
        count = self._failures.get(node_id, 0) + 1
        self._failures[node_id] = count
        if count >= self._failure_threshold:
            self._opened_at.setdefault(node_id, time.time())


# ---------------------------------------------------------------------------
# Main SiliconSwarm
# ---------------------------------------------------------------------------


class SiliconSwarm:
    """Unified silicon swarm — NPU + iGPU + CPU nodes as one adaptive mesh.

    Usage::

        swarm = SiliconSwarm()
        await swarm.start()

        result = await swarm.dispatch("Explain lattice QCD in 3 sentences")
        print(result.text, result.winning_node)

        # Fan out sub-tasks and aggregate
        results = await swarm.dispatch_parallel(["task A", "task B", "task C"])

        await swarm.stop()
    """

    def __init__(
        self,
        *,
        cpu_models: list[str] | None = None,
        n_cpu_workers: int = N_CPU_WORKERS,
        strategy: AggregationStrategy = AggregationStrategy.FIRST_PASS,
        experience_flush_every: int = 10,
    ) -> None:
        self._cpu_models = cpu_models or CPU_SMALL_MODELS
        self._n_cpu_workers = n_cpu_workers
        self._default_strategy = strategy
        self._router = AdaptiveRouter()
        self._collector = ExperienceCollector(flush_every=experience_flush_every)
        self._cpu_sem = asyncio.Semaphore(n_cpu_workers)
        self._circuit_breaker = NodeCircuitBreaker()
        self._running = False

        # Register all nodes with the adaptive router
        self._register_nodes()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _register_nodes(self) -> None:
        """Register all silicon lanes + CPU small-model workers."""
        # Lemonade lanes (Gemma-4 symphony)
        for lane_name, _port in _LANE_PORTS.items():
            kind = (
                NodeKind.NPU
                if lane_name == "npu"
                else (NodeKind.IGPU if "igpu" in lane_name else NodeKind.CPU)
            )
            model_id = {
                "npu": "Gemma-4-E2B-it-GGUF",
                "igpu_rocwmma": "Gemma-4-E4B-it-GGUF",
                "igpu_unified": "Gemma-4-26B-A4B-it-GGUF",
                "cpu": "Gemma-4-31B-it-GGUF",
            }[lane_name]
            self._router.register(f"lemonade:{lane_name}", model_id, kind)

        # Ollama CPU small models
        for model in self._cpu_models:
            node_id = f"ollama:{model}"
            self._router.register(node_id, model, NodeKind.OLLAMA)

    async def start(self) -> None:
        """Probe all nodes and drop unreachable ones from initial ranking."""
        self._running = True
        probe_tasks = []

        # Lemonade probes
        for lane_name, port in _LANE_PORTS.items():
            probe_tasks.append(self._probe_lemonade(lane_name, port))

        # Ollama probes
        probe_tasks.append(self._probe_ollama_models())

        await asyncio.gather(*probe_tasks, return_exceptions=True)
        logger.info("SiliconSwarm: started — probed %d node groups", len(probe_tasks))

    async def stop(self) -> None:
        self._running = False
        # Final flush
        await self._collector._flush()

    async def _probe_lemonade(self, lane: str, port: int) -> None:
        """Quick liveness check via /v1/models."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://localhost:{port}/v1/models")
                if resp.status_code == 200:
                    logger.debug("Lemonade lane %s (%d) is UP", lane, port)
                    return
        except Exception:
            pass
        logger.debug("Lemonade lane %s (%d) is DOWN — will skip", lane, port)
        # Mark as degraded by pre-loading bad metrics
        node_id = f"lemonade:{lane}"
        await self._router.record_error(node_id)
        await self._router.record_error(node_id)
        await self._router.record_error(node_id)

    async def _probe_ollama_models(self) -> None:
        """Check which Ollama models are available."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{_OLLAMA_BASE}/api/tags")
                if resp.status_code != 200:
                    return
            data = resp.json()
            available = {m["name"] for m in data.get("models", [])}
            for model in self._cpu_models:
                base = model.split(":")[0]
                hit = any(base in a for a in available)
                if hit:
                    logger.debug("Ollama model %s is available", model)
                else:
                    logger.debug("Ollama model %s NOT found — marking degraded", model)
                    node_id = f"ollama:{model}"
                    for _ in range(3):
                        await self._router.record_error(node_id)
        except Exception as exc:
            logger.debug("Ollama probe failed: %s", exc)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        strategy: AggregationStrategy | None = None,
        prefer_kind: NodeKind | None = None,
        timeout: float = 60.0,
    ) -> SwarmResult:
        """Dispatch a single prompt to the best available node.

        Adaptive routing: the node with the highest composite score gets first
        shot; if it fails or returns low quality, we escalate to the next node.
        """
        agg = strategy or self._default_strategy
        task_id = str(uuid4())[:8]
        t_start = time.perf_counter()

        # Prompt digest for trace (no PII stored)
        import hashlib

        prompt_digest = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        ranked = self._router.ranked_nodes(kind_filter=prefer_kind)
        if not ranked:
            ranked = self._router.ranked_nodes()  # fallback: no filter

        node_results: list[dict[str, Any]] = []
        best_text = ""
        best_quality = 0.0
        winning_node = "none"

        for node in ranked:
            text, quality, latency_ms = await self._call_node(
                node, prompt, max_tokens=max_tokens, timeout=timeout
            )
            node_results.append(
                {
                    "node_id": node.node_id,
                    "model": node.model,
                    "text_len": len(text),
                    "quality": round(quality, 3),
                    "latency_ms": round(latency_ms, 1),
                }
            )

            if quality > best_quality:
                best_quality = quality
                best_text = text
                winning_node = node.node_id

            if quality >= _MIN_QUALITY_ACCEPT:
                break  # Good enough — stop escalating

        latency_ms = (time.perf_counter() - t_start) * 1000

        # HIHO phi score: distance from 0.5 equilibrium, mapped to [0,1]
        phi = 1.0 - abs(best_quality - 0.5) * 2

        trace = SwarmExperienceTrace(
            trace_id=str(uuid4()),
            task_id=task_id,
            prompt_digest=prompt_digest,
            strategy=str(agg),
            node_count=len(node_results),
            winning_node=winning_node,
            latency_ms=latency_ms,
            quality_score=best_quality,
            phi_score=phi,
            per_node_metrics=node_results,
        )
        await self._collector.record(trace)

        return SwarmResult(
            task_id=task_id,
            prompt=prompt,
            text=best_text,
            strategy=agg,
            node_results=node_results,
            latency_ms=latency_ms,
            tokens_used=len(prompt.split()) + len(best_text.split()),
            winning_node=winning_node,
            quality_score=best_quality,
        )

    async def dispatch_parallel(
        self,
        prompts: list[str],
        *,
        max_tokens: int = 512,
        timeout: float = 90.0,
    ) -> list[SwarmResult]:
        """Fan out multiple prompts across the swarm simultaneously.

        Each prompt is routed independently.  CPU workers are bounded by
        the semaphore to avoid over-committing the Zen5 cores.
        """

        async def _bounded(p: str) -> SwarmResult:
            async with self._cpu_sem:
                return await self.dispatch(p, max_tokens=max_tokens, timeout=timeout)

        return list(await asyncio.gather(*[_bounded(p) for p in prompts]))

    async def _call_node(
        self,
        node: NodeMetrics,
        prompt: str,
        *,
        max_tokens: int,
        timeout: float,
    ) -> tuple[str, float, float]:
        """Dispatch to a specific node.

        Returns (text, quality_score, latency_ms).  The per-node circuit
        breaker skips nodes that have hit ``failure_threshold`` consecutive
        failures until the ``recovery_timeout`` elapses.
        """
        # Circuit breaker: skip nodes with too many consecutive failures
        if self._circuit_breaker.is_open(node.node_id):
            logger.debug("Swarm node %s: circuit OPEN — skipping", node.node_id)
            return "", 0.0, 9999.0

        try:
            if node.kind == NodeKind.OLLAMA:
                text, latency_ms = await _call_ollama(
                    node.model, prompt, max_tokens=max_tokens, timeout=timeout
                )
            else:
                # Lemonade — map node_id to port
                lane = node.node_id.split(":", 1)[1]
                port = _LANE_PORTS.get(lane, 13305)
                text, latency_ms = await _call_lemonade(
                    port, node.model, prompt, max_tokens=max_tokens, timeout=timeout
                )

            quality = _quality_score(text, prompt)
            await self._router.update(node.node_id, latency_ms, quality)
            self._circuit_breaker.record_success(node.node_id)
            logger.debug(
                "Swarm node %s: %.0fms, q=%.2f, len=%d",
                node.node_id,
                latency_ms,
                quality,
                len(text),
            )
            return text, quality, latency_ms

        except Exception as exc:
            logger.warning("Swarm node %s failed: %s", node.node_id, exc)
            await self._router.record_error(node.node_id)
            self._circuit_breaker.record_failure(node.node_id)
            return "", 0.0, 9999.0

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def node_report(self) -> list[dict[str, Any]]:
        """Return live metrics for all registered nodes."""
        return self._router.all_metrics()

    def swarm_summary(self) -> dict[str, Any]:
        """High-level swarm health summary."""
        metrics = self._router.all_metrics()
        healthy = [m for m in metrics if m["avg_quality"] > 0.2]
        return {
            "total_nodes": len(metrics),
            "healthy_nodes": len(healthy),
            "top_node": metrics[0]["node_id"] if metrics else "none",
            "avg_quality": (
                round(sum(m["avg_quality"] for m in healthy) / max(len(healthy), 1), 3)
            ),
            "avg_latency_ms": (
                round(sum(m["avg_latency_ms"] for m in healthy) / max(len(healthy), 1), 1)
            ),
        }


# ---------------------------------------------------------------------------
# Singleton accessor (mirrors local_inference.py pattern)
# ---------------------------------------------------------------------------

_swarm: SiliconSwarm | None = None
_swarm_lock = asyncio.Lock()


async def get_swarm(
    *,
    cpu_models: list[str] | None = None,
    n_cpu_workers: int = N_CPU_WORKERS,
) -> SiliconSwarm:
    """Return the process-level SiliconSwarm singleton (lazy-init, thread-safe)."""
    global _swarm
    if _swarm is None:
        async with _swarm_lock:
            if _swarm is None:
                _swarm = SiliconSwarm(cpu_models=cpu_models, n_cpu_workers=n_cpu_workers)
                await _swarm.start()
    return _swarm


async def swarm_dispatch(prompt: str, **kwargs: Any) -> SwarmResult:
    """Convenience one-liner — dispatch a single prompt via the global swarm."""
    swarm = await get_swarm()
    return await swarm.dispatch(prompt, **kwargs)


async def swarm_parallel(prompts: list[str], **kwargs: Any) -> list[SwarmResult]:
    """Convenience one-liner — fan out prompts via the global swarm."""
    swarm = await get_swarm()
    return await swarm.dispatch_parallel(prompts, **kwargs)


# ---------------------------------------------------------------------------
# Latent-space enhanced dispatch (Awesome-Latent-Space integration)
# ---------------------------------------------------------------------------


def _complexity_heuristic(prompt: str) -> float:
    """Estimate task complexity as a [0, 1] float.

    Used to decide whether to activate LatentEngine deliberation.
    Heuristics (cheap, no model call):
    - Prompt length (longer = likely more complex)
    - Presence of reasoning keywords (prove, derive, explain why, ...)
    - Question mark density (multi-step questions)
    - Code block markers (signals technical depth)
    """
    length_score = min(1.0, len(prompt) / 1000.0)  # cap at 1000 chars

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
        "complexity",
    }
    set(prompt.lower().split())
    keyword_score = min(1.0, sum(1 for k in reasoning_keywords if k in prompt.lower()) / 4.0)

    # Questions score: ratio of '?' to length
    question_score = min(1.0, prompt.count("?") * 0.2)

    # Code marker
    code_score = 0.3 if "```" in prompt or "def " in prompt or "class " in prompt else 0.0

    return min(
        1.0, 0.3 * length_score + 0.4 * keyword_score + 0.1 * question_score + 0.2 * code_score
    )


async def swarm_deliberate(
    prompt: str,
    *,
    complexity_threshold: float = 0.4,
    use_soft_cot: bool = True,
    use_coconut: bool = True,
    use_recurrent: bool = False,
    small_model: str = "qwen3:1.7b",
    medium_model: str = "phi4-mini",
    max_tokens: int = 256,
) -> dict[str, Any]:
    """Latent-space deliberation dispatch (Awesome-Latent-Space techniques).

    For simple tasks: falls through to ``swarm_dispatch`` (fast path).
    For complex tasks (complexity_heuristic >= threshold): activates the full
    LatentEngine pipeline (SoftCoT → COCONUT BFS → CoE self-eval → optional
    Recurrent Depth refinement).

    Returns a dict with:
        ``text``         : final answer text
        ``source``       : "swarm" | "latent_engine"
        ``complexity``   : computed complexity score
        ``confidence``   : CoE confidence (latent engine) or quality_score (swarm)
        ``coe_assessment``: (latent engine only) full CoE dict
        ``latency_ms``   : total wall-clock latency

    Usage::

        from cohezion.inference.distributed_swarm import swarm_deliberate

        result = await swarm_deliberate("Prove that √2 is irrational.")
        print(result["text"])
        print(f"Confidence: {result['confidence']:.2f} (source: {result['source']})")
    """
    t_start = time.perf_counter()
    complexity = _complexity_heuristic(prompt)

    if complexity < complexity_threshold:
        # Fast path: regular swarm dispatch
        swarm_result = await swarm_dispatch(prompt)
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {
            "text": swarm_result.text,
            "source": "swarm",
            "complexity": round(complexity, 3),
            "confidence": round(swarm_result.quality_score, 3),
            "coe_assessment": None,
            "latency_ms": round(latency_ms, 1),
            "winning_node": swarm_result.winning_node,
        }

    # Complex task: activate LatentEngine
    logger.info(
        "swarm_deliberate: complexity=%.2f >= %.2f — activating LatentEngine",
        complexity,
        complexity_threshold,
    )
    try:
        from cohezion.flume.latent_engine import LatentEngine

        engine = LatentEngine(
            small_model=small_model,
            medium_model=medium_model,
        )
        result = await engine.reason(
            prompt,
            use_soft_cot=use_soft_cot,
            use_coconut=use_coconut,
            use_recurrent=use_recurrent,
            max_tokens=max_tokens,
        )
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {
            "text": result.final_answer,
            "source": "latent_engine",
            "complexity": round(complexity, 3),
            "confidence": round(result.confidence, 3),
            "coe_assessment": result.coe_assessment,
            "latency_ms": round(latency_ms, 1),
            "coconut_bfs_explored": result.coconut_bfs_explored,
            "soft_prefix_used": result.soft_prefix_used,
            "state_depth": len(result.state_trajectory),
        }

    except ImportError:
        logger.warning(
            "LatentEngine unavailable (httpx/numpy missing?) — falling back to swarm dispatch"
        )
        swarm_result = await swarm_dispatch(prompt)
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {
            "text": swarm_result.text,
            "source": "swarm_fallback",
            "complexity": round(complexity, 3),
            "confidence": round(swarm_result.quality_score, 3),
            "coe_assessment": None,
            "latency_ms": round(latency_ms, 1),
        }
