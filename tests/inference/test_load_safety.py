"""Tests for the freeze-prevention load-safety guard (``load_safety``).

These are pure-function tests — no network, no /proc dependency beyond a single
sanity read — so they run offline in CI. The scenarios encode the 2026-07-16
hard-freeze: Mistral-Medium-128B IQ4_XS reported catalog ``size=42.3`` GB but
its real footprint was ~69 GB, and the existing RAM-floor-only gate approved it
because free RAM was above the floor. The guard must:

  a. REFUSE the freeze scenario (42.3 GB catalog x1.7 = 71.9 GB > 60-16 budget),
  b. REFUSE an unknown/None size (unknown != fits — the critical bypass),
  c. ADMIT an FLM-recipe model that reports no size (bounded nominal),
  d. ADMIT a small known model,
  e. subtract the RAM_FLOOR_GB reserve from the available budget.
"""

from __future__ import annotations

from cohezion.inference.load_safety import (
    RAM_FLOOR_GB,
    SIZE_SAFETY_FACTOR,
    available_ram_gb,
    check_load_safe,
    effective_size_gb,
)


class TestEffectiveSizeGb:
    def test_known_size_is_inflated_by_safety_factor(self):
        # Catalog size understates real footprint — inflate by SIZE_SAFETY_FACTOR.
        assert effective_size_gb({"size": 42.3}) == 42.3 * SIZE_SAFETY_FACTOR

    def test_accepts_size_gb_key_alias(self):
        # ModelEntry uses ``size_gb``; the catalog uses ``size`` — both accepted.
        assert effective_size_gb({"size_gb": 4.6}) == 4.6 * SIZE_SAFETY_FACTOR

    def test_unknown_size_is_none_not_zero(self):
        # None must propagate as None (unknown), never collapse to 0.0 ("fits").
        assert effective_size_gb({"size": None}) is None
        assert effective_size_gb({"size": 0}) is None
        assert effective_size_gb({}) is None

    def test_flm_recipe_without_size_gets_bounded_nominal(self):
        # Sub-8B NPU FLM models carry no catalog size; give them a bounded nominal.
        est = effective_size_gb({"size": None, "recipe": "flm"})
        assert est is not None
        assert est == 6.0 * SIZE_SAFETY_FACTOR

    def test_runtime_backend_key_alias_for_recipe(self):
        est = effective_size_gb({"size_gb": None, "runtime_backend": "flm"})
        assert est == 6.0 * SIZE_SAFETY_FACTOR


class TestCheckLoadSafe:
    def test_a_freeze_scenario_refuses(self):
        # 42.3 * 1.7 = 71.9 GB est > (60 - 16) = 44 GB budget => REFUSE.
        ok, reason = check_load_safe({"size": 42.3}, available_gb=60.0)
        assert ok is False
        assert "71" in reason or "footprint" in reason.lower()

    def test_b_unknown_size_refuses(self):
        ok, reason = check_load_safe({"size": None}, available_gb=60.0)
        assert ok is False
        assert "unknown" in reason.lower() or "unverifiable" in reason.lower()

    def test_c_flm_recipe_none_size_passes(self):
        # Bounded nominal 6.0 * 1.7 = 10.2 GB <= 44 GB budget => OK.
        ok, reason = check_load_safe({"size": None, "recipe": "flm"}, available_gb=60.0)
        assert ok is True, reason

    def test_d_small_known_model_passes(self):
        # 2.9 * 1.7 = 4.93 GB <= 44 GB budget => OK.
        ok, reason = check_load_safe({"size": 2.9}, available_gb=60.0)
        assert ok is True, reason

    def test_e_floor_reserve_is_subtracted(self):
        # Budget = available - RAM_FLOOR_GB. At available=60, budget=44.
        # size=25 -> est=42.5 <= 44 => OK. size=26 -> est=44.2 > 44 => REFUSE,
        # even though 44.2 < 60 (would "fit" without the floor).
        assert RAM_FLOOR_GB == 16.0
        ok_fits, _ = check_load_safe({"size": 25.0}, available_gb=60.0)
        ok_floor, reason = check_load_safe({"size": 26.0}, available_gb=60.0)
        assert ok_fits is True
        assert ok_floor is False
        assert "floor" in reason.lower() or "16" in reason


def test_available_ram_gb_reads_a_positive_float():
    # Sanity: the impure helper reads /proc/meminfo and returns a plausible value.
    val = available_ram_gb()
    assert isinstance(val, float)
    assert val >= 0.0


class TestPreLoadGateWiring:
    """Proves the guard is LIVE in oom_guard.pre_load_gate (not an orphan).

    This is the documented, publicly-exported "call before POST /api/v1/load"
    gate — the real site the 2026-07-16 freeze bypassed.
    """

    def test_freeze_model_refused_by_gate(self, monkeypatch):
        from cohezion.inference import oom_guard

        # Router catalog reports the freeze model with its (understated) size.
        monkeypatch.setattr(
            oom_guard,
            "_get_catalog",
            lambda *a, **k: [{"model_name": "Mistral-Medium-3.5-128B", "size": 42.3}],
        )
        # Plenty above the floor — the OLD gate would have APPROVED this.
        monkeypatch.setattr(oom_guard, "check_ram", lambda *a, **k: (True, 60.0))

        allowed, reason = oom_guard.pre_load_gate(
            "Mistral-Medium-3.5-128B", ctx_size=16384, min_free_gb=20.0
        )
        assert allowed is False
        assert "over-commit" in reason

    def test_small_model_still_allowed_by_gate(self, monkeypatch):
        from cohezion.inference import oom_guard

        monkeypatch.setattr(
            oom_guard,
            "_get_catalog",
            lambda *a, **k: [{"model_name": "Gemma-4-E4B-it-GGUF", "size": 4.6}],
        )
        monkeypatch.setattr(oom_guard, "check_ram", lambda *a, **k: (True, 60.0))

        allowed, reason = oom_guard.pre_load_gate(
            "Gemma-4-E4B-it-GGUF", ctx_size=16384, min_free_gb=20.0
        )
        assert allowed is True, reason
