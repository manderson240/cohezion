"""Lemonade OmniRouter recipe-aware health probe (stub).

Exports the types and functions consumed by:
  - tests/inference/test_lemonade_health.py
  - tests/inference/test_fleet_recipe_gate.py
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


_LLM_RECIPES: frozenset[str] = frozenset({"llamacpp", "vllm", "flm"})

_RECIPE_ENDPOINTS: dict[str, str] = {
    "llamacpp": "/v1/models",
    "kokoro": "/v1/audio/voices",
    "sd-cpp": "/v1/images/generations",
    "whispercpp": "/v1/audio/transcriptions",
}

_DEFAULT_PROBE_RECIPES: list[str] = ["llamacpp", "kokoro", "sd-cpp", "whispercpp"]


@dataclass
class CtxHazard:
    """A model loaded with ctx_size=0 — a potential OOM crasher."""

    model: str
    recipe: str
    ctx_size: int
    backend_url: str
    pid: int

    def __str__(self) -> str:
        return f"CtxHazard(model={self.model!r}, ctx_size={self.ctx_size}, pid={self.pid})"


@dataclass
class OrphanProcess:
    """A lemonade backend process with no matching loaded model."""

    model: str
    pid: int
    backend_url: str

    def __str__(self) -> str:
        return f"OrphanProcess(model={self.model!r}, pid={self.pid})"


@dataclass
class TypeHeadroom:
    """Slot headroom for a model type (e.g. 'llm', 'image')."""

    type: str
    loaded: int
    max_: int

    @property
    def free(self) -> int:
        return self.max_ - self.loaded

    @property
    def saturated(self) -> bool:
        return self.free <= 0

    def __str__(self) -> str:
        state = "SATURATED" if self.saturated else "ok"
        return f"TypeHeadroom(type={self.type!r}, loaded={self.loaded}/{self.max_}, {state})"


@dataclass
class RecipeProbe:
    """Result of probing a single lemonade recipe endpoint."""

    recipe: str
    ok: bool
    latency_ms: float
    detail: str = ""

    def __str__(self) -> str:
        if self.ok:
            return f"{self.recipe}=ok({self.latency_ms:.0f}ms) {self.detail}"
        return f"{self.recipe}=DOWN({self.detail})"


@dataclass
class LemonadeHealth:
    """Snapshot of OmniRouter (:13305) health."""

    checked_at: float
    port: int
    version: str
    status: str
    loaded_count: int
    recipe_probes: list[RecipeProbe] = field(default_factory=list)
    headroom: list[TypeHeadroom] = field(default_factory=list)
    ctx_hazards: list[CtxHazard] = field(default_factory=list)
    orphan_processes: list[OrphanProcess] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    @property
    def recipes_up(self) -> list[str]:
        return [p.recipe for p in self.recipe_probes if p.ok]

    @property
    def recipes_down(self) -> list[str]:
        return [p.recipe for p in self.recipe_probes if not p.ok]

    @property
    def has_ctx_hazards(self) -> bool:
        return len(self.ctx_hazards) > 0

    @property
    def ok(self) -> bool:
        return self.status == "ok" and not self.ctx_hazards

    @property
    def summary(self) -> str:
        up = ",".join(self.recipes_up) if self.recipes_up else "none"
        down = ",".join(self.recipes_down) if self.recipes_down else "none"
        return (
            f"v{self.version} port={self.port} status={self.status} "
            f"loaded={self.loaded_count} "
            f"recipes_up={up} recipes_down={down} "
            f"ctx_hazards={len(self.ctx_hazards)} "
            f"orphans={len(self.orphan_processes)}"
        )


async def is_lemonade_alive(port: int = 13305, timeout: float = 1.0) -> bool:
    """Return True when the OmniRouter HTTP endpoint is reachable."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"http://localhost:{port}/v1/models")
            return resp.status_code < 500
    except Exception:
        return False


async def probe_lemonade(
    port: int = 13305,
    timeout: float = 5.0,
    probe_recipes: list[str] | None = None,
) -> LemonadeHealth:
    """Probe the OmniRouter and return a full health snapshot."""
    recipes = probe_recipes if probe_recipes is not None else list(_DEFAULT_PROBE_RECIPES)
    t0 = time.monotonic()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                health_resp = await client.get(f"http://localhost:{port}/api/v1/health")
                if health_resp.status_code >= 500:
                    raise RuntimeError(f"HTTP {health_resp.status_code}")
                health_payload = health_resp.json()
            except Exception as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                return LemonadeHealth(
                    checked_at=time.time(),
                    port=port,
                    version="?",
                    status="down",
                    loaded_count=0,
                    recipe_probes=[],
                    headroom=[],
                    errors=[f"unreachable: {exc}"],
                    latency_ms=latency_ms,
                )

            version = health_payload.get("version", "?")
            status = health_payload.get("status", "ok")
            loaded_models = health_payload.get("all_models_loaded", [])
            max_models = health_payload.get("max_models", {})

            recipe_probes: list[RecipeProbe] = []
            for recipe in recipes:
                endpoint = _RECIPE_ENDPOINTS.get(recipe)
                if endpoint is None:
                    continue
                url = f"http://localhost:{port}{endpoint}"
                probe_t0 = time.monotonic()
                try:
                    resp = await client.get(url)
                    latency = (time.monotonic() - probe_t0) * 1000
                    ok = resp.status_code < 500
                    recipe_probes.append(
                        RecipeProbe(
                            recipe=recipe,
                            ok=ok,
                            latency_ms=latency,
                            detail=f"HTTP {resp.status_code}",
                        )
                    )
                except Exception as exc:
                    latency = (time.monotonic() - probe_t0) * 1000
                    recipe_probes.append(
                        RecipeProbe(
                            recipe=recipe,
                            ok=False,
                            latency_ms=latency,
                            detail=str(exc),
                        )
                    )

            ctx_hazards = await _check_ctx_hazards(loaded_models)
            orphans = await _check_orphans(loaded_models)

            for h in ctx_hazards:
                warnings.append(f"ctx_size<=0 on {h.model}")

            headroom: list[TypeHeadroom] = []
            loaded_by_type: dict[str, int] = {}
            for m in loaded_models:
                mtype = m.get("type", "llm")
                loaded_by_type[mtype] = loaded_by_type.get(mtype, 0) + 1
            for mtype, max_count in max_models.items():
                headroom.append(
                    TypeHeadroom(
                        type=mtype,
                        loaded=loaded_by_type.get(mtype, 0),
                        max_=max_count,
                    )
                )

            latency_ms = (time.monotonic() - t0) * 1000
            return LemonadeHealth(
                checked_at=time.time(),
                port=port,
                version=version,
                status=status,
                loaded_count=len(loaded_models),
                recipe_probes=recipe_probes,
                headroom=headroom,
                ctx_hazards=ctx_hazards,
                orphan_processes=orphans,
                warnings=warnings,
                errors=errors,
                latency_ms=latency_ms,
            )
    except Exception as exc:
        latency_ms = (time.monotonic() - t0) * 1000
        return LemonadeHealth(
            checked_at=time.time(),
            port=port,
            version="?",
            status="down",
            loaded_count=0,
            recipe_probes=[],
            headroom=[],
            errors=[f"unreachable: {exc}"],
            latency_ms=latency_ms,
        )


async def _check_ctx_hazards(models_payload: Any) -> list[CtxHazard]:
    """Extract ctx_size=0 hazards from the /api/v1/models response payload."""
    if not isinstance(models_payload, list):
        return []
    hazards: list[CtxHazard] = []
    for m in models_payload:
        recipe = m.get("recipe", "")
        if recipe not in _LLM_RECIPES:
            continue
        opts = m.get("recipe_options", {})
        if not isinstance(opts, dict):
            continue
        ctx_size = opts.get("ctx_size")
        if ctx_size == 0:
            hazards.append(
                CtxHazard(
                    model=m.get("model_name", "?"),
                    recipe=recipe,
                    ctx_size=0,
                    backend_url=m.get("backend_url", ""),
                    pid=m.get("pid", 0),
                )
            )
    return hazards


async def _check_orphans(models_payload: Any) -> list[OrphanProcess]:
    """Detect orphaned backend processes from the /api/v1/models response payload."""
    if not isinstance(models_payload, list):
        return []
    orphans: list[OrphanProcess] = []
    seen_pids: dict[int, str] = {}
    for m in models_payload:
        pid = m.get("pid", 0)
        name = m.get("model_name", "?")
        url = m.get("backend_url", "")
        if pid <= 0:
            orphans.append(OrphanProcess(model=name, pid=pid, backend_url=url))
        elif pid in seen_pids:
            orphans.append(
                OrphanProcess(
                    model=f"{name}(dup:{pid})",
                    pid=pid,
                    backend_url=url,
                )
            )
        else:
            seen_pids[pid] = name
    return orphans