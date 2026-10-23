"""Live, memory-aware role→model allocation for the local inference fleet.

Daemons ask ``ROSTER.select(role)`` instead of hardcoding a model id. The answer is the best
model for the role that can actually serve RIGHT NOW:

  1. Rank candidates from the live :13305 catalog by capability (catalog ``labels``) and,
     when measured, by role-scoped quality from SurrealDB ``model_performance``
     (three evidence tiers: proven-good > untested > proven-bad).
  2. Allocate against memory, the way the admission gate prices it:
       a. a candidate that is already RESIDENT and in the best evidence tier — it costs
          nothing to use;
       b. otherwise the best-ranked candidate whose load fits lemond's cgroup headroom
          (budget - working set - loads already reserved at the gate), crediting the NPU
          model an FLM load would evict;
       c. otherwise the smallest candidate, so callers never fall back to a hardcoded
          big model because the roster returned None.

Why: on 2026-10-21 this roster's ``interactive`` role picked a 22 GB Qwen3.6-35B CPU model and
``bbq`` a 16.9 GB Gemma-4-26B, by capability alone and blind to memory. The research and
cascade daemons kept asking for them, and the cgroup throttled every model past memory.high.
Footprints come from the gate's ``load_footprint_gb`` so the roster and the gate can never
disagree about what fits.

Merged 2026-10-22 from the daemons' standalone ``~/cohezion-labs/fleet_roster.py`` (untracked),
which carried role-scoped perf keys, the measured ``review`` exclusions and evidence tiers.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from cohezion.compound.oom_guard import normalize_model_name
from cohezion.inference.load_safety import (
    available_ram_gb,
    check_load_safe,
    effective_size_gb,
)
from cohezion.platform.admission_gate import load_footprint_gb, read_lemond_cgroup_gb


logger = logging.getLogger(__name__)

BASE = "http://localhost:13305"
SURREAL = "http://localhost:8001/sql"
_CACHE_TTL_S = 30.0


@dataclass
class RoleSpec:
    """How to choose a model for one role, from live catalog metadata."""

    require: tuple[str, ...] = ()  # labels ALL required (AND)
    prefer: tuple[str, ...] = ()  # labels that add rank score (OR)
    name_hint: tuple[str, ...] = ()  # id substrings that add rank score
    exclude: tuple[str, ...] = ()  # id substrings to reject
    size_min: float = 0.0  # GB, inclusive
    size_max: float = 999.0  # GB, inclusive
    bigger_is_better: bool = True  # size as quality proxy when labels tie
    heavy: bool = False  # apply RAM-fit guard on select(loadable=True)
    # Which gauntlet TASK-grade this role consumes from model_performance (roles here and
    # gauntlet task-roles are different vocabularies). None = no exec-graded signal.
    perf_role: str | None = None


# "HRX": the HIP Runtime Extended backend is a preview (FLM 1.0.8 notes) with no
# measurements here; keep it out of chat roles until model_performance grades it.
_NOT_CHAT = (
    "HRX",
    "Embedding",
    "embed",
    "Music",
    "SD-",
    "TRELLIS",
    "RealESRGAN",
    "Whisper",
    "kokoro",
    "Flux",
)

# Role -> selection policy. Capability-driven, NOT model ids: memory decides size.
ROLE_SPECS: dict[str, RoleSpec] = {
    # Strong interactive chat. NPU (FLM) models are eligible: the standing directive is
    # NPU + CPU with the iGPU free, and memory-aware allocation keeps big CPU models out
    # unless they fit. (Was name-hinted to A3B/MTP/Qwen3.6 with FLM excluded -> 22 GB 35B.)
    "interactive": RoleSpec(
        perf_role="synthesis",
        prefer=("mtp", "tool-calling", "reasoning"),
        exclude=(*_NOT_CHAT, "Bonsai-1", "0.6B"),
        size_min=1.0,
        size_max=45.0,
    ),
    # Skill refinement / judging. (Was name-hinted to 26B/A4B with FLM excluded.)
    "bbq": RoleSpec(
        perf_role="reasoning",
        prefer=("reasoning", "tool-calling"),
        exclude=(*_NOT_CHAT, "MTP"),
        size_min=1.0,
        size_max=40.0,
    ),
    # Deep reasoning. Heaviest available; RAM-fit-guarded, never auto-loaded.
    "deep": RoleSpec(
        name_hint=("Mistral-Medium", "128B", "70B", "Nemotron"),
        exclude=("Embedding", "embed", "FLM", "KT"),  # KT quant won't load (mainline llama.cpp)
        size_min=40.0,
        size_max=200.0,
        heavy=True,
    ),
    # Adversarial code review, ranked by measured balanced accuracy. The excludes are
    # MEASURED specificity failures (models that invent defects in correct code):
    # Qwen3-Coder-30B 0.67 on real code; SmolLM3 / lfm2.5-230m 0.00; Qwen3.6-35B 24/24
    # HTTPError; ThinkingCoder HTTP 500 on a five-token prompt.
    "review": RoleSpec(
        perf_role="review",
        prefer=("reasoning", "tool-calling"),
        name_hint=("Qwen3-8B", "gpt-oss", "Nemotron"),
        exclude=(
            *_NOT_CHAT,
            "vision",
            "Qwen3-Coder",
            "SmolLM3",
            "lfm2.5-230m",
            "Qwen3.6-35B",
            "ThinkingCoder",
        ),
        size_min=3.0,
        size_max=45.0,
    ),
    # Small fast draft / cheap dispatch.
    "draft": RoleSpec(
        perf_role="triage",
        exclude=(*_NOT_CHAT, "vision"),
        size_min=0.1,
        size_max=5.0,
        bigger_is_better=False,
    ),
    # NPU reasoning (FLM only). require=("reasoning",) keeps a routing-graded model from
    # winning a reasoning role on an unrelated score.
    "npu_reason": RoleSpec(
        perf_role="reasoning",
        name_hint=("deepseek-r1", "FLM"),
        require=("reasoning",),
        exclude=("embed", "1b"),
        size_min=2.0,
        size_max=12.0,
    ),
    # NPU routing / classification (sub-2B FLM).
    "npu_route": RoleSpec(
        perf_role="router",
        name_hint=("llama3.2-1b-FLM", "1b-FLM", "gemma3-1b-FLM"),
        size_min=0.0,
        size_max=3.0,
        bigger_is_better=False,
    ),
    # Embeddings on NPU: embeddings-only (chat FLMs carry no 'embeddings' label).
    "npu_embed": RoleSpec(require=("embeddings",), name_hint=("embed-gemma", "FLM"), size_max=2.0),
    # Embeddings, 768D (Qwen3-Embedding-0.6B is broken post-v11).
    "embed": RoleSpec(name_hint=("nomic-embed", "Embedding"), exclude=("Qwen3-Embedding",)),
    "image": RoleSpec(prefer=("image-generation",), name_hint=("Flux", "SD-Turbo")),
    "mesh_3d": RoleSpec(name_hint=("TRELLIS",)),
}


@dataclass(frozen=True)
class MemoryState:
    """What the roster needs to allocate: headroom, residency, and the NPU swap credit."""

    headroom_gb: float  # gate budget - working set - reserved
    resident: frozenset[str]  # normalized, lowercased resident model names
    flm_llm_resident_gb: float = 0.0  # footprint of the one resident FLM llm (NPU slot)


def _get_json(url: str, timeout: float) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
            data = json.loads(r.read())
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def live_memory_state(catalog: list[dict]) -> MemoryState | None:
    """lemond's cgroup headroom, residency and gate reservations; None if unreadable."""
    cgroup = read_lemond_cgroup_gb()
    if cgroup is None:
        return None
    working_set, high = cgroup
    status = _get_json(f"{BASE}/admission/status", timeout=2.0) or {}
    mem_raw = status.get("memory")
    mem: dict = mem_raw if isinstance(mem_raw, dict) else {}
    reserved = float(mem.get("reserved_gb") or 0.0)
    budget = float(mem.get("budget_gb") or 0.9 * high)
    health = _get_json(f"{BASE}/api/v1/health", timeout=2.0) or {}
    loaded = [e for e in health.get("all_models_loaded", []) if isinstance(e, dict)]
    by_id = {normalize_model_name(str(m.get("id", ""))): m for m in catalog}
    flm_gb = 0.0
    for e in loaded:
        if e.get("recipe") == "flm" and e.get("type") == "llm":
            name = normalize_model_name(str(e.get("model_name", "")))
            flm_gb = max(flm_gb, load_footprint_gb(name, by_id.get(name)) or 0.0)
    return MemoryState(
        headroom_gb=budget - working_set - reserved,
        resident=frozenset(
            normalize_model_name(str(e.get("model_name", ""))).lower() for e in loaded
        ),
        flm_llm_resident_gb=flm_gb,
    )


def _perf_scores() -> dict[tuple[str, str], float]:
    """Mean quality per (model, gauntlet-role) from SurrealDB. Empty on any error.

    Role-keyed: one model's grade varies enormously by task (deepseek-r1 triage 0.774 vs
    reasoning 0.048), so each roster role consumes only the grade it declares.
    """
    try:
        req = urllib.request.Request(
            SURREAL,
            data=b"SELECT model, role, math::mean(quality_score) AS q FROM model_performance "
            b"GROUP BY model, role;",
            headers={
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
        )
        with urllib.request.urlopen(req, timeout=4) as r:  # noqa: S310
            rows = json.loads(r.read())[-1].get("result", [])
        return {
            (row["model"], row["role"]): float(row["q"])
            for row in rows
            if row.get("q") is not None and row.get("role")
        }
    except Exception:
        return {}


def _tier(score: float) -> int:
    """Evidence tier of a score from _score(): 2 proven-good, 1 untested, 0 proven-bad."""
    return 2 if score >= 1000.0 else (1 if score >= 0.0 else 0)


@dataclass
class FleetRoster:
    """Live-catalog, memory-aware role→model allocator. Import the module-level ``ROSTER``."""

    _cache: list[dict] = field(default_factory=list)
    _cache_at: float = 0.0
    _perf: dict = field(default_factory=dict)  # {(model, role): mean}; flat {model: mean} tolerated
    # Injectable for tests; None-returning means "no memory signal" (rank only).
    memory: Callable[[list[dict]], MemoryState | None] = live_memory_state

    def catalog(self, force: bool = False) -> list[dict]:
        """Live (downloaded) model list from :13305, cached for _CACHE_TTL_S. Never raises."""
        now = time.monotonic()
        if force or not self._cache or (now - self._cache_at) > _CACHE_TTL_S:
            try:
                with urllib.request.urlopen(f"{BASE}/api/v1/models", timeout=5) as r:  # noqa: S310
                    self._cache = json.loads(r.read()).get("data", [])
                self._cache_at = now
                self._perf = _perf_scores()
            except Exception:
                pass  # keep the stale cache (possibly []); do not raise
        return self._cache

    def _perf_for(self, mid: str, spec: RoleSpec) -> float | None:
        if not self._perf:
            return None
        if any(isinstance(k, tuple) for k in self._perf):
            return None if spec.perf_role is None else self._perf.get((mid, spec.perf_role))
        return self._perf.get(mid)  # legacy flat model-keyed map

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
        banded = spec.size_min > 0.0 or spec.size_max < 999.0
        if banded:
            if size:
                if not (spec.size_min <= size <= spec.size_max):
                    return None
            elif name_hits == 0:
                return None
        # A role with positive signals requires at least one match, or the size proxy
        # hands every role to the biggest model.
        if (spec.prefer or spec.name_hint) and (prefer_hits + name_hits) == 0:
            return None
        # Three evidence tiers on one scale: measurement dominates, a measured 0.0 sits
        # below every untested model, and priors only break ties.
        priors = 10.0 * prefer_hits + 8.0 * name_hits
        priors += (size if spec.bigger_is_better else -size) * 0.5
        tiebreak = math.tanh(priors / 50.0)
        perf = self._perf_for(mid, spec)
        if perf is None:
            return 0.5 + 0.1 * tiebreak
        if perf <= 0.0:
            return -1.0 + 0.1 * tiebreak
        return 1000.0 + 1000.0 * perf + tiebreak

    def select(self, role: str, *, loadable: bool = False, force: bool = False) -> str | None:
        """The model ``role`` should use now. None only when no catalog model fits the role."""
        spec = ROLE_SPECS.get(role)
        if spec is None:
            raise KeyError(f"unknown role {role!r}; known: {sorted(ROLE_SPECS)}")
        catalog = self.catalog(force)
        ranked = sorted(
            ((s, m) for m in catalog if (s := self._score(m, spec)) is not None),
            key=lambda t: t[0],
            reverse=True,
        )
        if not ranked:
            return None
        if loadable and spec.heavy:
            avail = available_ram_gb()
            for _s, m in ranked:
                ok, _reason = check_load_safe(m, avail)
                if ok:
                    return m["id"]
            return None  # nothing heavy provably fits right now
        try:
            mem = self.memory(catalog)
        except Exception as exc:  # a memory probe must never break selection
            logger.warning("fleet roster: memory probe failed: %s", exc)
            mem = None
        if mem is None:
            return ranked[0][1]["id"]
        return self._allocate(ranked, mem)

    @staticmethod
    def _allocate(ranked: list[tuple[float, dict]], mem: MemoryState) -> str:
        best_tier = _tier(ranked[0][0])
        for score, m in ranked:  # (a) resident and as good as the best evidence
            if _tier(score) == best_tier and normalize_model_name(m["id"]).lower() in mem.resident:
                return m["id"]

        def cost(m: dict) -> float | None:
            fp = load_footprint_gb(m["id"], m)
            if fp is None:
                return None
            credit = mem.flm_llm_resident_gb if m["id"].lower().endswith("-flm") else 0.0
            return fp - credit

        for _score, m in ranked:  # (b) best that fits the headroom
            c = cost(m)
            if c is not None and c <= mem.headroom_gb:
                return m["id"]
        for score, m in ranked:  # (c) nothing new fits: anything resident and not proven-bad
            if _tier(score) > 0 and normalize_model_name(m["id"]).lower() in mem.resident:
                return m["id"]
        # (d) the cheapest new load, so the gate can admit it once room frees up
        return min(ranked, key=lambda t: cost(t[1]) or float("inf"))[1]["id"]

    def effective_size_gb(self, model_id: str) -> float | None:
        """Conservative footprint estimate for a catalog model, via load_safety."""
        m = next((x for x in self.catalog() if x["id"] == model_id), None)
        return effective_size_gb(m) if m else None

    def verify(self) -> dict[str, str | None]:
        return {role: self.select(role) for role in ROLE_SPECS}


ROSTER = FleetRoster()


def _main() -> int:
    """``python -m cohezion.inference.fleet_roles [--json]``: every role -> its model now."""
    resolved = ROSTER.verify()
    mem = live_memory_state(ROSTER.catalog())
    if "--json" in sys.argv:
        print(
            json.dumps(
                {"headroom_gb": mem and round(mem.headroom_gb, 1), "roles": resolved}, indent=2
            )
        )
        return 0
    head = f"{mem.headroom_gb:.1f} GB cgroup headroom" if mem else "memory unreadable"
    print(f"Fleet roster — {len(ROSTER.catalog())} models live, {head}")
    for role, model in resolved.items():
        print(f"  {role:12s} -> {model or 'UNRESOLVED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
