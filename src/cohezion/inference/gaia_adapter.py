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
import re
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


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# Gemma-4 does NOT use <think>. It emits a Harmony-style channel: `<|channel>thought ... ` and
# closes with `<channel|>` -- note the pipe MOVES between the open and close forms. Observed
# 2026-08-16 on Gemma-4-26B-A4B: a 2095-char reply that was reasoning up to `<channel|>` and the
# answer after it. Stripping only <think> left all of it reaching the caller while every unit
# test passed, because the fixtures used the delimiter that was already known.
#
# Both families are the same shape -- reasoning, delimiter, answer -- so the general rule is
# "take what follows the LAST closing delimiter". Anything unrecognised falls through to the
# empty-guard and is returned as-is, so a new family degrades to today's behaviour rather than
# to a wrong answer.
#
# The closer is only treated as MARKUP when its OPENER appears earlier in the text. Without that
# check, any output that merely QUOTES the delimiter gets truncated at the quote: an adversarial
# review of this very function returned only the text after the `<channel|>` it was discussing,
# silently destroying its own preamble (observed 2026-08-16 — two of three review lanes were
# mangled this way, and the failure looked like the model stopping early). A delimiter used as
# markup and one quoted as content are not distinguishable from the closer alone.
#
# The `<think>` path needs no equivalent guard: _THINK_RE requires BOTH tags, so a bare quoted
# `</think>` never matches. Only the channel form was splitting on an unpaired closer.
_CHANNEL_OPEN = "<|channel>"
_CHANNEL_CLOSE = "<channel|>"


def _answer_only(content: str, reasoning: str) -> str:
    """Return the ANSWER, whichever channel the backend used to deliver it.

    A lane's reasoning arrives in one of two places and which one is not a property of the model
    -- it is decided by whether ``reasoning_format="none"`` was sent, which depends on a substring
    match, and which the FLM backend ignores entirely (measured 2026-08-16, see
    docs/benchmarks/lane_selection.md). Callers should not have to care, so normalise here:

      1. prefer ``content``; fall back to ``reasoning_content`` when content is empty
      2. strip inline ``<think>...</think>`` blocks (Qwen / DeepSeek families)
      3. keep only what follows the last ``<channel|>`` (Gemma-4 Harmony family)
      4. NEVER return empty as a result of steps 2-3

    Step 3 is the part gauntlet.py:202 is missing. It applies the same regex with no guard, so a
    reply that is ENTIRELY a think block collapses to "" -- which is precisely the empty-content
    failure (defect 4dd925b0081f) that the reasoning_format guard exists to prevent, reintroduced
    by the cleanup meant to help. A response with no answer outside its thinking is better
    returned raw than as nothing: the caller can see what happened.

    An UNCLOSED ``<think>`` (budget exhausted before the block closed) is deliberately left
    alone. The regex requires a closing tag, so nothing matches, and that is correct -- with no
    closing tag there is no way to tell where reasoning ends and an answer begins.
    """
    text = content.strip() or reasoning
    out = _THINK_RE.sub("", text)
    close_at = out.rfind(_CHANNEL_CLOSE)
    # Paired only: the opener must appear BEFORE the closer for this to be markup rather than
    # prose quoting the delimiter. rfind for the closer because Gemma drafts an answer inside
    # its reasoning before emitting the final channel, so the LAST closer is the real boundary.
    if close_at != -1 and 0 <= out.find(_CHANNEL_OPEN) < close_at:
        out = out[close_at + len(_CHANNEL_CLOSE) :]
    return out.strip() or text


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
        # Duck-typed: a real gaia.Agent exposes neither attribute, and reports 0. Reading them
        # via getattr keeps this adapter working against any agent implementation rather than
        # coupling it to _GaiaLLMClientShim.
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
            gen_tokens=int(getattr(self.agent, "last_gen_tokens", 0) or 0),
            dropped_reasoning_chars=int(
                getattr(self.agent, "last_dropped_reasoning_chars", 0) or 0
            ),
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
        # Telemetry from the most recent prompt(). Initialised so a reader before the first call
        # sees 0 rather than an AttributeError -- 0 is also the honest value for "nothing run".
        self.last_gen_tokens: int = 0
        self.last_dropped_reasoning_chars: int = 0

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
        msg = resp["choices"][0]["message"]
        # Defence in depth for defect 4dd925b0081f. reasoning_format="none" (set by
        # build_gaia_llm_tier when _THINKING_MODEL_MARKERS matches) is the PREFERRED fix, but it
        # depends on a substring list, so any thinking model whose id is not listed silently
        # returns "" and every caller reads that as "no answer" — the adversarial gate reads it
        # as fail-open APPROVE. Verified 2026-07-28: Bonsai-27B-gguf matches no marker and
        # returned content=0 / reasoning_content=456, scoring 0/8 on a benchmark purely as a
        # harness artifact. Falling back here makes the marker list an optimisation rather than
        # a correctness dependency. gauntlet.py:201-202 has the complete pattern; this call site
        # previously copied only line 201 (the fallback) and not line 202 (the <think> strip), so
        # a guarded lane returned its whole chain of thought to every caller. _answer_only()
        # implements both, plus the empty-guard gauntlet lacks.
        content = (msg.get("content") or "").strip()
        reasoning = msg.get("reasoning_content") or ""

        # Record what this call actually cost and what we threw away, for the caller that cares.
        # The fallback above keeps an unlisted thinking model CORRECT, but it cannot make it
        # COMPARABLE: when content is non-empty, `reasoning` is silently discarded, so the
        # returned string understates the work done by however long that reasoning was. Without
        # this a measurement harness cannot tell a genuinely terse lane from a heavily-stripped
        # one -- which is exactly how a routing table came to rank gpt-oss-20b cheapest on
        # 2026-08-16 when token counts put it second (see docs/benchmarks/lane_selection.md).
        self.last_gen_tokens = int((resp.get("usage") or {}).get("completion_tokens", 0) or 0)
        answer = _answer_only(content, reasoning)
        # Count BOTH ways reasoning gets discarded, or the number understates itself:
        #   channel — `reasoning_content` dropped wholesale when `content` carried the answer
        #   inline  — <think>/<|channel> text removed from within the returned string
        # Counting only the channel made the benchmark print "no lane had reasoning stripped"
        # for a run in which Qwen3-8B had ~2240 chars stripped inline (2026-08-16). A telemetry
        # field that reports zero while its own subject is happening is worse than none.
        channel_dropped = len(reasoning) if content else 0
        inline_dropped = max(0, len(content or reasoning) - len(answer))
        self.last_dropped_reasoning_chars = channel_dropped + inline_dropped
        return answer


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
# `bonsai` added 2026-07-28: Bonsai IS a llama.cpp thinking family — verified live on :13305
# (content='OK' while reasoning_content held a full "Here's a thinking process:…" trace). Omitting
# it meant reasoning_format='none' was never sent, so on substantial prompts the CoT consumed the
# whole budget and `content` returned EMPTY. Budget-dependent, hence long-invisible: short prompts
# answered fine while every long one silently returned "". See test_predicate_flags_bonsai_family.
_THINKING_MODEL_MARKERS = ("gemma-4", "gemma4", "gemma-3", "qwen3", "deepseek-r1", "bonsai")


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
