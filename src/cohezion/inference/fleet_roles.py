"""Adaptive, live-catalog role→model selection for the local inference fleet.

Why this exists
---------------
The package's existing selectors (``route_by_capability`` / ``fleet_routing_specialist``
/ ``local_fleet`` / ``omni_model``) are all STATIC: they pick from a hardcoded
registry (Task enum + priority) and query the live :13305 catalog only for
*metadata* (size/ctx/vision) — never to decide *which* model fills a role. So when
a model is installed or removed, or a stronger model appears under a new name, they
don't adapt.

This module adds what they lacked: pick the best model for a ROLE **from the live
catalog right now**, ranked by the catalog's own capability ``labels`` + size band,
with the freeze-prevention load guard applied to heavy roles. It is the package home
for the logic prototyped (and adversarially reviewed) in the standalone
``cohezion-labs/fleet_roster.py`` — daemons should import ``ROSTER`` from here.

Separation of concerns: this module SELECTS; ``load_safety`` GUARDS. The heavy-role
fit check calls ``load_safety.check_load_safe`` — the single source of truth for
"does this model's footprint fit available RAM" — rather than reimplementing it.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field

from cohezion.inference.load_safety import (
    available_ram_gb,
    check_load_safe,
    effective_size_gb,
)


logger = logging.getLogger(__name__)

BASE = "http://localhost:13305"
SURREAL = "http://localhost:8001/sql"
_CACHE_TTL_S = 30.0


@dataclass
class RoleSpec:
    """How to choose a model for one role, from live catalog metadata."""

    require: tuple[str, ...] = ()        # labels ALL required (AND)
    prefer: tuple[str, ...] = ()         # labels that add rank score (OR)
    name_hint: tuple[str, ...] = ()      # id substrings that add rank score
    exclude: tuple[str, ...] = ()        # id substrings to reject
    size_min: float = 0.0                # GB, inclusive
    size_max: float = 999.0             # GB, inclusive
    bigger_is_better: bool = True        # size as quality proxy when labels tie
    heavy: bool = False                  # apply RAM-fit guard on select(loadable=True)


# Role -> selection policy. Capability-driven, NOT hardcoded model IDs.
ROLE_SPECS: dict[str, RoleSpec] = {
    "interactive": RoleSpec(
        prefer=("mtp", "tool-calling", "reasoning"),
        name_hint=("A3B", "MTP", "Qwen3.6"),
        exclude=("Embedding", "embed", "FLM", "Bonsai-1", "0.6B"),
        size_min=8.0, size_max=45.0,
    ),
    "bbq": RoleSpec(
        prefer=("reasoning", "tool-calling"),
        name_hint=("26B", "A4B", "Gemma-4-26B"),
        exclude=("Embedding", "embed", "FLM", "MTP"),
        size_min=8.0, size_max=40.0,
    ),
    "deep": RoleSpec(
        name_hint=("Mistral-Medium", "128B", "70B", "Nemotron"),
        exclude=("Embedding", "embed", "FLM", "KT"),  # KT quant won't load (mainline llama.cpp)
        size_min=40.0, size_max=200.0,
        heavy=True,
    ),
    "draft": RoleSpec(
        exclude=("Embedding", "embed", "vision", "Music", "SD-", "TRELLIS", "RealESRGAN", "Whisper", "kokoro", "Flux"),
        size_min=0.1, size_max=5.0,
        bigger_is_better=False,
    ),
    "npu_reason": RoleSpec(
        name_hint=("deepseek-r1", "FLM"),
        exclude=("embed", "1b"),
        size_min=2.0, size_max=12.0,
    ),
    "npu_route": RoleSpec(
        name_hint=("llama3.2-1b-FLM", "1b-FLM", "gemma3-1b-FLM"),
        size_min=0.0, size_max=3.0, bigger_is_better=False,
    ),
    "npu_embed": RoleSpec(
        name_hint=("embed-gemma", "FLM"),
        size_max=2.0,
    ),
    "embed": RoleSpec(
        name_hint=("nomic-embed", "Embedding"),
        exclude=("Qwen3-Embedding",),
    ),
    "image": RoleSpec(prefer=("image-generation",), name_hint=("Flux", "SD-Turbo")),
    "mesh_3d": RoleSpec(name_hint=("TRELLIS",)),
}


def _perf_scores() -> dict[str, float]:
    """Optional adaptive signal: avg quality per model from SurrealDB. Empty on any error."""
    try:
        req = urllib.request.Request(  # noqa: S310
            SURREAL,
            data=b"SELECT model, math::mean(quality_score) AS q FROM model_performance GROUP BY model;",
            headers={
                "surreal-ns": "cohezion", "surreal-db": "main",
                "Content-Type": "text/plain", "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
        )
        with urllib.request.urlopen(req, timeout=4) as r:  # noqa: S310
            rows = json.loads(r.read())[-1].get("result", [])
        return {row["model"]: float(row["q"]) for row in rows if row.get("q") is not None}
    except Exception:
        return {}


@dataclass
class FleetRoster:
    """Live-catalog role→model selector. Import the module-level ``ROSTER`` singleton."""

    _cache: list[dict] = field(default_factory=list)
    _cache_at: float = 0.0
    _perf: dict[str, float] = field(default_factory=dict)

    def catalog(self, force: bool = False) -> list[dict]:
        """Live model list from :13305, cached for _CACHE_TTL_S.

        NEVER raises: on a fetch error (server down) returns the last good cache,
        or [] if none — so ``select`` degrades to None instead of crashing a
        daemon at import time.
        """
        now = time.monotonic()
        if force or not self._cache or (now - self._cache_at) > _CACHE_TTL_S:
            try:
                with urllib.request.urlopen(f"{BASE}/api/v1/models", timeout=5) as r:  # noqa: S310
                    self._cache = json.loads(r.read()).get("data", [])
                self._cache_at = now
                self._perf = _perf_scores()
            except Exception:
                pass  # keep stale cache (possibly []); do not raise
        return self._cache

    def _score(self, m: dict, spec: RoleSpec) -> float | None:
        mid = m.get("id", "")
        labels = set(m.get("labels") or [])
        size = float(m.get("size") or 0.0)
        if any(x.lower() in mid.lower() for x in spec.exclude):
            return None
        if spec.require and not set(spec.require).issubset(labels):
            return None
        prefer_hits = len(labels & set(spec.prefer))
        name_hits = sum(1 for h in spec.name_hint if h.lower() in mid.lower())
        # Banded size role: known size must be in-band; unknown size allowed only
        # when name-hinted (FLM/NPU models carry no catalog size).
        banded = spec.size_min > 0.0 or spec.size_max < 999.0
        if banded:
            if size:
                if not (spec.size_min <= size <= spec.size_max):
                    return None
            elif name_hits == 0:
                return None
        # A role with positive signals requires at least one match — else the size
        # proxy hands every unconstrained role to the biggest model.
        if (spec.prefer or spec.name_hint) and (prefer_hits + name_hits) == 0:
            return None
        score = 10.0 * prefer_hits + 8.0 * name_hits
        score += (size if spec.bigger_is_better else -size) * 0.5
        score += 25.0 * self._perf.get(mid, 0.0)  # adaptive: recorded quality wins when present
        return score

    def select(self, role: str, *, loadable: bool = False, force: bool = False) -> str | None:
        """Best live model for ``role``. loadable=True applies the load-safety guard for heavy roles."""
        spec = ROLE_SPECS.get(role)
        if spec is None:
            raise KeyError(f"unknown role {role!r}; known: {sorted(ROLE_SPECS)}")
        ranked = sorted(
            ((self._score(m, spec), m) for m in self.catalog(force)),
            key=lambda t: (t[0] if t[0] is not None else -1e9),
            reverse=True,
        )
        cand = [(s, m) for s, m in ranked if s is not None]
        if not cand:
            return None
        if loadable and spec.heavy:
            avail = available_ram_gb()
            for m in (c[1] for c in cand):
                ok, _reason = check_load_safe(m, avail)  # SoT guard in load_safety
                if ok:
                    return m["id"]
            return None  # nothing heavy provably fits right now
        return cand[0][1]["id"]

    def effective_size_gb(self, model_id: str) -> float | None:
        """Conservative footprint estimate for a catalog model, via load_safety."""
        m = next((x for x in self.catalog() if x["id"] == model_id), None)
        return effective_size_gb(m) if m else None

    def verify(self) -> dict[str, str | None]:
        return {role: self.select(role) for role in ROLE_SPECS}


ROSTER = FleetRoster()
