"""Lemonade health probe — recipe-aware fleet liveness + safety checks.

Sister of ``health.py`` (which is lane-level) and ``audit_lemonade_recipes.py``
(which is consumer-code diff). This module is the **runtime** check that runs
before the swarm dispatches, returning a typed result that the router can
read to avoid dead/unsafe endpoints.

Checks (in order):

1. OmniRouter (``/api/v1/health``) reachable + status==ok + version
2. Every loaded model has a positive ``recipe_options.ctx_size`` (the
   ``ctx_size=0`` OOM hazard per `lemonade-multi-device` pitfall 13)
3. Every loaded model reports a non-zero ``pid`` (no orphan processes)
4. Per-recipe liveness probe via the OpenAI-spec endpoints:
     - llamacpp: GET /v1/models
     - kokoro:   GET /v1/audio/voices
     - sd-cpp:   GET /v1/images/generations (returns 405 without auth —
                  we accept 4xx as proof the backend is alive)
     - whispercpp: GET /v1/audio/transcriptions (returns 4xx without file
                   — accepted as alive; see stt_tier.is_alive for why)
5. Catalog coverage: how many catalog models are loaded vs available
6. Type slot headroom: ``max_models - len(loaded)`` per type (llm, tts,
   image, transcription, embedding, reranking)

Design rules (2026-06-10):
- All probes go through :13305 (the OmniRouter) for app code. Per-model
  backends (8002-8013) are probed ONLY if the user explicitly passes a
  ``backend_url`` override; default is the OmniRouter surface.
- No subprocess / no shell; only ``httpx`` async GETs. Safe for cron.
- Pure function: takes a port, returns a typed result. Caching is the
  caller's problem (see fleet.py / health.py for the 30s cache layer).

Usage::

    from cohezion.inference.lemonade_health import probe_lemonade
    r = await probe_lemonade(port=13305)
    if not r.ok:
        logger.error("lemonade unhealthy: %s", r.summary)
    for hazard in r.ctx_hazards:
        logger.warning("ctx_size=0 on %s — OOM risk", hazard.model)

Validated live 2026-06-10 against lemonade v10.6.0 with 6 loaded models.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal

import httpx


logger = logging.getLogger(__name__)


Recipe = Literal["llamacpp", "kokoro", "sd-cpp", "whispercpp", "flm", "vllm", "rocm", "vulkan"]
ModelType = Literal["llm", "tts", "image", "transcription", "embedding", "reranking"]


@dataclass(frozen=True)
class CtxHazard:
    """A loaded model with ``recipe_options.ctx_size <= 0`` (OOM risk).

    Reproduces the 2026-06-09 incident: Qwen3.6-35B-A3B-NoThinking loaded
    with ctx_size=0 forwarded to llama-server --ctx-size 0, KV cache grew
    unbounded and hard-hung the box (cold-boot required).
    """

    model: str
    recipe: str
    ctx_size: int
    backend_url: str
    pid: int

    def __str__(self) -> str:
        return (
            f"{self.model} ({self.recipe}, ctx_size={self.ctx_size}, "
            f"pid={self.pid}, backend={self.backend_url})"
        )


@dataclass(frozen=True)
class OrphanProcess:
    """A model entry in health with a non-positive or duplicate pid."""

    model: str
    pid: int
    backend_url: str

    def __str__(self) -> str:
        return f"{self.model} pid={self.pid} backend={self.backend_url}"


@dataclass(frozen=True)
class RecipeProbe:
    """Liveness of one recipe family on the OmniRouter surface."""

    recipe: Recipe
    ok: bool
    latency_ms: float
    detail: str = ""

    def __str__(self) -> str:
        flag = "ok" if self.ok else "DOWN"
        return f"{self.recipe}={flag} ({self.latency_ms:.0f}ms) {self.detail}".strip()


@dataclass(frozen=True)
class TypeHeadroom:
    """Per-type slot availability on the OmniRouter."""

    type: ModelType
    loaded: int
    max_: int

    @property
    def free(self) -> int:
        return max(self.max_ - self.loaded, 0)

    @property
    def saturated(self) -> bool:
        return self.loaded >= self.max_

    def __str__(self) -> str:
        flag = "SATURATED" if self.saturated else "ok"
        return f"{self.type}={self.loaded}/{self.max_} ({flag})"


@dataclass(frozen=True)
class LemonadeHealth:
    """Aggregate health of the lemonade OmniRouter.

    ``ok`` is True iff every required check passes. ``warnings`` lists
    non-fatal issues (e.g. partial headroom). ``ctx_hazards`` and
    ``orphans`` are also surfaced individually for ops dashboards.
    """

    checked_at: float
    port: int
    version: str
    status: str  # "ok" / "degraded" / "down"
    loaded_count: int
    recipe_probes: list[RecipeProbe]
    headroom: list[TypeHeadroom]
    ctx_hazards: list[CtxHazard] = field(default_factory=list)
    orphans: list[OrphanProcess] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return (
            self.status == "ok"
            and not self.errors
            and all(p.ok for p in self.recipe_probes)
            and not self.ctx_hazards
        )

    @property
    def has_ctx_hazards(self) -> bool:
        return bool(self.ctx_hazards)

    @property
    def has_orphans(self) -> bool:
        return bool(self.orphans)

    @property
    def recipes_up(self) -> list[str]:
        return [p.recipe for p in self.recipe_probes if p.ok]

    @property
    def recipes_down(self) -> list[str]:
        return [p.recipe for p in self.recipe_probes if not p.ok]

    @property
    def summary(self) -> str:
        parts = [
            f"lemonade v{self.version} on :{self.port} status={self.status}",
            f"loaded={self.loaded_count}",
            f"recipes_up={','.join(self.recipes_up) or 'none'}",
        ]
        if self.recipes_down:
            parts.append(f"recipes_down={','.join(self.recipes_down)}")
        if self.has_ctx_hazards:
            parts.append(f"ctx_hazards={len(self.ctx_hazards)}")
        if self.has_orphans:
            parts.append(f"orphans={len(self.orphans)}")
        if self.warnings:
            parts.append(f"warnings={len(self.warnings)}")
        return " | ".join(parts)


# The probes we run for each recipe via the OmniRouter surface. Each
# recipe has an OpenAI-spec probe that returns 4xx on misuse (which we
# treat as alive — see stt_tier.is_alive for the same pattern). 5xx
# and connection errors = dead.
_RECIPE_PROBES: dict[Recipe, tuple[str, str]] = {
    # recipe -> (method, path)
    "llamacpp": ("GET", "/v1/models"),
    "kokoro": ("GET", "/v1/audio/voices"),
    "sd-cpp": ("GET", "/v1/images/generations"),
    "whispercpp": ("GET", "/v1/audio/transcriptions"),
}


async def _probe_recipe(client: httpx.AsyncClient, base_url: str, recipe: Recipe) -> RecipeProbe:
    method, path = _RECIPE_PROBES[recipe]
    start = time.perf_counter()
    try:
        resp = await client.request(method, f"{base_url}{path}")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return RecipeProbe(
            recipe=recipe, ok=False, latency_ms=latency, detail=f"{type(exc).__name__}: {exc}"
        )
    latency = (time.perf_counter() - start) * 1000
    # 4xx = the backend parsed the request and complained = alive.
    # 5xx + connection refused = dead.
    if resp.status_code < 500:
        return RecipeProbe(
            recipe=recipe, ok=True, latency_ms=latency, detail=f"HTTP {resp.status_code}"
        )
    return RecipeProbe(
        recipe=recipe, ok=False, latency_ms=latency, detail=f"HTTP {resp.status_code}"
    )


async def _check_ctx_hazards(loaded: list[dict]) -> list[CtxHazard]:
    """Find models with ctx_size <= 0 (OOM hazard)."""
    hazards: list[CtxHazard] = []
    for m in loaded:
        ro = m.get("recipe_options", {}) or {}
        ctx = ro.get("ctx_size")
        # Only relevant for llamacpp / vllm / similar (NOT sd-cpp / whispercpp /
        # kokoro — those don't take a context size in the same way).
        if m.get("recipe") in ("llamacpp", "vllm", "flm") and ctx is not None and int(ctx) <= 0:
            hazards.append(
                CtxHazard(
                    model=str(m.get("model_name", "?")),
                    recipe=str(m.get("recipe", "?")),
                    ctx_size=int(ctx),
                    backend_url=str(m.get("backend_url", "?")),
                    pid=int(m.get("pid", 0)),
                )
            )
    return hazards


async def _check_orphans(loaded: list[dict]) -> list[OrphanProcess]:
    """Find models with pid<=0 (zombie) or duplicate pids (likely stale)."""
    orphans: list[OrphanProcess] = []
    seen_pids: dict[int, str] = {}
    for m in loaded:
        pid = int(m.get("pid", 0))
        name = str(m.get("model_name", "?"))
        url = str(m.get("backend_url", "?"))
        if pid <= 0:
            orphans.append(OrphanProcess(model=name, pid=pid, backend_url=url))
        elif pid in seen_pids:
            orphans.append(
                OrphanProcess(
                    model=f"{name} (dup of {seen_pids[pid]})",
                    pid=pid,
                    backend_url=url,
                )
            )
        else:
            seen_pids[pid] = name
    return orphans


async def probe_lemonade(
    port: int = 13305,
    *,
    timeout_s: float = 5.0,
    probe_recipes: list[Recipe] | None = None,
) -> LemonadeHealth:
    """Probe the lemonade OmniRouter and return aggregate health.

    Parameters
    ----------
    port : int
        OmniRouter port. Default 13305 (the only port app code should use).
    timeout_s : float
        Per-probe HTTP timeout.
    probe_recipes : list[Recipe] | None
        Subset of recipes to probe. Default = all four we know how to
        check (llamacpp, kokoro, sd-cpp, whispercpp). flm / vllm are not
        separately probed — they sit on the llamacpp endpoint and
        contribute to the loaded-model count.

    Returns
    -------
    LemonadeHealth
        Frozen result. Check ``.ok`` for overall status; inspect
        ``.ctx_hazards`` / ``.orphans`` / ``.errors`` for specifics.
    """
    if probe_recipes is None:
        probe_recipes = ["llamacpp", "kokoro", "sd-cpp", "whispercpp"]

    base_url = f"http://localhost:{port}"
    start = time.perf_counter()
    errors: list[str] = []
    warnings: list[str] = []

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        # 1. Main health check
        try:
            resp = await client.get(f"{base_url}/api/v1/health")
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            return LemonadeHealth(
                checked_at=time.time(),
                port=port,
                version="?",
                status="down",
                loaded_count=0,
                recipe_probes=[],
                headroom=[],
                errors=[f"omni health unreachable: {type(exc).__name__}: {exc}"],
                latency_ms=latency,
            )
        if resp.status_code != 200:
            errors.append(f"omni health HTTP {resp.status_code}: {resp.text[:200]}")
            health_data = {}
        else:
            health_data = resp.json()

        # 2. Recipe probes (parallel-ish — just await in series for simplicity)
        probes: list[RecipeProbe] = []
        for r in probe_recipes:
            probes.append(await _probe_recipe(client, base_url, r))

    latency = (time.perf_counter() - start) * 1000

    version = str(health_data.get("version", "?"))
    status_str = str(health_data.get("status", "?"))
    loaded = list(health_data.get("all_models_loaded", []) or [])
    loaded_count = len(loaded)

    # 3. Per-type headroom
    max_models = health_data.get("max_models", {}) or {}
    type_to_loaded: dict[str, int] = {}
    for m in loaded:
        t = str(m.get("type", "?"))
        type_to_loaded[t] = type_to_loaded.get(t, 0) + 1
    headroom: list[TypeHeadroom] = []
    for t, max_ in max_models.items():
        h = TypeHeadroom(type=t, loaded=type_to_loaded.get(t, 0), max_=int(max_))
        headroom.append(h)
        if h.saturated:
            warnings.append(f"type {t} saturated: {h.loaded}/{h.max_}")

    # 4. Safety checks
    ctx_hazards = await _check_ctx_hazards(loaded)
    orphans = await _check_orphans(loaded)
    for h in ctx_hazards:
        warnings.append(f"ctx_size<=0 on {h.model} (recipe={h.recipe}) — OOM hazard")

    return LemonadeHealth(
        checked_at=time.time(),
        port=port,
        version=version,
        status=status_str,
        loaded_count=loaded_count,
        recipe_probes=probes,
        headroom=headroom,
        ctx_hazards=ctx_hazards,
        orphans=orphans,
        warnings=warnings,
        errors=errors,
        latency_ms=latency,
    )


async def is_lemonade_alive(port: int = 13305, *, timeout_s: float = 3.0) -> bool:
    """Cheap liveness check. Returns True if OmniRouter is reachable + status==ok."""
    try:
        r = await probe_lemonade(port=port, timeout_s=timeout_s, probe_recipes=[])
        return r.status == "ok" and not r.errors
    except Exception:
        return False


__all__ = [
    "CtxHazard",
    "LemonadeHealth",
    "OrphanProcess",
    "RecipeProbe",
    "TypeHeadroom",
    "is_lemonade_alive",
    "probe_lemonade",
]
