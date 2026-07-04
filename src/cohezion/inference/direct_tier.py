"""Direct HTTP lemonade tier — bypasses GAIA LemonadeManager singleton.

The GAIA LemonadeManager uses a class-level singleton that assumes one lemonade
port per process. For multi-port TieredOrchestrator (NPU/iGPU/CPU each on a
different port), each tier needs its own connection. This module provides
DirectLemonadeTier: a drop-in replacement that talks to lemonade via httpx
without touching LemonadeManager.

Quarter-on-a-String Protocol (user directive, recurring):
  Claude (cloud, expensive) = orchestration and planning only.
  Local Lemonade = execution. Always. Cost = $0.
  Dispatcher: quarter_on_a_string_tier(complexity)
  - "routine"       → llama3.2-1b-FLM  (NPU, 42 TPS, classification/routing)
  - "synthesis"     → Bonsai-8B-gguf   (iGPU-class, structured output)
  - "orchestration" → Qwen3.6-35B-A3B-NoThinking (35B, reasoning)
  - "review"        → Qwen3.6-35B-A3B-NoThinking (same tier, review context)

All routes go through the OmniRouter at :13305 — dedicated per-port servers
(13306/13307/13309) are optional and often offline.

Validated in exp_OOOO3 and exp_PPPP3 (2026-05-30, autoresearch round 13).
Restored to main 2026-06-25 from session 18b9f3af worktree.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed as _futs_done
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_OMNI_PORT = 13305

# Strip <think>...</think> blocks emitted by reasoning models (e.g. deepseek-r1).
# Applied at every response return point so callers never see raw reasoning traces.
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def _strip_think(text: str) -> str:
    """Remove <think>...</think> blocks from model output. No-op when absent."""
    if "<think>" not in text:
        return text
    stripped = _THINK_RE.sub("", text).strip()
    return stripped if stripped else text

# Quarter-on-a-string model routing by complexity
_QUARTER_MODELS: dict[str, str] = {
    "routine": "llama3.2-1b-FLM",           # NPU, 42 TPS, $0
    "synthesis": "Bonsai-8B-gguf",           # iGPU-class, balanced
    "orchestration": "Qwen3.6-35B-A3B-NoThinking",  # 35B, full reasoning
    "review": "Qwen3.6-35B-A3B-NoThinking",          # same tier
}

_QUARTER_MAX_TOKENS: dict[str, int] = {
    "routine": 256,
    "synthesis": 512,
    "orchestration": 1024,
    "review": 1024,
}

_NO_THINK_SUFFIX = ("-NoThinking", "-GGUF", "Bonsai")


def _needs_no_think(model_id: str) -> bool:
    return any(model_id.endswith(s) or s in model_id for s in _NO_THINK_SUFFIX)


class DirectLemonadeTier:
    """Thin sync/async wrapper for a single lemonade port.

    Parameters
    ----------
    port : int
        Lemonade port to target (13305 = OmniRouter, preferred).
    model_id : str
        Model ID to request.
    max_tokens : int
        Maximum tokens to generate.
    temperature : float
        Sampling temperature.
    """

    def __init__(
        self,
        port: int = _OMNI_PORT,
        model_id: str = "llama3.2-1b-FLM",
        *,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system_message: str | None = None,
    ) -> None:
        self.port = port
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_message = system_message
        self.label = f"direct:{model_id}"
        self._base_url = f"http://localhost:{port}/v1/chat/completions"

    def _build_messages(self, prompt: str) -> list[dict[str, str]]:
        msgs: list[dict[str, str]] = []
        if self.system_message:
            msgs.append({"role": "system", "content": self.system_message})
        elif _needs_no_think(self.model_id):
            msgs.append({"role": "system", "content": "/no_think"})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def call(self, prompt: str) -> dict[str, Any]:
        """Synchronous call via urllib (stdlib-only, no httpx dependency)."""
        payload = json.dumps({
            "model": self.model_id,
            "messages": self._build_messages(prompt),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }).encode()

        start = time.perf_counter()
        try:
            req = urllib.request.Request(
                self._base_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            text = _strip_think(data["choices"][0]["message"]["content"].strip())
            error = None
        except urllib.error.URLError as exc:
            text = ""
            error = str(exc)
            logger.debug("DirectLemonadeTier %s: %s", self.model_id, error)
        except Exception as exc:
            text = ""
            error = f"{type(exc).__name__}: {exc}"
            logger.debug("DirectLemonadeTier %s: %s", self.model_id, error)

        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "text": text,
            "model": self.model_id,
            "port": self.port,
            "latency_ms": latency_ms,
            "error": error,
            "cost_usd": 0.0,
        }

    async def run(self, prompt: str, **_: object) -> Any:
        """Async-compatible shim — wraps sync call in executor for event loops."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.call, prompt)


# ── Convenience builders ───────────────────────────────────────────────────────

def build_direct_npu_tier(
    port: int = _OMNI_PORT,
    model_id: str = "llama3.2-1b-FLM",
) -> DirectLemonadeTier:
    """NPU-class tier — fastest, classification/routing tasks."""
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=256)


def build_direct_igpu_tier(
    port: int = _OMNI_PORT,
    model_id: str = "Bonsai-8B-gguf",
) -> DirectLemonadeTier:
    """iGPU-class tier — balanced, structured output tasks."""
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=512)


def build_direct_cpu_tier(
    port: int = _OMNI_PORT,
    model_id: str = "Qwen3.6-35B-A3B-NoThinking",
) -> DirectLemonadeTier:
    """CPU-class tier — strongest local reasoning."""
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=1024)


# ── Fleet dataclasses ──────────────────────────────────────────────────────────

@dataclass
class FleetNodeResult:
    """Result from a single compute node in a parallel fleet dispatch."""

    model_id: str
    node: str       # "npu" | "igpu" | "cpu"
    text: str
    latency_ms: float
    error: str | None = None


@dataclass
class FleetResult:
    """Aggregated result from all nodes fired simultaneously."""

    nodes: list[FleetNodeResult] = field(default_factory=list)
    best_text: str = ""
    best_node: str = ""
    wall_ms: float = 0.0   # max latency — all nodes ran in parallel
    cost_usd: float = 0.0  # always free (local silicon)

    @property
    def succeeded(self) -> bool:
        return bool(self.best_text)


# ── Parallel fleet orchestrator ────────────────────────────────────────────────

class ParallelFleetOrchestrator:
    """Fan-out: same prompt → NPU + iGPU + CPU simultaneously → FleetResult.

    All three nodes are dispatched at once via asyncio.gather().
    Unlike TieredOrchestrator (sequential cascade), this leverages all compute
    units in parallel — wall-clock = slowest single node, not sum of all.

    Node mapping (via OmniRouter :13305):
      npu  → llama3.2-1b-FLM           42 TPS, fast classification
      igpu → Bonsai-8B-gguf            iGPU-class, balanced generation
      cpu  → Qwen3.6-35B-A3B-NoThinking  35B, full reasoning
    """

    def __init__(self, *, omni_port: int = _OMNI_PORT) -> None:
        self._nodes: dict[str, DirectLemonadeTier] = {
            "npu": DirectLemonadeTier(
                port=omni_port, model_id="llama3.2-1b-FLM", max_tokens=256
            ),
            "igpu": DirectLemonadeTier(
                port=omni_port, model_id="Bonsai-8B-gguf", max_tokens=512
            ),
            "cpu": DirectLemonadeTier(
                port=omni_port, model_id="Qwen3.6-35B-A3B-NoThinking", max_tokens=1024
            ),
        }

    async def generate(self, prompt: str) -> FleetResult:
        """Fire all three nodes simultaneously and return aggregated FleetResult."""
        raw_results = await asyncio.gather(
            *(tier.run(prompt) for tier in self._nodes.values()),
            return_exceptions=True,
        )
        node_results: list[FleetNodeResult] = []
        for (node, tier), raw in zip(self._nodes.items(), raw_results):
            if isinstance(raw, Exception):
                node_results.append(
                    FleetNodeResult(
                        model_id=tier.model_id, node=node,
                        text="", latency_ms=0.0, error=str(raw),
                    )
                )
            else:
                d: dict[str, Any] = raw if isinstance(raw, dict) else {}
                node_results.append(
                    FleetNodeResult(
                        model_id=tier.model_id, node=node,
                        text=d.get("text", ""),
                        latency_ms=d.get("latency_ms", 0.0),
                        error=d.get("error"),
                    )
                )
        non_empty = [r for r in node_results if r.text]
        best = max(non_empty, key=lambda r: len(r.text)) if non_empty else node_results[0]
        wall_ms = max((r.latency_ms for r in node_results), default=0.0)
        return FleetResult(
            nodes=node_results,
            best_text=best.text,
            best_node=best.node,
            wall_ms=wall_ms,
        )

    def generate_sync(self, prompt: str) -> FleetResult:
        """Sync wrapper — safe for non-async callers without a running event loop."""
        return asyncio.run(self.generate(prompt))

    async def run_batch(self, prompts: list[str]) -> list[FleetResult]:
        """Fan-out batch: every prompt hits all three nodes in parallel."""
        return list(await asyncio.gather(*[self.generate(p) for p in prompts]))


# ── Multi-node dispatch (sync, ThreadPoolExecutor) ────────────────────────────

def multi_node_batch(
    tasks: list[tuple[str, str]],
    *,
    port: int = _OMNI_PORT,
) -> list[dict[str, Any]]:
    """Route each (prompt, complexity) to its natural tier; fire all simultaneously.

    Uses ThreadPoolExecutor so it works from sync code (compound_daemon) without
    needing a running event loop. Each task hits a different local model — the
    OmniRouter dispatches to the right silicon backend:

      routine       → llama3.2-1b-FLM  (NPU, XDNA2)
      synthesis     → Bonsai-8B-gguf   (iGPU-class)
      orchestration → Qwen3.6-35B      (CPU AVX-512)

    Example::

        results = multi_node_batch([
            ("classify this: ...",    "routine"),
            ("synthesize report",     "synthesis"),
            ("reason about tradeoffs","orchestration"),
        ])
        # All three fire at the same time; wall-clock = slowest single call.

    Returns results in the same order as the input tasks.
    """
    if not tasks:
        return []

    tiers = [quarter_on_a_string_tier(complexity, port=port) for _, complexity in tasks]
    results: list[dict[str, Any]] = [{}] * len(tasks)

    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as pool:
        futures = {
            pool.submit(tier.call, prompt): i
            for i, ((prompt, _), tier) in enumerate(zip(tasks, tiers))
        }
        for fut in _futs_done(futures):
            idx = futures[fut]
            try:
                results[idx] = fut.result()
            except Exception as exc:
                results[idx] = {"text": "", "error": str(exc), "cost_usd": 0.0}

    return results


def quarter_on_a_string_tier(
    task_complexity: str = "routine",
    *,
    port: int = _OMNI_PORT,
    system_message: str | None = None,
) -> DirectLemonadeTier:
    """Quarter-on-a-String protocol dispatcher.

    Route every inference call to the cheapest local tier that can handle the
    stated complexity. Cloud inference is NEVER called from this path.

    Complexity levels
    -----------------
    routine       → llama3.2-1b-FLM  (NPU, 42 TPS) — classify, route, short answers
    synthesis     → Bonsai-8B-gguf   (iGPU-class)  — code gen, structured output
    orchestration → Qwen3.6-35B-A3B-NoThinking (35B) — multi-step reasoning
    review        → Qwen3.6-35B-A3B-NoThinking (35B) — adversarial review, audit

    Examples
    --------
    >>> tier = quarter_on_a_string_tier("routine")
    >>> result = tier.call("Classify this task: write a haiku")
    >>> print(result["text"], result["cost_usd"])  # some text, 0.0
    """
    model_id = _QUARTER_MODELS.get(task_complexity, _QUARTER_MODELS["routine"])
    max_tokens = _QUARTER_MAX_TOKENS.get(task_complexity, 512)
    logger.debug(
        "Quarter-on-a-String: complexity=%s → model=%s port=%d",
        task_complexity, model_id, port,
    )
    return DirectLemonadeTier(
        port=port,
        model_id=model_id,
        max_tokens=max_tokens,
        system_message=system_message,
    )
