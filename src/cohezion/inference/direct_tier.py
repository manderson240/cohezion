"""Direct HTTP lemonade tier — bypasses GAIA LemonadeManager singleton.

The GAIA LemonadeManager uses a class-level singleton that assumes one lemonade
port per process. For multi-port TieredOrchestrator (NPU/iGPU/CPU each on a
different port), each tier needs its own connection. This module provides
DirectLemonadeTier: a drop-in replacement that talks to lemonade via httpx
without touching LemonadeManager.

Validated in exp_OOOO3 and exp_PPPP3 (2026-05-30, autoresearch round 13).
"""

from __future__ import annotations

import asyncio
import logging
import time

from cohezion.inference.orchestrator import OrchestrationResult


logger = logging.getLogger(__name__)

_NO_THINK_MODELS = frozenset(
    {
        "Qwen3-0.6B-GGUF",
        "Qwen3-8B-GGUF",
        "Qwen3.5-35B-A3B-GGUF",
        "Qwen3.5-4B-MTP-GGUF",
        "Qwen3-14B-GGUF",
    }
)


class DirectLemonadeTier:
    """Thin async wrapper for a single lemonade port.

    Parameters
    ----------
    port : int
        Lemonade port to target (e.g. 13306 for NPU, 13309 for CPU).
    model_id : str
        Model ID to request (must be loaded on the target port).
    max_tokens : int
        Maximum tokens to generate (default 512).
    temperature : float
        Sampling temperature (default 0.3).
    """

    def __init__(
        self,
        port: int,
        model_id: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        self.port = port
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.label = f"direct:{model_id}"
        self._base_url = f"http://localhost:{port}/v1/chat/completions"

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        """Dispatch prompt to lemonade via direct HTTP, return OrchestrationResult."""
        import httpx

        start = time.perf_counter()
        text = ""
        error: str | None = None

        messages = []
        if self.model_id in _NO_THINK_MODELS:
            messages.append({"role": "system", "content": "/no_think"})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self._base_url,
                    json={
                        "model": self.model_id,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                msg = data["choices"][0]["message"]
                # F2 (audit 2026-06-09): thinking models (deepseek-r1, FLM) emit the answer in
                # reasoning_content with empty content; fall back so the tier doesn't drop the
                # response and escalate. Mirrors fleet.py's _dispatch_openai_compatible.
                text = (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "").strip()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.debug("DirectLemonadeTier %s port %d: %s", self.model_id, self.port, error)

        latency_ms = (time.perf_counter() - start) * 1000
        return OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,
            latency_ms=latency_ms,
            ttft_ms=None,
            error=error,
        )


def build_direct_npu_tier(
    port: int = 13306,
    model_id: str = "llama3.2-1b-FLM",
    *,
    silent: bool = True,
) -> DirectLemonadeTier:
    """NPU tier via direct HTTP — bypasses GAIA singleton.

    DEPRECATED (Phase 2, 2026-06-09): prefer ``build_router_npu_tier`` which targets the
    router (:13305) and does not depend on a dedicated :13306 server being up.
    Retained non-destructively per the non-destructive-wiring policy.
    """
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=256)


def build_direct_igpu_tier(
    port: int = 13307,
    model_id: str = "Gemma-4-E4B-it-GGUF",
) -> DirectLemonadeTier:
    """iGPU tier via direct HTTP.

    DEPRECATED (Phase 2, 2026-06-09): prefer ``build_router_igpu_tier`` which targets the
    router (:13305) and does not depend on a dedicated :13307 server being up.
    Retained non-destructively per the non-destructive-wiring policy.
    """
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=512)


def build_direct_cpu_tier(
    port: int = 13309,
    model_id: str = "Gemma-4-31B-it-GGUF",
) -> DirectLemonadeTier:
    """CPU tier via direct HTTP to a DEDICATED per-port server (legacy/optional).

    NOTE (router-centric topology, 2026-06): the dedicated :13309 CPU server is often DOWN.
    The PRIMARY CPU reasoner path is ``build_router_cpu_tier`` (router :13305 with
    ``llamacpp_backend=cpu``). This direct-port builder is retained as the legacy alternative
    for deployments that still run a dedicated :13309 lemonade instance.
    """
    return DirectLemonadeTier(port=port, model_id=model_id, max_tokens=512)


# Bounded context for the CPU reasoner. N3 (OOM crasher): never let the :13305 router auto-load
# a heavy model at ctx_size=0 (full ~256K context → unbounded KV cache → hard UMA hang). 16384 is
# the safe global default; the load is issued explicitly with save_options so the bound persists.
_ROUTER_CPU_CTX_SIZE = 16384


class RouterCpuTier(DirectLemonadeTier):
    """PRIMARY CPU reasoner tier via the lemonade router (:13305).

    :13305 is the canonical unified interface — a single Lemonade Server serves the whole catalog
    on demand and dispatches to the right backend (NPU / iGPU / CPU). This tier targets the router
    and selects ``llamacpp_backend=cpu`` per-request, so it does not depend on a dedicated :13309
    server being up.

    OOM safety (N3): before the first chat request, this tier explicitly pre-loads the model with a
    BOUNDED ``ctx_size`` (≤16384) and ``save_options=true`` via ``POST :13305/api/v1/load``. This
    guarantees the router never auto-loads the reasoner at ``ctx_size=0``. The load is idempotent
    and issued once (guarded by ``_loaded``); a load failure is non-fatal — the chat request will
    still run, and the model card's persisted bound applies.
    """

    def __init__(
        self,
        *,
        port: int = 13305,
        model_id: str = "Gemma-4-31B-it-GGUF",
        ctx_size: int = _ROUTER_CPU_CTX_SIZE,
        backend: str = "cpu",
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        # Clamp ctx to the bounded ceiling — N3 forbids unbounded (0 / huge) ctx on heavy models.
        ctx_size = min(max(1, ctx_size), _ROUTER_CPU_CTX_SIZE)
        super().__init__(
            port=port, model_id=model_id, max_tokens=max_tokens, temperature=temperature
        )
        self.ctx_size = ctx_size
        self.backend = backend
        self.label = f"router:{model_id}"
        self._load_url = f"http://localhost:{port}/api/v1/load"
        self._loaded = False
        self._load_lock = asyncio.Lock()  # F3: serialize concurrent preloads (item 113)

    async def _ensure_loaded(self) -> None:
        """Pre-load the reasoner on the router with a bounded ctx_size (N3).

        F3: a lock serializes concurrent preloads (one ``/api/v1/load``, not N — item 113).
        F4: ``_loaded`` is set ONLY on success — a failed preload retries the BOUNDED load
        next call rather than letting the router auto-load at an unbounded ctx (N3).
        """
        if self._loaded:
            return
        import httpx

        async with self._load_lock:
            if self._loaded:  # another coroutine completed the load while we waited
                return
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        self._load_url,
                        json={
                            "model_name": self.model_id,
                            "llamacpp_backend": self.backend,
                            "ctx_size": self.ctx_size,  # N3: bounded ≤16384, never 0
                            "save_options": True,
                        },
                    )
                    resp.raise_for_status()
                self._loaded = True  # F4: only mark loaded on SUCCESS
            except Exception as exc:  # F4: do NOT mark loaded — next call retries bounded load
                logger.debug(
                    "RouterCpuTier pre-load (%s, backend=%s, ctx=%d) failed: %s",
                    self.model_id,
                    self.backend,
                    self.ctx_size,
                    exc,
                )

    async def run(self, prompt: str, **kwargs: object) -> OrchestrationResult:
        await self._ensure_loaded()
        return await super().run(prompt, **kwargs)


def build_router_cpu_tier(
    port: int = 13305,
    model_id: str = "Gemma-4-31B-it-GGUF",
    *,
    ctx_size: int = _ROUTER_CPU_CTX_SIZE,
    backend: str = "cpu",
) -> RouterCpuTier:
    """PRIMARY CPU reasoner tier — router :13305 with ``llamacpp_backend=cpu``, bounded ctx (N3).

    This is the default CPU lane in the router-centric topology. Use ``build_direct_cpu_tier`` only
    for the legacy dedicated :13309 server.
    """
    return RouterCpuTier(port=port, model_id=model_id, ctx_size=ctx_size, backend=backend)


# ---------------------------------------------------------------------------
# RouterTier — generic router-centric tier for NPU and iGPU lanes (Phase 2)
# ---------------------------------------------------------------------------
# Mirrors RouterCpuTier exactly but accepts any backend string.
# Targets :13305 (unified lemonade router) so callers don't depend on a
# dedicated per-port server being up.  N3 OOM guard is inherited: bounded
# ctx_size (≤16384) is pre-loaded via POST /api/v1/load before the first
# chat request.
# ---------------------------------------------------------------------------


class RouterTier(DirectLemonadeTier):
    """Generic router-centric tier via the lemonade router (:13305).

    Unlike ``DirectLemonadeTier`` (which targets a dedicated per-port server),
    this tier talks exclusively to the unified router and selects the backend
    via a per-load ``backend`` hint.  This makes NPU and iGPU lanes available
    even when the dedicated :13306/:13307 servers are down.

    OOM safety (N3): identical to ``RouterCpuTier`` — the model is pre-loaded
    with a BOUNDED ``ctx_size`` (≤16384) and ``save_options=true`` before the
    first chat request, preventing the router from auto-loading at ctx_size=0.

    Parameters
    ----------
    backend : str
        Routing hint sent to the router's load endpoint.  Values:
        ``"npu"``    — FLM recipe (omits ``llamacpp_backend`` key in payload)
        ``"vulkan"`` — iGPU Vulkan/RDNA (``llamacpp_backend=vulkan``)
        ``"cpu"``    — CPU AVX-512 (``llamacpp_backend=cpu``)
        ``"auto"``   — router decides (omits the key entirely)
    """

    # FLM-recipe models: the router's load endpoint does NOT accept
    # ``llamacpp_backend`` for FLM-served models.  Mirror the frozenset from
    # router_client.py to avoid a circular import.
    _FLM_RECIPE_MODELS: frozenset[str] = frozenset(
        {
            "llama3.2-1b-FLM",
            "gemma3-4b-FLM",
            "deepseek-r1-0528-8b-FLM",
            "qwen3.5-4b-FLM",
        }
    )

    def __init__(
        self,
        *,
        port: int = 13305,
        model_id: str,
        backend: str = "auto",
        ctx_size: int = _ROUTER_CPU_CTX_SIZE,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        # Clamp ctx to the bounded ceiling — N3 forbids unbounded (0 / huge) ctx.
        ctx_size = min(max(1, ctx_size), _ROUTER_CPU_CTX_SIZE)
        super().__init__(
            port=port, model_id=model_id, max_tokens=max_tokens, temperature=temperature
        )
        self.ctx_size = ctx_size
        self.backend = backend
        self.label = f"router:{model_id}"
        self._load_url = f"http://localhost:{port}/api/v1/load"
        self._loaded = False
        self._load_lock = asyncio.Lock()  # F3: serialize concurrent preloads (item 113)

    def _build_load_payload(self) -> dict:
        """Build the /api/v1/load payload, omitting llamacpp_backend for FLM models."""
        payload: dict = {
            "model_name": self.model_id,
            "ctx_size": self.ctx_size,  # N3: bounded ≤16384, never 0
            "save_options": True,
        }
        # FLM-recipe models do not accept llamacpp_backend; npu/auto also omit it.
        if self.backend not in ("npu", "auto") and self.model_id not in self._FLM_RECIPE_MODELS:
            payload["llamacpp_backend"] = self.backend
        return payload

    async def _ensure_loaded(self) -> None:
        """Pre-load the model on the router with a bounded ctx_size (N3).

        F3: a lock serializes concurrent preloads so N ``run_batch`` coroutines fire ONE
        ``/api/v1/load``, not N (the storm that saturated :13305 / starved the bot, item 113).
        F4: ``_loaded`` is set ONLY on a successful load — a failed preload retries the BOUNDED
        load on the next call rather than letting the router auto-load at an unbounded ctx (N3).
        """
        if self._loaded:
            return
        import httpx

        async with self._load_lock:
            if self._loaded:  # another coroutine completed the load while we waited
                return
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(self._load_url, json=self._build_load_payload())
                    resp.raise_for_status()
                self._loaded = True  # F4: only mark loaded on SUCCESS
            except Exception as exc:  # F4: do NOT mark loaded — next call retries bounded load
                logger.debug(
                    "RouterTier pre-load (%s, backend=%s, ctx=%d) failed: %s",
                    self.model_id,
                    self.backend,
                    self.ctx_size,
                    exc,
                )

    async def run(self, prompt: str, **kwargs: object) -> OrchestrationResult:
        await self._ensure_loaded()
        return await super().run(prompt, **kwargs)


def build_router_npu_tier(
    port: int = 13305,
    model_id: str = "llama3.2-1b-FLM",
    *,
    ctx_size: int = _ROUTER_CPU_CTX_SIZE,
) -> RouterTier:
    """PRIMARY NPU tier — router :13305 with FLM recipe, bounded ctx (N3).

    Targets the unified lemonade router instead of the dedicated :13306 server, so this
    tier works even when the per-port NPU daemon is down.  FLM-recipe models omit
    ``llamacpp_backend`` in the load payload (the router recognises them by model_id).
    """
    return RouterTier(
        port=port, model_id=model_id, backend="npu", ctx_size=ctx_size, max_tokens=256
    )


def build_router_igpu_tier(
    port: int = 13305,
    model_id: str = "deepseek-r1-0528-8b-FLM",
    *,
    ctx_size: int = _ROUTER_CPU_CTX_SIZE,
) -> RouterTier:
    """PRIMARY iGPU tier — router :13305 with Vulkan/RDNA backend, bounded ctx (N3).

    Targets the unified lemonade router instead of the dedicated :13307 server, so this
    tier works even when the per-port iGPU daemon is down.
    """
    return RouterTier(
        port=port, model_id=model_id, backend="vulkan", ctx_size=ctx_size, max_tokens=512
    )


# ---------------------------------------------------------------------------
# ## FUTURE HOOKS
# ---------------------------------------------------------------------------
# FH-1 (Phase 3): when router gains a /api/v1/backend-hint RPC, remove the
#        _build_load_payload() workaround and pass backend via that endpoint.
# FH-2 (Phase 4): retire build_direct_npu_tier / build_direct_igpu_tier once
#        the per-port :13306/:13307 daemons are fully decommissioned.
# ---------------------------------------------------------------------------
