"""Tests for byte-budgeted, device-aware residency planning.

The T2 tests are discriminating: each fails if the safety rule it names is
removed. In particular the budget and protection tests exist because the
failure they prevent (evicting a busy model, or loading past the RAM floor)
is silent and catastrophic on a 24/7 box.
"""

from __future__ import annotations

from cohezion.inference.silicon_policy import (
    DEFAULT_POLICY,
    ResidencyPolicy,
    SiliconSlot,
    evictable_candidates,
    plan_residency,
)
from cohezion.inference.silicon_residency import parse_census


CATALOG = [
    {"id": "llama3.2-1b-FLM", "size": 1.3},
    {"id": "Gemma-4-E4B-it-GGUF", "size": 5.56},
    {"id": "Nemotron-3-Nano-30B-A3B-GGUF", "size": 21.3},
    {"id": "Qwen3-0.6B-GGUF", "size": 0.356},
]


def _entry(name, device, **kw):
    base = {
        "model_name": name,
        "device": device,
        "type": kw.pop("type", "llm"),
        "recipe_options": {"ctx_size": kw.pop("ctx_size", 8192)},
        "pinned": kw.pop("pinned", False),
        "is_busy": kw.pop("is_busy", False),
        "is_streaming": kw.pop("is_streaming", False),
        "last_use": kw.pop("last_use", 1000),
        "backend_alive": True,
        "backend_health": "ready",
    }
    base.update(kw)
    return base


# The live fleet shape observed 2026-08-29: CPU carries no LLM.
LIVE_SHAPE = {
    "all_models_loaded": [
        _entry("llama3.2-1b-FLM", "npu", ctx_size=4096, last_use=1156275),
        _entry("Gemma-4-E4B-it-GGUF", "gpu", last_use=1156827),
        _entry("Qwen3-0.6B-GGUF", "gpu", last_use=936739),
    ]
}


# --------------------------- fail-closed ---------------------------


def test_empty_census_bootstraps_rather_than_refusing() -> None:
    """REVERSED by code review 2026-08-29 -- the old assertion was the bug.

    An earlier revision refused to plan on an empty census, reasoning that it
    meant "router unreachable". It does not: the daemon handles an unreachable
    router in its own except branch (emitting router_unreachable and keeping
    the last good census), so the only way to reach here with no residents is a
    REACHABLE router with an EMPTY fleet -- exactly the cold-boot state `--heal`
    exists to fix. The refusal meant the supervisor could never bootstrap the
    tier-0 NPU router it was written to keep resident.

    DISCRIMINATING: restoring the refusal makes this fail.
    """
    plan = plan_residency(parse_census({}), catalog=CATALOG, available_gb=100.0)

    assert not plan.is_noop, "an empty fleet is the case healing exists for"
    assert "llama3.2-1b-FLM" in {a.model for a in plan.of("load")}
    assert set(plan.idle_devices) == {"npu", "igpu", "cpu"}


def test_unmeasurable_ram_refuses_all_loads() -> None:
    """REVIEW FINDING: headroom must fail CLOSED when RAM cannot be measured.

    `_available_ram_gb()` returns 0.0 on OSError or a missing MemAvailable
    line. An earlier revision then fell back to the byte ceiling alone,
    silently dropping the whole reserve -- a 21 GB load could proceed against
    the 80 GB ceiling on a box with 4 GB free.
    """
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=0.0)

    assert plan.of("load") == (), "unmeasurable RAM must not permit loads"
    assert any("could not be measured" in w for w in plan.warnings)


def test_catalog_entry_without_size_is_refused_not_treated_as_zero() -> None:
    """REVIEW FINDING: byte-budget bypass via a missing `size` key.

    `_catalog_size` returned 0.0 both for "absent from catalog" and "present
    with no size". Only the first was caught by `_catalog_has`, so an entry
    like {"id": "Nemotron-..."} scored 0.0, passed `size > headroom`, and
    subtracted nothing. Catalog entries really do lack `size` (kokoro-v1 does),
    and hotswap.py filters for a numeric size for this reason.
    """
    catalog = [
        {"id": "llama3.2-1b-FLM", "size": 1.3},
        {"id": "Gemma-4-E4B-it-GGUF", "size": 5.56},
        {"id": "Nemotron-3-Nano-30B-A3B-GGUF"},  # no `size` key
    ]
    plan = plan_residency(parse_census({}), catalog=catalog, available_gb=100.0)

    assert "Nemotron-3-Nano-30B-A3B-GGUF" not in {a.model for a in plan.of("load")}
    assert any("no `size`" in r for r in plan.refused)


# --------------------------- device reconciliation ---------------------------


def test_cpu_slot_gap_is_detected_on_the_live_shape() -> None:
    """The measured inefficiency: 32-core CPU carries no LLM."""
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=100.0)

    loads = {a.model for a in plan.of("load")}
    assert "Nemotron-3-Nano-30B-A3B-GGUF" in loads
    assert "cpu" in plan.idle_devices


def test_npu_tier0_model_is_planned_for_pinning() -> None:
    """DISCRIMINATING: an impl ignoring `slot.pin` emits no pin action."""
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=100.0)

    pins = {a.model for a in plan.of("pin")}
    assert pins == {"llama3.2-1b-FLM"}


def test_already_pinned_model_is_not_re_pinned() -> None:
    payload = {
        "all_models_loaded": [
            _entry("llama3.2-1b-FLM", "npu", ctx_size=4096, pinned=True),
        ]
    }
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert plan.of("pin") == ()


def test_model_on_wrong_silicon_is_warned_not_silently_accepted() -> None:
    """A model advertised as the NPU tier but resident on iGPU is a real defect."""
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "gpu", ctx_size=4096)]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert any("policy expects npu" in w for w in plan.warnings)


# --------------------------- byte budget ---------------------------


def test_load_is_refused_when_it_would_breach_the_ram_reserve() -> None:
    """DISCRIMINATING: an impl ignoring reserve_gb emits the load and fails.

    30GB free with a 24GB reserve leaves 6GB usable; Nemotron needs 21.3GB.
    """
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=30.0)

    assert "Nemotron-3-Nano-30B-A3B-GGUF" not in {a.model for a in plan.of("load")}
    assert any("headroom" in r for r in plan.refused)


def test_load_is_allowed_when_headroom_suffices() -> None:
    """Positive control -- proves the budget guard is not always-refuse."""
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=100.0)
    assert "Nemotron-3-Nano-30B-A3B-GGUF" in {a.model for a in plan.of("load")}


def test_max_resident_ceiling_is_independent_of_free_ram() -> None:
    """Even with limitless RAM, the byte ceiling still binds."""
    policy = ResidencyPolicy(slots=DEFAULT_POLICY.slots, max_resident_gb=8.0)
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, policy=policy, catalog=CATALOG, available_gb=9999.0)
    assert any("headroom" in r for r in plan.refused)


def test_model_absent_from_catalog_is_refused_not_attempted() -> None:
    policy = ResidencyPolicy(
        slots=(SiliconSlot(device="cpu", model="does-not-exist", ctx_size=4096, role="x"),)
    )
    plan = plan_residency(
        parse_census(LIVE_SHAPE, catalog=CATALOG),
        policy=policy,
        catalog=CATALOG,
        available_gb=100.0,
    )
    assert any("not present in the model catalog" in r for r in plan.refused)
    assert plan.of("load") == ()


def test_excessive_ctx_size_is_refused() -> None:
    """KV-cache blow-up guard: the documented Strix Halo hard-hang vector."""
    policy = ResidencyPolicy(
        slots=(SiliconSlot(device="cpu", model="Qwen3-0.6B-GGUF", ctx_size=999_999, role="x"),),
        max_ctx_size=32768,
    )
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "npu")]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG),
        policy=policy,
        catalog=CATALOG,
        available_gb=100.0,
    )
    assert any("exceeds" in r for r in plan.refused)


# --------------------------- hazard surfacing ---------------------------


def test_uncapped_ctx_surfaces_as_warning() -> None:
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "npu", ctx_size=-1)]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert any("no explicit ctx cap" in w for w in plan.warnings)
    assert not any("hard-hang" in w for w in plan.warnings), (
        "ctx_size=-1 must not be reported as the ctx_size=0 crasher"
    )


def test_ctx_zero_surfaces_as_the_hard_hang_vector() -> None:
    """DISCRIMINATING: reporting 0 with the milder wording understates a crasher."""
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "npu", ctx_size=0)]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert any("hard-hang" in w for w in plan.warnings)


def test_watchdog_reset_surfaces_as_warning() -> None:
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "npu", watchdog_reset=True)]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert any("watchdog" in w for w in plan.warnings)


# --------------------------- eviction safety ---------------------------


def test_evictable_candidates_are_lru_ordered() -> None:
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    chosen = evictable_candidates(census, need_gb=0.3)
    assert chosen[0].name == "Qwen3-0.6B-GGUF", "oldest last_use must go first"


def test_busy_model_is_never_an_eviction_candidate() -> None:
    """DISCRIMINATING: dropping the `evictable` filter selects the busy model."""
    payload = {
        "all_models_loaded": [
            _entry("busy-big", "gpu", is_busy=True, last_use=1),
            _entry("idle-small", "gpu", last_use=999),
        ]
    }
    catalog = [{"id": "busy-big", "size": 50.0}, {"id": "idle-small", "size": 1.0}]
    census = parse_census(payload, catalog=catalog)

    chosen = evictable_candidates(census, need_gb=1.0)
    assert [m.name for m in chosen] == ["idle-small"]


def test_insufficient_reclaim_returns_empty_not_partial() -> None:
    """DISCRIMINATING: a partial-return impl evicts models and still fails to fit.

    Evicting without meeting the need is strictly worse than not evicting:
    it destroys warm state and still cannot satisfy the load.
    """
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    assert evictable_candidates(census, need_gb=500.0) == ()


def test_protect_set_excludes_models_even_when_evictable() -> None:
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    chosen = evictable_candidates(census, need_gb=0.3, protect=frozenset({"Qwen3-0.6B-GGUF"}))
    assert "Qwen3-0.6B-GGUF" not in {m.name for m in chosen}


# --------------------------- plan reporting ---------------------------


def test_actions_render_reviewable_cli_commands() -> None:
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    plan = plan_residency(census, catalog=CATALOG, available_gb=100.0)
    cmds = [a.as_command() for a in plan.actions]
    assert any(c.startswith("lemonade load Nemotron") and "--ctx-size" in c for c in cmds)
    assert "lemonade pin llama3.2-1b-FLM" in cmds


def test_default_policy_covers_all_three_silicon_types() -> None:
    assert {s.device for s in DEFAULT_POLICY.slots} == {"npu", "igpu", "cpu"}


def test_default_policy_pins_only_the_tier0_router() -> None:
    pinned = {s.model for s in DEFAULT_POLICY.slots if s.pin}
    assert pinned == {"llama3.2-1b-FLM"}


# ---------------- single-slot contention (measured 2026-08-29) ----------------


def test_t2_single_slot_displacement_is_warned() -> None:
    """DISCRIMINATING: without the check this thrash is silent.

    Measured on live hardware: the NPU holds exactly one model (FastFlowLM owns
    XDNA2 exclusively), and two Cohezion builders in the SAME module want
    different models there -- build_triune_omni_orchestrator wants
    llama3.2-1b-FLM, build_reasoning_orchestrator wants deepseek-r1-8b-FLM.
    Each tier-0 call then paid a 12-20s model swap versus 0.47s resident.

    An impl without single_slot_devices just emits a `load` and says nothing,
    so the ~40x penalty reads as "the NPU tier is inexplicably slow".
    """
    payload = {
        "all_models_loaded": [
            _entry("deepseek-r1-0528-8b-FLM", "npu", ctx_size=16384),
            _entry("Gemma-4-E4B-it-GGUF", "gpu"),
        ]
    }
    catalog = [*CATALOG, {"id": "deepseek-r1-0528-8b-FLM", "size": 5.6}]
    plan = plan_residency(
        parse_census(payload, catalog=catalog), catalog=catalog, available_gb=100.0
    )

    assert any("single-slot" in w and "DISPLACES" in w for w in plan.warnings), (
        f"expected a displacement warning, got {plan.warnings}"
    )
    # It still plans the load -- the warning informs, it does not block.
    assert "llama3.2-1b-FLM" in {a.model for a in plan.of("load")}


def test_t2_no_contention_warning_when_the_right_model_is_resident() -> None:
    """DISCRIMINATING: an always-warn impl fires here and fails."""
    payload = {"all_models_loaded": [_entry("llama3.2-1b-FLM", "npu", ctx_size=4096)]}
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert not any("single-slot" in w for w in plan.warnings)


def test_t2_multi_slot_device_does_not_warn_on_displacement() -> None:
    """iGPU holds several models at once, so a load displaces nothing."""
    payload = {
        "all_models_loaded": [
            _entry("llama3.2-1b-FLM", "npu", ctx_size=4096),
            _entry("Qwen3-0.6B-GGUF", "gpu"),
        ]
    }
    plan = plan_residency(
        parse_census(payload, catalog=CATALOG), catalog=CATALOG, available_gb=100.0
    )
    assert not any("single-slot" in w for w in plan.warnings)


def test_t1_npu_is_the_declared_single_slot_device() -> None:
    assert "npu" in DEFAULT_POLICY.single_slot_devices
    assert "igpu" not in DEFAULT_POLICY.single_slot_devices


# ---------------- the safety asymmetry: additive-only healing ----------------


def test_t1_plan_never_emits_an_evict_action() -> None:
    """SAFETY INVARIANT: no CLI flag can cause an eviction, because no plan
    ever contains one.

    The supervisor's `--apply` / `--heal` gates iterate `plan.of(verb)`. If
    `plan_residency` could emit an "evict" action, a future flag -- or a typo
    widening an existing one -- would be able to destroy warm state that
    another session may be mid-request against. Keeping eviction out of the
    PLAN, rather than out of the applier, makes that structurally impossible
    instead of merely unimplemented.

    DISCRIMINATING: an impl that added eviction to close a byte-budget gap
    fails here, which is the point -- that change must be deliberate.
    """
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)

    for available in (0.0, 5.0, 30.0, 100.0, 9999.0):
        plan = plan_residency(census, catalog=CATALOG, available_gb=available)
        assert plan.of("evict") == (), f"evict emitted at available_gb={available}"
        assert {a.verb for a in plan.actions} <= {"load", "pin"}


def test_t2_starved_silicon_is_healed_by_loading_not_by_evicting() -> None:
    """Under memory pressure the plan REFUSES; it does not free space itself."""
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    tight = plan_residency(census, catalog=CATALOG, available_gb=25.0)

    assert tight.of("evict") == ()
    assert tight.refused, "a load it cannot afford must be refused, not funded by eviction"


def test_evictable_candidates_is_advisory_and_not_wired_into_plans() -> None:
    """`evictable_candidates` exists for a caller that has decided to evict.

    It must remain a separate, explicitly-invoked helper -- never something
    `plan_residency` reaches for on its own.
    """
    census = parse_census(LIVE_SHAPE, catalog=CATALOG)
    assert evictable_candidates(census, need_gb=0.3), "helper still works when called"
    assert plan_residency(census, catalog=CATALOG, available_gb=0.0).of("evict") == ()
