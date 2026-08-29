"""Tests for device-aware silicon residency census.

Fixtures are transcribed from a LIVE `/api/v1/health` response captured from
Lemonade 11.8.1 on the Strix Halo box (2026-08-29). Using the real payload
rather than an invented one means these tests encode the server's actual
schema, not our assumptions about it.

Every T2 test below is DISCRIMINATING: it fails when the mechanism under test
is neutralised, so a green run is evidence of behaviour, not of existence.
"""

from __future__ import annotations

from cohezion.inference.silicon_residency import (
    DeviceOccupancy,
    ResidentModel,
    SiliconCensus,
    normalize_device,
    parse_census,
)


# --- Live-captured fixture (verbatim field values, trimmed to relevant keys) ---

LIVE_HEALTH: dict = {
    "status": "ok",
    "version": "11.8.1",
    "all_models_loaded": [
        {
            "model_name": "kokoro-v1",
            "device": "cpu",
            "type": "tts",
            "recipe": "kokoro",
            "recipe_options": {"ctx_size": 32768},
            "pinned": False,
            "is_busy": False,
            "is_streaming": False,
            "last_use": 175174,
            "slot_pool": "standard/tts",
            "residency_class": "standard",
            "watchdog_reset": False,
            "backend_alive": True,
            "backend_health": "ready",
            "pid": 18483,
        },
        {
            "model_name": "llama3.2-1b-FLM",
            "device": "npu",
            "type": "llm",
            "recipe": "flm",
            "recipe_options": {"ctx_size": 4096},
            "pinned": False,
            "is_busy": False,
            "is_streaming": False,
            "last_use": 900544,
            "slot_pool": "standard/llm",
            "residency_class": "standard",
            "watchdog_reset": False,
            "backend_alive": True,
            "backend_health": "ready",
            "pid": 42292,
        },
        {
            "model_name": "Gemma-4-E4B-it-GGUF",
            "device": "gpu",
            "type": "llm",
            "recipe": "llamacpp",
            "recipe_options": {"ctx_size": 8192},
            "pinned": False,
            "is_busy": False,
            "is_streaming": False,
            "last_use": 901079,
            "slot_pool": "standard/llm",
            "residency_class": "standard",
            "watchdog_reset": False,
            "backend_alive": True,
            "backend_health": "ready",
            "pid": 42341,
        },
        {
            "model_name": "nomic-embed-text-v2-moe-GGUF",
            "device": "gpu",
            "type": "embedding",
            "recipe": "llamacpp",
            "recipe_options": {"ctx_size": 2048},
            "pinned": False,
            "is_busy": False,
            "is_streaming": False,
            "last_use": 938780,
            "slot_pool": "standard/embedding",
            "residency_class": "standard",
            "watchdog_reset": False,
            "backend_alive": True,
            "backend_health": "ready",
            "pid": 20512,
        },
    ],
}

LIVE_CATALOG: list[dict] = [
    {"id": "llama3.2-1b-FLM", "size": 1.3},
    {"id": "Gemma-4-E4B-it-GGUF", "size": 5.56},
    {"id": "nomic-embed-text-v2-moe-GGUF", "size": 0.477},
    {"id": "kokoro-v1"},  # no size reported by the live catalog
]


# --------------------------- T1: structural ---------------------------


def test_t1_normalize_device_maps_gpu_to_igpu() -> None:
    assert normalize_device("gpu") == "igpu"
    assert normalize_device("npu") == "npu"
    assert normalize_device("cpu") == "cpu"


def test_t1_unknown_device_is_not_guessed() -> None:
    """An unrecognised device must NOT be coerced onto real silicon."""
    assert normalize_device("tpu") == "unknown"
    assert normalize_device(None) == "unknown"
    assert normalize_device("") == "unknown"


def test_t1_raw_device_is_preserved() -> None:
    census = parse_census(LIVE_HEALTH)
    gemma = next(m for m in census.residents if m.name == "Gemma-4-E4B-it-GGUF")
    assert gemma.raw_device == "gpu", "raw device string must survive normalisation"
    assert gemma.device == "igpu"


# ------------------- T2: discriminating -- device awareness -------------------


def test_t2_census_separates_silicon_not_model_type() -> None:
    """DISCRIMINATING: a device-blind impl groups by `type` and fails here.

    llama3.2-1b-FLM and Gemma-4-E4B are BOTH type='llm'. Grouping by type
    puts them in one bucket; only reading `device` separates npu from igpu.
    """
    census = parse_census(LIVE_HEALTH)

    assert census.occupancy("npu").count == 1
    assert census.occupancy("npu").models[0].name == "llama3.2-1b-FLM"

    igpu_names = {m.name for m in census.occupancy("igpu").models}
    assert igpu_names == {"Gemma-4-E4B-it-GGUF", "nomic-embed-text-v2-moe-GGUF"}

    assert census.occupancy("cpu").count == 1
    assert census.occupancy("cpu").models[0].name == "kokoro-v1"


def test_t2_all_three_silicon_types_are_resolved() -> None:
    """The whole point of the goal: see NPU, iGPU and CPU simultaneously."""
    census = parse_census(LIVE_HEALTH)
    assert census.devices_loaded == {"npu", "igpu", "cpu"}


def test_t2_loaded_is_not_engaged() -> None:
    """DISCRIMINATING: an impl conflating 'loaded' with 'busy' fails.

    The live fleet has 4 models resident and ZERO serving. Reporting them as
    engaged would make a scheduler believe the box is saturated when it is idle.
    """
    census = parse_census(LIVE_HEALTH)
    assert census.devices_loaded == {"npu", "igpu", "cpu"}
    assert census.devices_engaged == set(), "nothing is busy in the captured snapshot"
    assert census.occupancy("npu").idle is True


def test_t2_missing_device_field_does_not_land_on_real_silicon() -> None:
    payload = {"all_models_loaded": [{"model_name": "mystery", "type": "llm"}]}
    census = parse_census(payload)
    assert census.devices_loaded == {"unknown"}
    assert census.occupancy("npu").count == 0


# ------------------- T2: discriminating -- eviction safety -------------------


def _model(**overrides) -> ResidentModel:
    base = {
        "name": "m",
        "raw_device": "gpu",
        "device": "igpu",
        "backend_alive": True,
        "backend_health": "ready",
    }
    base.update(overrides)
    return ResidentModel(**base)


def test_t2_busy_model_is_never_evictable() -> None:
    """DISCRIMINATING: an impl checking only `pinned` returns True and fails."""
    assert _model(is_busy=True, pinned=False).evictable is False


def test_t2_streaming_model_is_never_evictable() -> None:
    """DISCRIMINATING: evicting mid-stream truncates a live response."""
    assert _model(is_streaming=True, pinned=False).evictable is False


def test_t2_pinned_model_is_never_evictable() -> None:
    assert _model(pinned=True).evictable is False


def test_t2_unknown_health_fails_closed() -> None:
    """DISCRIMINATING: fail-OPEN impl (default True) returns evictable and fails.

    An empty/absent backend_health is UNKNOWN, not healthy. Treating unknown
    as safe is how a supervisor evicts a model that was mid-recovery.
    """
    assert _model(backend_health="").evictable is False
    assert _model(backend_alive=False, backend_health="ready").evictable is False


def test_t2_idle_healthy_unpinned_model_is_evictable() -> None:
    """The positive case -- proves the guard is not simply always-False."""
    assert _model().evictable is True


# --- regressions found by the LIVE server, not by fixtures (2026-08-29) ---


def test_t2_busy_backend_health_is_not_an_unhealthy_alert() -> None:
    """REGRESSION: `backend_health='busy'` was raising a CRITICAL alert.

    DISCRIMINATING: an impl using `health not in ('ready','')` flags busy and
    fails. 'busy' means the model is serving a request -- normal operation.
    The live fleet emitted this state within minutes of the fixture being
    written, which no recorded fixture could have caught.
    """
    assert _model(backend_health="busy").unhealthy is False


def test_t2_busy_backend_is_still_not_evictable() -> None:
    """The asymmetry: not alert-worthy, but also not safe to evict.

    DISCRIMINATING: an impl that simply added 'busy' to one shared healthy-set
    would make a serving model evictable and fail here.
    """
    assert _model(backend_health="busy").evictable is False


def test_t2_known_bad_health_states_still_alert() -> None:
    """Proves the relaxation did not disable the alert entirely."""
    for bad in ("error", "failed", "crashed", "dead", "stopped"):
        assert _model(backend_health=bad).unhealthy is True, bad
    assert _model(backend_alive=False).unhealthy is True


def test_t2_unrecognised_health_does_not_page_but_does_not_evict() -> None:
    """Unknown states resolve oppositely for alerting vs eviction."""
    unknown = _model(backend_health="reticulating-splines")
    assert unknown.unhealthy is False, "unknown state must not raise CRITICAL"
    assert unknown.evictable is False, "unknown state must not permit eviction"


def test_t2_evictable_gb_excludes_protected_models() -> None:
    occ = DeviceOccupancy(
        device="igpu",
        models=(
            _model(name="busy", is_busy=True, size_gb=20.0),
            _model(name="pinned", pinned=True, size_gb=10.0),
            _model(name="free", size_gb=5.0),
        ),
    )
    assert occ.resident_gb == 35.0
    assert occ.evictable_gb == 5.0, "only the idle unpinned model may be reclaimed"


# ------------------- T2: discriminating -- ctx hazards -------------------


def test_t2_both_zero_and_negative_ctx_are_hazards() -> None:
    """DISCRIMINATING: an impl checking only ctx_size == 0 passes 0 and fails -1."""
    assert _model(ctx_size=0).ctx_hazard is True
    assert _model(ctx_size=-1).ctx_hazard is True
    assert _model(ctx_size=None).ctx_hazard is True
    assert _model(ctx_size=16384).ctx_hazard is False


def test_t2_crasher_and_uncapped_are_distinct_risks() -> None:
    """MEASURED 2026-08-29: ctx_size=-1 is NOT the ctx_size=0 crasher.

    Loading gemma3-1b-FLM with no explicit ctx_size under a global default of
    -1 produced `--ctx-len 32768` -- exactly the model's own
    `max_context_window`. So -1 means "use the model maximum", not an unbounded
    GTT mapping. An earlier revision conflated them, which overstated -1 and
    understated 0.

    DISCRIMINATING: an impl treating them as one class fails both asserts below.
    """
    crasher = _model(ctx_size=0)
    uncapped = _model(ctx_size=-1)

    assert crasher.ctx_crasher is True
    assert crasher.ctx_uncapped is False
    assert crasher.ctx_risk == "crasher"

    assert uncapped.ctx_crasher is False, "-1 is not the documented hard-hang vector"
    assert uncapped.ctx_uncapped is True
    assert uncapped.ctx_risk == "uncapped"

    assert _model(ctx_size=16384).ctx_risk == "ok"


def test_t2_live_snapshot_has_no_ctx_hazards() -> None:
    """All four live models carry explicit bounded ctx -- regression guard."""
    census = parse_census(LIVE_HEALTH)
    assert census.ctx_hazards == ()


# ------------------- byte budget + 11.8.1 scheduler fields -------------------


def test_catalog_join_supplies_sizes() -> None:
    census = parse_census(LIVE_HEALTH, catalog=LIVE_CATALOG)
    assert census.occupancy("npu").resident_gb == 1.3
    assert census.occupancy("igpu").resident_gb == round(5.56 + 0.477, 3)
    assert census.total_resident_gb == round(1.3 + 5.56 + 0.477, 3)


def test_missing_size_is_zero_not_estimated() -> None:
    """A fabricated size would corrupt the byte budget silently."""
    census = parse_census(LIVE_HEALTH, catalog=LIVE_CATALOG)
    kokoro = next(m for m in census.residents if m.name == "kokoro-v1")
    assert kokoro.size_gb == 0.0


def test_slot_pool_and_residency_class_are_captured() -> None:
    """11.8.1 scheduler fields -- previously unparsed anywhere in the codebase."""
    census = parse_census(LIVE_HEALTH)
    npu = census.occupancy("npu").models[0]
    assert npu.slot_pool == "standard/llm"
    assert npu.residency_class == "standard"


def test_watchdog_reset_surfaces_as_instability_signal() -> None:
    payload = {
        "all_models_loaded": [
            {
                "model_name": "flappy",
                "device": "gpu",
                "watchdog_reset": True,
                "backend_alive": True,
                "backend_health": "ready",
                "recipe_options": {"ctx_size": 8192},
            }
        ]
    }
    census = parse_census(payload)
    assert [m.name for m in census.watchdog_resets] == ["flappy"]
    assert parse_census(LIVE_HEALTH).watchdog_resets == ()


# ------------------------- robustness -------------------------


def test_empty_and_malformed_payloads_do_not_raise() -> None:
    assert parse_census({}).residents == ()
    assert parse_census({"all_models_loaded": None}).residents == ()
    assert parse_census({"all_models_loaded": ["not-a-dict"]}).residents == ()


def test_occupancy_for_absent_device_is_empty_not_error() -> None:
    census: SiliconCensus = parse_census({})
    occ = census.occupancy("npu")
    assert occ.count == 0
    assert occ.busy is False
    assert occ.idle is False
