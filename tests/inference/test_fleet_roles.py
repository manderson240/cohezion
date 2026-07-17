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
    return r


_CATALOG = [
    {"id": "Qwen3.6-35B-A3B-MTP-GGUF", "labels": ["mtp", "tool-calling"], "size": 22.1, "recipe": "llamacpp"},
    {"id": "Gemma-4-26B-A4B-it-GGUF", "labels": ["reasoning", "tool-calling"], "size": 16.9, "recipe": "llamacpp"},
    {"id": "mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS", "labels": [], "size": 42.3, "recipe": "llamacpp"},
    {"id": "Bonsai-1.7B-gguf", "labels": ["tool-calling"], "size": 0.231, "recipe": "llamacpp"},
    {"id": "deepseek-r1-0528-8b-FLM", "labels": [], "size": None, "recipe": "flm"},
    {"id": "gemma3-1b-FLM", "labels": [], "size": None, "recipe": "flm"},
    {"id": "embed-gemma-300m-FLM", "labels": [], "size": None, "recipe": "flm"},
    {"id": "nomic-embed-text-v2-moe-GGUF", "labels": [], "size": 0.5, "recipe": "llamacpp"},
    {"id": "Flux-2-Klein-9B-GGUF", "labels": ["image-generation"], "size": 9.0, "recipe": "sd-cpp"},
    {"id": "TRELLIS-3D", "labels": ["3d"], "size": 15.4, "recipe": "trellis"},
]


def test_roles_resolve_to_expected_models():
    r = _roster_with(_CATALOG)
    got = r.verify()
    # 2026-07-17 RAM-policy retarget: interactive shares the 26B with bbq; the
    # 22GB 35B-MTP is excluded (it stacked on the 26B and breached the RAM floor).
    assert got["interactive"] == "Gemma-4-26B-A4B-it-GGUF"
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
    # The live adaptivity lever is MEASURED quality (25×perf from SurrealDB
    # model_performance — fed by the NPU gauntlet since 2026-07-17): a same-
    # family newcomer with a better recorded score outranks the incumbent
    # purely from data — no ROLE_SPECS edit.
    catalog = [
        *_CATALOG,
        {"id": "Gemma-5-26B-A4B-it-GGUF", "labels": ["reasoning", "tool-calling"], "size": 18.5, "recipe": "llamacpp"},
    ]
    r = _roster_with(catalog)
    assert r.select("interactive") == "Gemma-4-26B-A4B-it-GGUF"  # no perf data → incumbent
    r._perf = {"Gemma-5-26B-A4B-it-GGUF": 0.9, "Gemma-4-26B-A4B-it-GGUF": 0.4}
    assert r.select("interactive") == "Gemma-5-26B-A4B-it-GGUF"  # measured quality wins


def test_interactive_excludes_mtp_heavy_stacker():
    # Discriminating test for the 2026-07-17 retarget: even a catalog where the
    # 35B-MTP has MORE matching labels must NOT resolve interactive to it —
    # the MTP exclusion is the load-bearing RAM-policy mechanism.
    catalog = [
        {"id": "Qwen3.6-35B-A3B-MTP-GGUF", "labels": ["mtp", "tool-calling", "reasoning"], "size": 22.1, "recipe": "llamacpp"},
        {"id": "Gemma-4-26B-A4B-it-GGUF", "labels": ["tool-calling"], "size": 16.9, "recipe": "llamacpp"},
    ]
    r = _roster_with(catalog)
    assert r.select("interactive") == "Gemma-4-26B-A4B-it-GGUF"


def test_deep_loadable_uses_load_safety_guard(monkeypatch):
    import cohezion.inference.fleet_roles as fr

    r = _roster_with(_CATALOG)
    # Plenty of RAM => deep model provably fits (est 42.3*1.7=71.9 <= 100-16).
    monkeypatch.setattr(fr, "available_ram_gb", lambda: 100.0)
    assert r.select("deep", loadable=True) == "mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS"
    # Tight RAM => the load-safety guard refuses; nothing heavy fits.
    monkeypatch.setattr(fr, "available_ram_gb", lambda: 40.0)
    assert r.select("deep", loadable=True) is None
