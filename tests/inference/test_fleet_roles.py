"""Tests for adaptive live-catalog role→model selection (fleet_roles)."""

from __future__ import annotations

import time

from cohezion.inference.fleet_roles import ROLE_SPECS, FleetRoster


def _roster_with(catalog: list[dict]) -> FleetRoster:
    """A FleetRoster with a pinned in-memory catalog (no network)."""
    r = FleetRoster()
    r._cache = catalog
    r._cache_at = time.monotonic() + 1e6  # far future => never re-fetches
    r._perf = {}
    r.memory = lambda _catalog: None  # rank only: no live cgroup/residency in unit tests
    return r


_CATALOG = [
    {
        "id": "Qwen3.6-35B-A3B-MTP-GGUF",
        "labels": ["mtp", "tool-calling"],
        "size": 22.1,
        "recipe": "llamacpp",
    },
    {
        "id": "Gemma-4-26B-A4B-it-GGUF",
        "labels": ["reasoning", "tool-calling"],
        "size": 16.9,
        "recipe": "llamacpp",
    },
    {
        "id": "mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS",
        "labels": [],
        "size": 42.3,
        "recipe": "llamacpp",
    },
    {"id": "Bonsai-1.7B-gguf", "labels": ["tool-calling"], "size": 0.231, "recipe": "llamacpp"},
    {
        "id": "deepseek-r1-0528-8b-FLM",
        "labels": ["reasoning", "chat"],
        "size": None,
        "recipe": "flm",
    },
    {"id": "gemma3-1b-FLM", "labels": [], "size": None, "recipe": "flm"},
    {"id": "embed-gemma-300m-FLM", "labels": ["embeddings"], "size": None, "recipe": "flm"},
    {"id": "nomic-embed-text-v2-moe-GGUF", "labels": [], "size": 0.5, "recipe": "llamacpp"},
    {"id": "Flux-2-Klein-9B-GGUF", "labels": ["image-generation"], "size": 9.0, "recipe": "sd-cpp"},
    {"id": "TRELLIS-3D", "labels": ["3d"], "size": 15.4, "recipe": "trellis"},
]


def test_roles_resolve_to_expected_models():
    r = _roster_with(_CATALOG)
    got = r.verify()
    assert got["interactive"] == "Qwen3.6-35B-A3B-MTP-GGUF"
    assert got["bbq"] == "Gemma-4-26B-A4B-it-GGUF"
    assert got["deep"] == "mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS"
    assert got["draft"] == "Bonsai-1.7B-gguf"
    assert got["npu_reason"] == "deepseek-r1-0528-8b-FLM"
    assert got["npu_route"] == "gemma3-1b-FLM"
    assert got["npu_embed"] == "embed-gemma-300m-FLM"
    assert got["embed"] == "nomic-embed-text-v2-moe-GGUF"
    assert got["image"] == "Flux-2-Klein-9B-GGUF"
    assert got["mesh_3d"] == "TRELLIS-3D"


def test_all_roles_defined_and_resolvable():
    r = _roster_with(_CATALOG)
    for role in ROLE_SPECS:
        assert r.select(role) is not None, f"role {role} unresolved against test catalog"


def test_empty_catalog_returns_none_not_raise():
    # Server-down / no models: catalog() yields []; select degrades to None, never raises.
    r = FleetRoster()
    r.catalog = lambda force=False: []  # type: ignore[method-assign]
    assert r.select("interactive") is None
    assert r.verify()["deep"] is None


def test_unknown_role_raises():
    r = _roster_with(_CATALOG)
    try:
        r.select("nonsense")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_adaptivity_new_model_wins_without_code_change():
    # A newly-installed stronger interactive model (more matching labels) is
    # picked purely from catalog metadata — no ROLE_SPECS edit.
    catalog = [
        *_CATALOG,
        {
            "id": "Qwen4-40B-A3B-MTP-GGUF",
            "labels": ["mtp", "tool-calling", "reasoning"],
            "size": 24.0,
            "recipe": "llamacpp",
        },
    ]
    r = _roster_with(catalog)
    # Both match; the newcomer has an extra 'reasoning' label => higher score.
    assert r.select("interactive") == "Qwen4-40B-A3B-MTP-GGUF"


def test_deep_loadable_uses_load_safety_guard(monkeypatch):
    import cohezion.inference.fleet_roles as fr

    r = _roster_with(_CATALOG)
    # Plenty of RAM => deep model provably fits (est 42.3*1.7=71.9 <= 100-16).
    monkeypatch.setattr(fr, "available_ram_gb", lambda: 100.0)
    assert r.select("deep", loadable=True) == "mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS"
    # Tight RAM => the load-safety guard refuses; nothing heavy fits.
    monkeypatch.setattr(fr, "available_ram_gb", lambda: 40.0)
    assert r.select("deep", loadable=True) is None


# -- memory-aware allocation (2026-10-22) -------------------------------------------------
# Live 2026-10-21: interactive -> a 22 GB Qwen3.6-35B CPU model and bbq -> a 16.9 GB
# Gemma-4-26B, chosen by capability alone; the daemons asking for them throttled lemond.

from cohezion.inference.fleet_roles import MemoryState


_ALLOC = [
    {
        "id": "Big-35B-GGUF",
        "labels": ["reasoning", "tool-calling"],
        "size": 22.0,
        "recipe": "llamacpp",
    },
    {
        "id": "Mid-12B-GGUF",
        "labels": ["reasoning", "tool-calling"],
        "size": 9.0,
        "recipe": "llamacpp",
    },
    {"id": "small-4b-FLM", "labels": ["reasoning", "tool-calling"], "size": 5.0, "recipe": "flm"},
]


def _alloc(memory: MemoryState) -> FleetRoster:
    r = _roster_with(_ALLOC)
    r.memory = lambda _catalog: memory
    return r


def test_without_memory_the_biggest_wins():  # the old behaviour, kept for rank-only callers
    assert _roster_with(_ALLOC).select("bbq") == "Big-35B-GGUF"


def test_resident_model_in_the_best_tier_is_chosen():
    mem = MemoryState(headroom_gb=50.0, resident=frozenset({"mid-12b-gguf"}))
    assert _alloc(mem).select("bbq") == "Mid-12B-GGUF"  # loaded: costs nothing


def test_best_candidate_that_fits_the_headroom():
    # Mid-12B costs 9 GB weights + 5 GB KV = 14 GB: footprints include the KV cache.
    assert (
        _alloc(MemoryState(headroom_gb=15.0, resident=frozenset())).select("bbq") == "Mid-12B-GGUF"
    )
    assert (
        _alloc(MemoryState(headroom_gb=12.0, resident=frozenset())).select("bbq") == "small-4b-FLM"
    )


def test_npu_swap_credit_lets_an_flm_model_fit():
    mem = MemoryState(headroom_gb=1.0, resident=frozenset({"other-flm"}), flm_llm_resident_gb=5.0)
    assert _alloc(mem).select("bbq") == "small-4b-FLM"  # replaces the resident FLM


def test_nothing_fits_returns_the_cheapest_not_none():
    # Callers fall back to a hardcoded big model on None; never hand them that excuse.
    mem = MemoryState(headroom_gb=0.0, resident=frozenset())
    assert _alloc(mem).select("bbq") == "small-4b-FLM"


def test_measured_quality_beats_residency_of_a_worse_tier():
    r = _alloc(MemoryState(headroom_gb=50.0, resident=frozenset({"mid-12b-gguf"})))
    r._perf = {("Big-35B-GGUF", "reasoning"): 0.9, ("Mid-12B-GGUF", "reasoning"): 0.0}
    assert r.select("bbq") == "Big-35B-GGUF"  # proven-good beats a resident proven-bad


def test_specs_carry_no_big_model_name_hints():
    for role in ("interactive", "bbq", "review"):
        hints = " ".join(ROLE_SPECS[role].name_hint)
        assert "26B" not in hints and "35B" not in hints and "A3B" not in hints
    assert "FLM" not in ROLE_SPECS["interactive"].exclude and "FLM" not in ROLE_SPECS["bbq"].exclude


def test_when_nothing_fits_a_resident_model_beats_a_new_load():
    # Live 2026-10-22: 1 GB headroom, a proven-good model existed but did not fit, and the
    # cheapest-new-load fallback picked an untested preview runtime while two eligible
    # models sat resident.
    r = _alloc(MemoryState(headroom_gb=1.0, resident=frozenset({"mid-12b-gguf"})))
    r._perf = {("Big-35B-GGUF", "reasoning"): 0.9}  # best tier is proven-good, and too big
    assert r.select("bbq") == "Mid-12B-GGUF"


def test_resident_proven_bad_is_not_preferred():
    r = _alloc(MemoryState(headroom_gb=1.0, resident=frozenset({"mid-12b-gguf"})))
    r._perf = {("Mid-12B-GGUF", "reasoning"): 0.0}
    assert r.select("bbq") == "small-4b-FLM"


def test_preview_runtime_excluded_from_chat_roles():
    for role in ("interactive", "bbq", "review", "draft"):
        assert any(x.lower() == "hrx" for x in ROLE_SPECS[role].exclude), role
