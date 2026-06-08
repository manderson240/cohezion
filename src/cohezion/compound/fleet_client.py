"""LemonadeRouterClient — unified HTTP client for the :13305 Lemonade router.

Routes inference requests to any loaded model by name; the router dispatches
to the correct device (NPU/iGPU/GPU/CPU) internally.  Replaces per-device
port management (13306/13307/13309) with a single router endpoint.

Three public building blocks
────────────────────────────
* ``LemonadeRouterClient``  — synchronous HTTP wrapper (health, chat, load, unload).
* ``RouterLemonadeTier``    — async drop-in for ``TieredOrchestrator`` that speaks
                              to the router instead of a per-device port.
* ``fleet_review()``        — one-shot multi-tier review: dispatches the same prompt
                              to NPU + iGPU + CPU and returns a ``FleetReviewResult``.

## FUTURE HOOKS
- ``RouterLemonadeTier`` could expose ``cost_usd`` once budget-enforcement is
  plumbed through ``LemonadeRouterClient.chat``.
- ``fleet_review()`` could accept an ``on_tier_complete`` callback for streaming
  progressive results back to the caller.
- ``LemonadeRouterClient.load/unload`` lifecycle could be wrapped in a context
  manager for guaranteed cleanup of on-demand CPU models.
- Health polling could feed into ``DegradationDetector`` for router-level
  health metrics (model swap latency, queue depth from ``max_models``).
"""

from __future__ import annotations

import logging
import time
import urllib.request
from dataclasses import dataclass
from json import dumps as _json_dumps
from json import loads as _json_loads

from cohezion.inference.orchestrator import OrchestrationResult


logger = logging.getLogger(__name__)

# Models that require the /no_think system prompt in llamacpp (Qwen3 thinking-mode
# models will consume the entire max_tokens budget on reasoning_content otherwise).
_NO_THINK_MODELS = frozenset(
    {
        "Qwen3-0.6B-GGUF",
        "Qwen3-8B-GGUF",
        "Qwen3-14B-GGUF",
        "Qwen3.5-35B-A3B-GGUF",
        "Qwen3.5-4B-MTP-GGUF",
    }
)

# Device tier preference order — lower index = preferred tier.
_DEVICE_TIER_ORDER = ["npu", "gpu", "vulkan", "cpu"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouterModelInfo:
    """One loaded model as reported by GET /api/v1/health."""

    model_name: str
    device: str  # "npu" | "gpu" | "cpu" | "vulkan"
    backend_url: str
    pid: int = 0


@dataclass
class TierResult:
    """Result from a single device tier in a fleet review."""

    tier: str  # "npu" | "igpu" | "cpu"
    model: str
    device: str
    latency_ms: int
    text: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        """True when inference completed without error and produced non-empty text."""
        return self.error is None and bool(self.text)


@dataclass
class FleetReviewResult:
    """Aggregated results from a tri-tier fleet review pass."""

    npu: TierResult | None = None
    igpu: TierResult | None = None
    cpu: TierResult | None = None
    # Optional on-demand CPU load/unload times (ms)
    cpu_load_ms: int = 0
    cpu_unload_ms: int = 0

    @property
    def tiers(self) -> list[TierResult]:
        return [t for t in (self.npu, self.igpu, self.cpu) if t is not None]

    @property
    def succeeded_count(self) -> int:
        return sum(1 for t in self.tiers if t.ok)

    @property
    def failed_tiers(self) -> list[str]:
        return [t.tier for t in self.tiers if not t.ok]

    def summary(self) -> str:
        lines = [f"Fleet review: {self.succeeded_count}/{len(self.tiers)} tiers succeeded"]
        for t in self.tiers:
            status = "OK" if t.ok else f"FAIL({t.error})"
            lines.append(f"  {t.tier:6s} {t.model} [{t.device}] {t.latency_ms}ms — {status}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LemonadeRouterClient
# ---------------------------------------------------------------------------


class LemonadeRouterClient:
    """Thin synchronous HTTP wrapper around the Lemonade unified router.

    Uses the Lemonade native API (``/api/v1/``), not the OpenAI-compat alias
    (``/v1/``), to access management endpoints (health, load, unload).
    Inference uses ``/api/v1/chat/completions`` with ``{"model": name, ...}``.

    Parameters
    ----------
    port:
        Router port — default 13305 (the unified Lemonade router).
    timeout_s:
        Per-request timeout in seconds.  Inference calls may take longer;
        the ``chat()`` method accepts a per-call override.
    """

    def __init__(self, port: int = 13305, *, timeout_s: float = 30.0) -> None:
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.api_url = f"{self.base_url}/api/v1"
        self.timeout_s = timeout_s

    # ------------------------------------------------------------------
    # Availability / discovery
    # ------------------------------------------------------------------

    def available(self, timeout_s: float = 2.0) -> bool:
        """Non-blocking probe — True when the router is reachable."""
        try:
            urllib.request.urlopen(f"{self.api_url}/health", timeout=timeout_s)
            return True
        except Exception:
            return False

    def health(self) -> dict:
        """GET /api/v1/health → raw JSON dict."""
        with urllib.request.urlopen(f"{self.api_url}/health", timeout=self.timeout_s) as r:
            return _json_loads(r.read())

    def hot_models(self) -> list[RouterModelInfo]:
        """Return currently loaded models, sorted by tier preference (NPU first)."""
        h = self.health()
        models = [
            RouterModelInfo(
                model_name=m["model_name"],
                device=m.get("device", "unknown"),
                backend_url=m.get("backend_url", ""),
                pid=m.get("pid", 0),
            )
            for m in h.get("all_models_loaded", [])
        ]

        def _tier_rank(m: RouterModelInfo) -> int:
            d = m.device.lower()
            for i, prefix in enumerate(_DEVICE_TIER_ORDER):
                if d.startswith(prefix):
                    return i
            return len(_DEVICE_TIER_ORDER)

        return sorted(models, key=_tier_rank)

    def find_model(self, name: str) -> RouterModelInfo | None:
        """Return model info if ``name`` is currently hot, else None."""
        for m in self.hot_models():
            if m.model_name == name:
                return m
        return None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        max_tokens: int = 512,
        temperature: float = 0.0,
        timeout_s: float | None = None,
    ) -> tuple[str, int]:
        """POST /api/v1/chat/completions.

        Returns
        -------
        (text, latency_ms)
            ``text`` is the assistant message content (stripped); ``latency_ms``
            is wall-clock time for the round-trip.

        Notes
        -----
        Thinking-mode Qwen3 models (``_NO_THINK_MODELS``) automatically receive
        a ``/no_think`` system message prepended to suppress chain-of-thought and
        prevent the reasoning tokens from consuming the entire ``max_tokens`` budget.
        """
        # Prepend /no_think for Qwen3 thinking-mode models (see direct_tier._NO_THINK_MODELS).
        if model in _NO_THINK_MODELS:
            messages = [{"role": "system", "content": "/no_think"}, *messages]

        payload = _json_dumps(
            {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.api_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout_s or self.timeout_s) as r:
                body = _json_loads(r.read())
            latency_ms = int((time.time() - t0) * 1000)
            text = body["choices"][0]["message"]["content"].strip()
            return text, latency_ms
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            raise RuntimeError(
                f"LemonadeRouterClient.chat({model}@:{self.port}) failed after {latency_ms}ms: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def load(
        self,
        model_name: str,
        *,
        ctx_size: int = 4096,
        backend: str = "cpu",
        timeout_s: float | None = None,
    ) -> dict:
        """POST /api/v1/load — load ``model_name`` on ``backend`` (cpu|vulkan|rocm).

        OOM note: prefer small models for on-demand CPU loads (≤1B params).
        Always call ``unload()`` when done.
        """
        payload = _json_dumps(
            {"model_name": model_name, "ctx_size": ctx_size, "llamacpp_backend": backend}
        ).encode()
        req = urllib.request.Request(
            f"{self.api_url}/load",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout_s or self.timeout_s) as r:
            return _json_loads(r.read())

    def unload(self, model_name: str, *, timeout_s: float | None = None) -> dict:
        """POST /api/v1/unload — unload ``model_name`` to free device memory."""
        payload = _json_dumps({"model_name": model_name}).encode()
        req = urllib.request.Request(
            f"{self.api_url}/unload",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout_s or self.timeout_s) as r:
            return _json_loads(r.read())


# ---------------------------------------------------------------------------
# RouterLemonadeTier — async tier for TieredOrchestrator
# ---------------------------------------------------------------------------


class RouterLemonadeTier:
    """Async tier that dispatches through ``LemonadeRouterClient`` by model name.

    Drop-in replacement for ``DirectLemonadeTier`` for use with
    ``TieredOrchestrator``.  Routes via the unified :13305 router instead of
    a per-device port — the router selects the correct physical device.

    Parameters
    ----------
    router:
        A ``LemonadeRouterClient`` instance (typically sharing the session singleton).
    model_id:
        Model name to request (must be loaded on the router).
    max_tokens:
        Generation budget.
    temperature:
        Sampling temperature.
    """

    def __init__(
        self,
        router: LemonadeRouterClient,
        model_id: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        self.router = router
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.label = f"router:{model_id}@:{router.port}"

    async def run(self, prompt: str, **_: object) -> OrchestrationResult:
        """Dispatch ``prompt`` to the router, return an ``OrchestrationResult``."""
        import asyncio

        loop = asyncio.get_event_loop()
        text = ""
        error: str | None = None
        latency_ms = 0.0

        try:
            # Router client is synchronous; run in a thread to avoid blocking the loop.
            text, latency_ms = await loop.run_in_executor(
                None,
                lambda: self.router.chat(
                    self.model_id,
                    [{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                ),
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.debug("RouterLemonadeTier %s: %s", self.model_id, error)

        return OrchestrationResult(
            text=text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,
            latency_ms=float(latency_ms),
            ttft_ms=None,
            error=error,
        )


# ---------------------------------------------------------------------------
# fleet_review() — one-shot tri-tier review
# ---------------------------------------------------------------------------


def fleet_review(
    prompt: str,
    *,
    npu_model: str = "llama3.2-1b-FLM",
    igpu_model: str = "Granite-4.1-8B-GGUF",
    cpu_model: str = "Qwen3-0.6B-GGUF",
    max_tokens: int = 300,
    router_port: int = 13305,
    cpu_backend: str = "cpu",
    cpu_ctx_size: int = 4096,
) -> FleetReviewResult:
    """Dispatch ``prompt`` to NPU, iGPU, and CPU via the :``router_port`` router.

    The CPU model is loaded on-demand and unloaded after inference (OOM-safe).
    NPU and iGPU models are assumed to be already hot on the router.

    Parameters
    ----------
    prompt:
        The review/analysis prompt to send to each tier.
    npu_model:
        Model name to use for the NPU tier (must be hot).
    igpu_model:
        Model name to use for the iGPU tier (must be hot).
    cpu_model:
        Model name to load on-demand for the CPU tier (small ≤1B recommended).
    max_tokens:
        Token budget per tier.
    router_port:
        Lemonade router port (default 13305).
    cpu_backend:
        llamacpp backend for the on-demand CPU model ("cpu"|"vulkan"|"rocm").
    cpu_ctx_size:
        Context window size for the on-demand CPU model.

    Returns
    -------
    FleetReviewResult
        Per-tier ``TierResult`` instances.  ``error`` is set (not raised) when a
        tier is unreachable or returns empty.
    """
    router = LemonadeRouterClient(port=router_port)
    result = FleetReviewResult()

    messages = [{"role": "user", "content": prompt}]

    # --- NPU tier ---
    npu_info = router.find_model(npu_model)
    if npu_info is not None:
        try:
            text, lat = router.chat(npu_model, messages, max_tokens=max_tokens, temperature=0.0)
            result.npu = TierResult(
                tier="npu", model=npu_model, device=npu_info.device, latency_ms=lat, text=text
            )
        except Exception as exc:
            result.npu = TierResult(
                tier="npu",
                model=npu_model,
                device=npu_info.device,
                latency_ms=0,
                text="",
                error=str(exc),
            )
    else:
        result.npu = TierResult(
            tier="npu",
            model=npu_model,
            device="npu",
            latency_ms=0,
            text="",
            error=f"{npu_model} not loaded on router",
        )
        logger.warning("fleet_review: NPU model %s not found on router :%d", npu_model, router_port)

    # --- iGPU tier ---
    igpu_info = router.find_model(igpu_model)
    if igpu_info is not None:
        try:
            text, lat = router.chat(igpu_model, messages, max_tokens=max_tokens, temperature=0.0)
            result.igpu = TierResult(
                tier="igpu", model=igpu_model, device=igpu_info.device, latency_ms=lat, text=text
            )
        except Exception as exc:
            result.igpu = TierResult(
                tier="igpu",
                model=igpu_model,
                device=igpu_info.device,
                latency_ms=0,
                text="",
                error=str(exc),
            )
    else:
        result.igpu = TierResult(
            tier="igpu",
            model=igpu_model,
            device="gpu",
            latency_ms=0,
            text="",
            error=f"{igpu_model} not loaded on router",
        )
        logger.warning(
            "fleet_review: iGPU model %s not found on router :%d", igpu_model, router_port
        )

    # --- CPU tier (on-demand load → infer → unload) ---
    cpu_loaded = False
    load_ms = 0
    unload_ms = 0
    cpu_device = "cpu"
    try:
        t_load = time.time()
        load_resp = router.load(cpu_model, ctx_size=cpu_ctx_size, backend=cpu_backend)
        load_ms = int((time.time() - t_load) * 1000)
        cpu_loaded = True
        logger.debug("fleet_review: loaded %s in %dms (resp=%s)", cpu_model, load_ms, load_resp)
    except Exception as exc:
        result.cpu = TierResult(
            tier="cpu",
            model=cpu_model,
            device="cpu",
            latency_ms=0,
            text="",
            error=f"load failed: {exc}",
        )

    if cpu_loaded:
        cpu_info = router.find_model(cpu_model)
        cpu_device = cpu_info.device if cpu_info else "cpu"
        try:
            text, lat = router.chat(cpu_model, messages, max_tokens=max_tokens, temperature=0.0)
            result.cpu = TierResult(
                tier="cpu", model=cpu_model, device=cpu_device, latency_ms=lat, text=text
            )
        except Exception as exc:
            result.cpu = TierResult(
                tier="cpu",
                model=cpu_model,
                device=cpu_device,
                latency_ms=0,
                text="",
                error=str(exc),
            )
        # Always unload (OOM discipline)
        try:
            t_unload = time.time()
            router.unload(cpu_model)
            unload_ms = int((time.time() - t_unload) * 1000)
            logger.debug("fleet_review: unloaded %s in %dms", cpu_model, unload_ms)
        except Exception as exc:
            logger.warning("fleet_review: unload %s failed: %s", cpu_model, exc)

    result.cpu_load_ms = load_ms
    result.cpu_unload_ms = unload_ms
    return result
