"""GAIA SDK adapter + AMD-optimization-aware tier selection.

Two surfaces:

1. **GaiaAgentTier** — wraps an ``amd-gaia`` Agent (or MCPAgent) so it can
   serve as a tier inside a ``TieredOrchestrator``. GAIA's Agent natively
   talks to Lemonade → XDNA 2 NPU, so using GAIA as a tier target picks the
   AMD-optimized path automatically.

2. **amd_optimized_hierarchy()** — factory that prefers AMD-backed tiers
   (FLM on NPU, ROCWMMA on iGPU, AVX-VNNI on CPU) ahead of generic paths.

Reference: amd-gaia 0.17.2 installed (2026-04-18) — see
``/home/mike-anderson/dev/cohezion/.venv/lib/python3.11/site-packages/gaia/``.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from cohezion.inference.orchestrator import (
    OrchestrationResult,
    QualityGate,
    TieredOrchestrator,
)
from cohezion.inference.registry import Lane, get_registry


logger = logging.getLogger(__name__)


# Lane-family ranking: lower number = more AMD-silicon-native = preferred.
# This is the "pick paths that unlock AMD optimizations" directive, encoded.
_AMD_PATH_RANK: dict[Lane, int] = {
    Lane.NPU: 0,  # XDNA 2 via FLM — most AMD-native
    Lane.IGPU_ROCWMMA: 1,  # RDNA 3.5 ROCWMMA
    Lane.IGPU_UNIFIED: 1,  # RDNA 3.5 with 120 GB GTT
    Lane.CPU: 2,  # AVX-VNNI via lemonade
    Lane.CLOUD_OLLAMA: 3,  # Generic (non-AMD) cloud
    Lane.CLOUD_GEMINI: 4,
    Lane.CLOUD_CLAUDE: 5,
}


@dataclass
class GaiaAgentTier:
    """Wrap a ``gaia.Agent`` / ``gaia.MCPAgent`` instance as a tier target.

    Usage::

        from gaia import Agent
        from cohezion.inference.orchestrator import TieredOrchestrator, QualityGate
        from cohezion.inference.gaia_adapter import GaiaAgentTier

        gaia_agent = Agent(model_id="Gemma-4-E2B-it-GGUF", silent_mode=True)
        orch = TieredOrchestrator(tiers=[
            (GaiaAgentTier(gaia_agent, label="gaia-e2b"), QualityGate.TRUST),
        ])
    """

    agent: object  # gaia.Agent — kept as `object` to avoid import-time dep
    label: str = "gaia-agent"

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        """Invoke the GAIA Agent, wrap its response in OrchestrationResult."""
        start = time.perf_counter()
        ttft: float | None = None
        text = ""
        cost = 0.0
        error: str | None = None

        # GAIA's Agent.prompt() is the public sync surface. Some versions
        # expose .run() — we probe for either. Keep the adapter resilient.
        run_fn = (
            getattr(self.agent, "prompt", None)
            or getattr(self.agent, "run", None)
            or getattr(self.agent, "chat", None)
        )
        if run_fn is None:
            error = "GaiaAgentTier: agent has no prompt/run/chat method"
        else:
            try:
                # GAIA is sync-first; run in default executor to avoid blocking loop
                import asyncio

                loop = asyncio.get_running_loop()
                out = await loop.run_in_executor(None, run_fn, prompt)
                text = out if isinstance(out, str) else str(out)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        latency_ms = (time.perf_counter() - start) * 1000
        return OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=cost,
            latency_ms=latency_ms,
            ttft_ms=ttft,
            error=error,
        )


def rank_models_by_amd_optimization(model_ids: list[str]) -> list[str]:
    """Sort model IDs so AMD-native backends come first.

    NPU (FLM) < iGPU (ROCWMMA) < CPU (AVX-VNNI) < Cloud. Within a rank,
    preserve registry priority.
    """
    registry = get_registry()
    keyed: list[tuple[int, int, str]] = []
    for mid in model_ids:
        if mid not in registry.models:
            keyed.append((99, 999, mid))
            continue
        m = registry.models[mid]
        rank = _AMD_PATH_RANK.get(m.lane, 99)
        keyed.append((rank, m.priority, mid))
    keyed.sort()
    return [mid for _, _, mid in keyed]


def amd_optimized_hierarchy(
    *,
    include_cloud: bool = True,
    max_cost_usd: float = 0.05,
) -> TieredOrchestrator:
    """Build an orchestrator that prefers AMD-backed tiers in ascending cost.

    Tier 0: NPU (FLM, most AMD-native) — Gemma-4-E2B
    Tier 1: iGPU ROCWMMA — Gemma-4-E4B
    Tier 2: iGPU Unified (120GB GTT, MoE) — Gemma-4-26B-A4B
    Tier 3: CPU (AVX-VNNI) — Gemma-4-31B
    Tier 4+: Cloud fallback (Claude/Gemini CLI) — only if include_cloud
    """
    tiers: list[tuple[str, QualityGate]] = [
        ("Gemma-4-E2B-it-GGUF", QualityGate(min_chars=15)),
        ("Gemma-4-E4B-it-GGUF", QualityGate(min_chars=25)),
        ("Gemma-4-26B-A4B-it-GGUF", QualityGate(min_chars=40)),
        ("Gemma-4-31B-it-GGUF", QualityGate(min_chars=60)),
    ]
    if include_cloud:
        tiers.append(("claude-haiku-4-5", QualityGate(min_chars=80)))
        tiers.append(("claude-sonnet-4-6", QualityGate.TRUST))  # type: ignore[attr-defined]
    return TieredOrchestrator(
        tiers=tiers,  # type: ignore[arg-type]
        max_cost_usd=max_cost_usd,
    )


def build_gaia_native_tier(
    model_id: str = "Gemma-4-E2B-it-GGUF",
    *,
    silent: bool = True,
    base_url: str | None = "http://localhost:13305/v1",
) -> GaiaAgentTier:
    """Instantiate a GAIA ChatAgent bound to a specific lane, wrap as a tier.

    Uses ``skip_lemonade=True`` so we can pin the dispatch to the specific port.

    .. deprecated:: amd-gaia 0.19.0
        ChatAgent now hard-requires RAG deps (pypdf/sentence-transformers/faiss-cpu)
        at init; sentence-transformers segfaults on XDNA2 (harness CA1). This path
        fails init -> silent empty result. **Use :func:`build_gaia_llm_tier` instead**
        (GAIA's LemonadeClient, zero RAG deps, talks to the same fleet).
    """
    try:
        from gaia.agents.chat.agent import (  # type: ignore[import-not-found]
            ChatAgent,
            ChatAgentConfig,
        )
    except ImportError as exc:
        raise RuntimeError("amd-gaia not installed — `uv pip install amd-gaia`") from exc

    # ChatAgent doesn't pass skip_lemonade through its config, but the base Agent does.
    class FixedChatAgent(ChatAgent):
        def __init__(self, config):
            super().__init__(config=config)
            self.skip_lemonade = True

    config = ChatAgentConfig(
        model_id=model_id,
        base_url=base_url,
        silent_mode=silent,
    )
    agent = FixedChatAgent(config=config)
    return GaiaAgentTier(agent=agent, label=f"gaia:{model_id}")


def build_gaia_mcp_tier(
    model_id: str = "Gemma-4-E2B-it-GGUF",
    *,
    mcp_servers: dict[str, Any] | None = None,
    silent: bool = True,
    base_url: str | None = "http://localhost:13305/v1",
) -> GaiaAgentTier:
    """Instantiate a GAIA MCPAgent bound to a specific lane with tools, wrap as a tier."""
    try:
        from gaia.agents.mcp.agent import MCPAgent, MCPAgentConfig
    except ImportError as exc:
        raise RuntimeError("amd-gaia not installed — `uv pip install amd-gaia`") from exc

    class FixedMCPAgent(MCPAgent):
        def __init__(self, config):
            super().__init__(config=config)
            self.skip_lemonade = True

    config = MCPAgentConfig(
        model_id=model_id,
        base_url=base_url,
        mcp_servers=mcp_servers or {},
        silent_mode=silent,
    )
    agent = FixedMCPAgent(config=config)
    return GaiaAgentTier(agent=agent, label=f"gaia-mcp:{model_id}")


class _GaiaLLMClientShim:
    """Adapt GAIA's ``LemonadeClient`` to the ``.prompt(text) -> str`` surface that
    :class:`GaiaAgentTier` probes for.

    This is the WORKING GAIA path under amd-gaia 0.19.0: ``LemonadeClient`` is what the
    ``gaia llm`` CLI uses, has zero RAG dependencies, and talks to our already-running
    lemonade fleet (default router :13305). Unlike ``ChatAgent`` it does not pull in
    pypdf/sentence-transformers/faiss-cpu at init.
    """

    def __init__(
        self,
        client: object,
        model_id: str,
        *,
        max_tokens: int,
        temperature: float,
        extra_sampling: dict[str, str | float | int] | None = None,
    ):
        self._client = client
        self._model = model_id
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._extra_sampling = extra_sampling or {}

    def prompt(self, text: str) -> str:
        resp = self._client.chat_completions(  # type: ignore[attr-defined]
            model=self._model,
            messages=[{"role": "user", "content": text}],
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            auto_download=False,
            **self._extra_sampling,
        )
        # OpenAI-compatible shape; raise (don't silently return '') on an unexpected body
        return resp["choices"][0]["message"].get("content", "") or ""


class _LocalRouterClient:
    """Dependency-free fallback for GAIA's ``LemonadeClient`` — same ``.chat_completions``
    surface, but talks to the lemonade OmniRouter (:13305) directly over stdlib urllib.

    Used when ``amd-gaia`` is not installed: the GAIA ``LemonadeClient`` is only ever an
    OpenAI-compatible HTTP client to the same router the fleet already runs, so a missing
    optional SDK must NOT take down the loop while the router is healthy. Matches the
    stdlib-only transport idiom of :class:`~cohezion.inference.direct_tier.DirectLemonadeTier`.
    """

    def __init__(self, base_url: str, model: str, *, verbose: bool = False):
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model

    def chat_completions(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        auto_download: bool = False,  # GAIA-specific flag; ignored on the direct path
        **extra_sampling: str | float | int,
    ) -> dict[str, Any]:
        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
                **extra_sampling,
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310 (localhost :13305 router, fixed scheme)
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (localhost router)
            return json.loads(resp.read())


# Thinking/reasoning model families that stream chain-of-thought to a SEPARATE
# ``reasoning_content`` field on lemonade's llama.cpp backend. Without a reasoning-format
# override these return EMPTY ``content`` with finish_reason='length' on structured prompts
# at low budgets — the </think> block never closes in-budget, so every token lands in
# reasoning_content and content stays "" (defect 4dd925b0081f; verified 2-session 2026-07-12
# on Gemma-4-E4B/E2B: content 0->760/769/758). ``reasoning_format="none"`` keeps the answer
# IN content so it is non-empty. Excludes the NPU FastFlowLM backend (``*-FLM``): it has no
# reasoning_content channel and rejects the arg on some builds — this guard is load-bearing
# for the LIVE ``deepseek-r1-0528-8b-FLM`` NPU reasoning tier, which matches ``deepseek-r1``
# AND contains ``FLM`` (FLM check runs first). Matched CASE-INSENSITIVELY to mirror
# ``model_card_defaults.get_sampling_defaults`` (callers such as actioner/engine.py pass
# free-form ids, incl. lowercase/hyphenless ``gemma4``); a case-sensitive miss would let the
# model resolve as Gemma for temperature yet silently skip reasoning_format → defect returns.
_THINKING_MODEL_MARKERS = ("gemma-4", "gemma4", "gemma-3", "qwen3", "deepseek-r1")


def _is_llamacpp_thinking_model(model_id: str) -> bool:
    """True for llama.cpp-served reasoning models that stream to reasoning_content."""
    mid = model_id.lower()
    if "flm" in mid:  # NPU FastFlowLM backend — no reasoning_content channel
        return False
    return any(marker in mid for marker in _THINKING_MODEL_MARKERS)


def build_gaia_llm_tier(
    model_id: str = "Granite-4.1-8B-GGUF",
    *,
    base_url: str = "http://localhost:13305/api/v1",
    max_tokens: int = 512,
    temperature: float | None = None,
    silent: bool = True,
) -> GaiaAgentTier:
    """Wrap GAIA's ``LemonadeClient`` as a tier — the supported GAIA path (0.19.0+).

    Prefer this over :func:`build_gaia_native_tier`. Points at the existing fleet
    (router :13305) so GAIA does NOT spawn a second lemonade (OOM-safe on the shared box).
    Note: GAIA may reload the target model to its expected ctx (32768) on first call,
    which mutates shared fleet state — pin a model the fleet already serves at that ctx,
    or accept the one-time reload.
    """
    try:
        from gaia.llm.lemonade_client import LemonadeClient  # type: ignore[import-not-found]

        client_factory: Any = LemonadeClient
        label_prefix = "gaia-llm"
    except ImportError:
        # amd-gaia absent: GAIA's LemonadeClient is only an OpenAI-compatible HTTP client to
        # the :13305 router the fleet already runs. A missing OPTIONAL SDK must not take down
        # the compound loop / actioner while the router is healthy — fall back to a stdlib
        # client with the same .chat_completions surface (local-inference-first). The router
        # is the real dependency; the SDK is not.
        client_factory = _LocalRouterClient
        label_prefix = "local-router"

    # TR1 (2026-07-07, restored 2026-07-09): temperature=None resolves the model's
    # card sampling defaults (temp + top_k/top_p/min_p) instead of a fixed 0.0 for
    # every model — greedy 0.0 on Gemma-family cards (which want temp 1.0) produces
    # degenerate/empty output. An explicit temperature= still overrides.
    extra_sampling: dict[str, str | float | int] = {}
    if temperature is None:
        from cohezion.inference.model_card_defaults import get_sampling_defaults

        sampling = get_sampling_defaults(model_id)
        # Unknown model: generic NON-ZERO fallback. 0.0-greedy is never a safe guess
        # (degenerate on Gemma-family cards); 0.7 is the least-surprising generic. Family
        # extras (top_k/top_p) are only sent on a real registry match.
        temperature = float(sampling.get("temperature", 0.7))
        extra_sampling = {k: v for k, v in sampling.items() if k != "temperature"}

    # defect 4dd925b0081f: thinking models stream CoT to reasoning_content and return EMPTY
    # content on structured prompts at low budgets. reasoning_format="none" keeps the answer
    # in content. Flows through extra_sampling into BOTH the gaia LemonadeClient (verified:
    # its chat_completions ends in **kwargs, merged straight into the request payload) and the
    # _LocalRouterClient payload. setdefault is defensive — card defaults never set it today.
    if _is_llamacpp_thinking_model(model_id):
        extra_sampling.setdefault("reasoning_format", "none")

    client = client_factory(base_url=base_url, model=model_id, verbose=not silent)
    shim = _GaiaLLMClientShim(
        client,
        model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        extra_sampling=extra_sampling,
    )
    return GaiaAgentTier(agent=shim, label=f"{label_prefix}:{model_id}")
