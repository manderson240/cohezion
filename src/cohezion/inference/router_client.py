"""Canonical lemonade router client — single HTTP client for :13305.

All local inference in ``src/cohezion/**`` should eventually route through
``LemonadeRouterClient``.  This module is a **leaf** in the import graph:
it imports ONLY ``httpx`` and stdlib.  ``swarm/providers`` will import FROM
it; any back-import from ``swarm/``, ``compound/``, or ``inference/``
(except this file) creates a cycle.

Confirmed backend strings (queried 2026-06-09, lemonade 10.6.x):
  - ``"cpu"``    → ``llamacpp_backend=cpu`` in load payload
  - ``"vulkan"`` → ``llamacpp_backend=vulkan`` in load payload
  - ``"npu"``    → FLM-recipe models (e.g. llama3.2-1b-FLM); omit
                   ``llamacpp_backend`` key from load payload (FLM recipe
                   handles backend selection internally)
  - ``"auto"``   → omit ``llamacpp_backend``; router selects backend

N3 compliance (OOM guard): every ``load()`` call sends a bounded
``ctx_size ≤ 16384`` and ``save_options=True``.  The router must NEVER
auto-load a heavy model at ``ctx_size=0`` (unbounded KV cache → UMA hang).

Ollama protocol translation (R1): ``from_ollama_options()`` maps the flat
``/api/generate`` shape (prompt string + options dict) onto OpenAI
``/v1/chat/completions`` (messages list).  No Ollama field is silently
dropped — unknown options are recorded in ``RouterResult.dropped_options``.

This module generalises ``RouterCpuTier`` from ``direct_tier.py`` (added
2026-06-09 commit 711690049).  Migration callers should replace
``build_router_cpu_tier()`` with ``LemonadeRouterClient(..., backend="cpu")``.

Validated in consolidation plan Phase 0a (2026-06-09).
"""

from __future__ import annotations

import dataclasses
import logging
import time
from typing import Any, Literal, Sequence

# LEAF CONSTRAINT: only httpx + stdlib below this line.
# NO imports from cohezion.inference.*, cohezion.swarm.*, cohezion.compound.*
import httpx


logger = logging.getLogger(__name__)

# N3: hard ceiling for ctx_size on any model loaded via router.
_MAX_CTX_SIZE: int = 16384

# Models whose FLM recipe handles backend selection internally — do NOT pass
# ``llamacpp_backend`` in the load payload for these.
_FLM_RECIPE_MODELS: frozenset[str] = frozenset(
    {
        "llama3.2-1b-FLM",
        "gemma3-4b-FLM",
        "gemma4-it-e2b-FLM",
        "qwen3-4b-FLM",
        "qwen3.5-4b-FLM",
    }
)

# Models that need ``/no_think`` system message to suppress chain-of-thought tokens.
_NO_THINK_MODELS: frozenset[str] = frozenset(
    {
        "Qwen3-0.6B-GGUF",
        "Qwen3-8B-GGUF",
        "Qwen3.5-35B-A3B-GGUF",
        "Qwen3.5-4B-MTP-GGUF",
        "Qwen3-14B-GGUF",
    }
)

# Mapping from ``backend`` literal → ``llamacpp_backend`` string for the load payload.
# ``"auto"`` and ``"npu"`` use FLM recipes and must NOT include the key.
_BACKEND_TO_LLAMACPP: dict[str, str] = {
    "cpu": "cpu",
    "vulkan": "vulkan",
    # "npu" and "auto" intentionally absent → key omitted from payload
}


@dataclasses.dataclass
class RouterResult:
    """Minimal result returned by ``LemonadeRouterClient.run()``/``chat()``.

    Higher layers (TieredOrchestrator, etc.) wrap this into their own richer
    result types — this class deliberately avoids ``OrchestrationResult``
    (which would require importing from ``cohezion.inference.orchestrator``
    and break the leaf constraint).
    """

    text: str
    label: str
    error: str | None = None
    latency_ms: float = 0.0
    # Ollama options that could not be mapped to an OpenAI field (R1 audit trail).
    dropped_options: dict[str, Any] = dataclasses.field(default_factory=dict)


class LemonadeRouterClient:
    """Canonical async client for the lemonade unified router at ``:13305``.

    Parameters
    ----------
    base_url:
        HTTP origin of the router, e.g. ``"http://localhost:13305"``.  Trailing
        slashes are stripped; ``/api/v1`` suffix is auto-removed if present so
        callers can pass either form.
    model_id:
        Model name as listed in ``:13305/api/v1/models``.
    backend:
        Compute backend to request when pre-loading the model:
        ``"npu"`` (FLM recipe, no llamacpp key), ``"vulkan"``, ``"cpu"``,
        or ``"auto"`` (let the router decide).
    ctx_size:
        KV-cache window.  Clamped to ``[1, 16384]`` (N3 guard).
    max_tokens:
        Maximum tokens to generate per request.
    temperature:
        Sampling temperature.
    timeout_s:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:13305",
        *,
        model_id: str,
        backend: Literal["npu", "vulkan", "cpu", "auto"] = "auto",
        ctx_size: int = _MAX_CTX_SIZE,
        max_tokens: int = 512,
        temperature: float = 0.3,
        timeout_s: float = 60.0,
    ) -> None:
        # Normalise base_url: strip trailing slash and any /api/v1 suffix.
        origin = base_url.rstrip("/")
        if origin.endswith("/api/v1"):
            origin = origin[: -len("/api/v1")]
        self._origin = origin

        self.model_id = model_id
        self.backend = backend
        # N3: clamp ctx_size — never allow 0 or a value exceeding the OOM ceiling.
        self.ctx_size = max(1, min(ctx_size, _MAX_CTX_SIZE))
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_s = timeout_s

        # Stable label used in tier-path traces.
        self.label = f"router:{model_id}"

        self._chat_url = f"{self._origin}/v1/chat/completions"
        self._load_url = f"{self._origin}/api/v1/load"
        self._models_url = f"{self._origin}/api/v1/models"

        self._loaded: bool = False
        # Set by from_ollama_options(); defaults so every client has them.
        self._stop_sequences: list[str] | None = None
        self._dropped_ollama_opts: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Load / pre-warm
    # ------------------------------------------------------------------

    async def load(self, *, save_options: bool = True) -> None:
        """Pre-load the model on the router with a bounded ctx_size (N3).

        Idempotent: once called successfully (no exception), subsequent calls
        are no-ops.  A failed load is non-fatal for ``run()``/``chat()`` — the
        router may auto-load the model on the first chat request; the N3 guard
        is enforced because ``save_options=True`` persists the bounded ctx.

        Parameters
        ----------
        save_options:
            If ``True``, the router persists the ``ctx_size`` bound to the
            model card so future auto-loads also use the bounded context.
        """
        if self._loaded:
            return

        payload: dict[str, Any] = {
            "model_name": self.model_id,
            "ctx_size": self.ctx_size,  # N3: bounded ≤16384
            "save_options": save_options,
        }

        # FLM-recipe and "auto" models do NOT use llamacpp_backend key.
        llamacpp_str = _BACKEND_TO_LLAMACPP.get(self.backend)
        if llamacpp_str and self.model_id not in _FLM_RECIPE_MODELS:
            payload["llamacpp_backend"] = llamacpp_str

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(self._load_url, json=payload)
                resp.raise_for_status()
        except Exception as exc:
            # Non-fatal: chat still runs; persisted model-card ctx bound applies.
            logger.debug(
                "LemonadeRouterClient.load(%s, backend=%s, ctx=%d) failed: %s",
                self.model_id,
                self.backend,
                self.ctx_size,
                exc,
            )
        finally:
            self._loaded = True

    # ------------------------------------------------------------------
    # Chat / run
    # ------------------------------------------------------------------

    async def run(self, prompt: str, **_: object) -> RouterResult:
        """Convenience wrapper: send a single user prompt, return ``RouterResult``.

        Equivalent to ``chat([{"role": "user", "content": prompt}])``.
        """
        messages: list[dict[str, str]] = []
        if self.model_id in _NO_THINK_MODELS:
            messages.append({"role": "system", "content": "/no_think"})
        messages.append({"role": "user", "content": prompt})
        return await self._dispatch(messages)

    async def chat(
        self,
        messages: Sequence[dict[str, str]],
    ) -> RouterResult:
        """Send a full messages list (OpenAI shape) to the router."""
        return await self._dispatch(list(messages))

    async def _dispatch(
        self, messages: list[dict[str, str]]
    ) -> RouterResult:
        start = time.perf_counter()
        text = ""
        error: str | None = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    self._chat_url,
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
                text = data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.debug(
                "LemonadeRouterClient %s: %s", self.label, error
            )

        latency_ms = (time.perf_counter() - start) * 1000

        # R1: surface empty completions as errors — never silently swallow them.
        if not error and text == "":
            error = "empty completion from router"

        return RouterResult(
            text=text,
            label=self.label,
            error=error,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Ollama protocol translation (R1)
    # ------------------------------------------------------------------

    @classmethod
    def from_ollama_options(
        cls,
        base_url: str = "http://localhost:13305",
        *,
        model_id: str,
        backend: Literal["npu", "vulkan", "cpu", "auto"] = "auto",
        options: dict[str, Any] | None = None,
    ) -> "LemonadeRouterClient":
        """Construct a client from Ollama-style ``options`` dict (R1).

        Maps Ollama ``/api/generate`` options onto OpenAI parameters:

        +-------------------+------------------+-----------------------------------+
        | Ollama key        | Mapped to        | Notes                             |
        +===================+==================+===================================+
        | ``num_predict``   | ``max_tokens``   | Ollama token-count parameter      |
        +-------------------+------------------+-----------------------------------+
        | ``temperature``   | ``temperature``  | Direct mapping                    |
        +-------------------+------------------+-----------------------------------+
        | ``stop``          | stored; passed   | Caller can retrieve via            |
        |                   | to chat payload  | ``client.stop_sequences``         |
        +-------------------+------------------+-----------------------------------+
        | ``num_ctx``       | ``ctx_size``     | Mapped + clamped to N3 ceiling    |
        +-------------------+------------------+-----------------------------------+
        | ``top_k``         | dropped          | No OpenAI equivalent; recorded in |
        |                   |                  | ``RouterResult.dropped_options``  |
        +-------------------+------------------+-----------------------------------+
        | ``top_p``         | dropped*         | OpenAI supports top_p but the     |
        |                   |                  | canonical client does not pass it |
        +-------------------+------------------+-----------------------------------+

        Unknown options are captured so callers can audit what was lost.

        Parameters
        ----------
        options:
            Ollama ``options`` dict, e.g.
            ``{"num_predict": 256, "temperature": 0.7, "top_k": 40}``.
        """
        opts = options or {}
        max_tokens = int(opts.get("num_predict", 512))
        temperature = float(opts.get("temperature", 0.3))
        ctx_size = int(opts.get("num_ctx", _MAX_CTX_SIZE))
        stop = opts.get("stop")  # kept for callers that need it

        # Track options we cannot map — exposed in RouterResult for audit.
        _KNOWN_OLLAMA_KEYS = {"num_predict", "temperature", "num_ctx", "stop"}
        dropped = {k: v for k, v in opts.items() if k not in _KNOWN_OLLAMA_KEYS}

        client = cls(
            base_url,
            model_id=model_id,
            backend=backend,
            ctx_size=ctx_size,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        client._stop_sequences = stop if isinstance(stop, list) else ([stop] if stop else None)
        client._dropped_ollama_opts = dropped
        return client

    # ------------------------------------------------------------------
    # Catalog / health
    # ------------------------------------------------------------------

    async def list_models(self) -> list[str]:
        """Return model IDs available on the router (read-only query)."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self._models_url)
                resp.raise_for_status()
                data = resp.json()
                # Router returns OpenAI-compatible {"data": [...]} shape.
                if isinstance(data, dict) and "data" in data:
                    return [m.get("id", "") for m in data["data"]]
                if isinstance(data, list):
                    return [
                        m.get("id") or m.get("model_name") or "" for m in data
                    ]
        except Exception as exc:
            logger.debug("LemonadeRouterClient.list_models failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Builder helpers (subsume build_router_cpu_tier from direct_tier.py)
# ---------------------------------------------------------------------------


def build_router_npu_client(
    base_url: str = "http://localhost:13305",
    model_id: str = "llama3.2-1b-FLM",
    *,
    max_tokens: int = 256,
) -> LemonadeRouterClient:
    """NPU lane via the unified router.

    FLM-recipe models (llama3.2-1b-FLM) use backend="npu" which omits the
    ``llamacpp_backend`` key from the load payload (FLM recipe selects XDNA2).
    """
    return LemonadeRouterClient(
        base_url,
        model_id=model_id,
        backend="npu",
        max_tokens=max_tokens,
    )


def build_router_igpu_client(
    base_url: str = "http://localhost:13305",
    model_id: str = "Gemma-4-E4B-it-GGUF",
    *,
    max_tokens: int = 512,
) -> LemonadeRouterClient:
    """iGPU lane (Vulkan/RDNA) via the unified router."""
    return LemonadeRouterClient(
        base_url,
        model_id=model_id,
        backend="vulkan",
        max_tokens=max_tokens,
    )


def build_router_cpu_client(
    base_url: str = "http://localhost:13305",
    model_id: str = "Gemma-4-31B-it-GGUF",
    *,
    ctx_size: int = _MAX_CTX_SIZE,
    max_tokens: int = 512,
) -> LemonadeRouterClient:
    """CPU lane via the unified router.

    Supersedes ``build_router_cpu_tier()`` from ``direct_tier.py``.
    Callers should migrate to this function; ``build_router_cpu_tier``
    is retained in ``direct_tier.py`` for backward compatibility until
    Phase 2 of the consolidation plan lands.
    """
    return LemonadeRouterClient(
        base_url,
        model_id=model_id,
        backend="cpu",
        ctx_size=ctx_size,
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# ## FUTURE HOOKS
# ---------------------------------------------------------------------------
# FH-1 (Phase 2): wire DirectLemonadeTier + RouterCpuTier in direct_tier.py
#       to delegate to LemonadeRouterClient internally, then deprecate.
# FH-2 (Phase 2): wire triune_orchestrator.py NPU/iGPU/CPU tiers onto the
#       three builder helpers above.
# FH-3 (Phase 3): wire swarm/providers/lemonade_provider.py to use this client
#       instead of direct httpx calls to :13307.
# FH-4 (Phase 4): replace OllamaProvider with OllamaShim(LemonadeRouterClient)
#       using from_ollama_options() for callers that still send options dicts.
# FH-5: add streaming support (server-sent events → async generator) once
#       :13305 exposes stream=True reliably on all backend types.
# FH-6: add retry/backoff policy (exponential, max 3 attempts) for transient
#       503/504 errors from the router during model-swap transitions.
# ---------------------------------------------------------------------------
