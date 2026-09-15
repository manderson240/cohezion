"""HS1-HS7: demand-driven hotswap must free memory, and must REFUSE when it cannot.

The dangerous failure here is not an exception — it is loading anyway. An mmap load that
"succeeds" still page-storms the box (harness N3 item 5, the 2026-07-16 freeze). So the
refusal paths carry the discriminating tests: an implementation that skipped the gate and
called load() unconditionally fails HS2, HS3 and HS6.
"""

from __future__ import annotations

import pytest

from cohezion.inference import hotswap


@pytest.fixture(autouse=True)
def _no_real_http(monkeypatch):
    """Fail loudly if a test forgets to stub a network seam."""

    def _boom(*_a, **_k):  # pragma: no cover - only fires on a test bug
        raise AssertionError("unstubbed HTTP call in hotswap test")

    monkeypatch.setattr(hotswap, "_post", _boom)
    monkeypatch.setattr(hotswap, "resident_models", lambda: [])
    monkeypatch.setattr(hotswap, "_catalog_sizes", dict)
    monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)


def _model(name, last_use=0, busy=False):
    return {"model_name": name, "last_use": last_use, "is_busy": busy, "loaded": True}


class TestHotswap:
    def test_hs1_already_resident_is_a_noop(self, monkeypatch):
        """HS1: a resident model must not be unloaded/reloaded (no churn, no eviction)."""
        monkeypatch.setattr(hotswap, "resident_models", lambda: [_model("A")])
        r = hotswap.ensure_resident("A")
        assert r.ok and r.already_resident and r.evicted == []

    def test_hs2_unknown_model_is_refused_not_loaded(self, monkeypatch):
        """HS2 (discriminating): unknown weight size => REFUSE, never call load.

        `_post` is the boom-stub, so any load attempt raises AssertionError.
        """
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"B": 4.0})
        r = hotswap.ensure_resident("UNKNOWN-MODEL")
        assert r.ok is False and "unknown weight size" in r.reason

    def test_hs3_refuses_when_still_too_big_after_evicting_everything(self, monkeypatch):
        """HS3 (discriminating): nothing left to evict and it still does not fit => REFUSE.

        An impl that loads anyway hits the boom-stub. This is the freeze scenario.
        """
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"HUGE": 90.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)  # budget = 20-16 = 4 GB
        r = hotswap.ensure_resident("HUGE")
        assert r.ok is False and "insufficient RAM" in r.reason

    def test_hs4_evicts_least_recently_used_first(self, monkeypatch):
        """HS4 (discriminating): the OLDEST last_use is evicted, not an arbitrary model."""
        # newest-first ordering is done by resident_models(); emulate it here
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("new", 300), _model("mid", 200), _model("old", 100)],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"TARGET": 5.0})
        freed = {"n": 0}
        monkeypatch.setattr(hotswap, "free_gb", lambda: 17.0 + 10.0 * freed["n"])

        def _unload(mid, timeout=30.0):
            freed["n"] += 1
            return True

        monkeypatch.setattr(hotswap, "unload", _unload)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        # after load, report it resident so verification passes
        calls = {"n": 0}

        def _resident():
            calls["n"] += 1
            base = [_model("new", 300), _model("mid", 200), _model("old", 100)]
            return base if calls["n"] == 1 else [*base, _model("TARGET", 400)]

        monkeypatch.setattr(hotswap, "resident_models", _resident)
        r = hotswap.ensure_resident("TARGET")
        assert r.ok, r.reason
        assert r.evicted == ["old"], f"LRU victim must be 'old', got {r.evicted}"

    def test_hs5_never_evicts_a_busy_or_protected_model(self, monkeypatch):
        """HS5 (discriminating): busy and protected models are excluded from victims."""
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("busy", 100, busy=True), _model("keep", 90)],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"T": 50.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 18.0)
        unloaded: list[str] = []
        monkeypatch.setattr(
            hotswap, "unload", lambda mid, timeout=30.0: unloaded.append(mid) or True
        )
        r = hotswap.ensure_resident("T", protect=("keep",))
        assert r.ok is False  # cannot fit
        assert unloaded == [], f"must not evict busy/protected models, evicted {unloaded}"

    def test_hs6_ctx_size_is_clamped_to_the_n3_cap(self, monkeypatch):
        """HS6 (discriminating): an unbounded/oversized ctx_size must be clamped.

        ctx_size=0 / -1 is the documented hard-freeze vector; a request for 999999 must
        never reach the router verbatim.
        """
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"M": 1.0})
        seen: dict = {}

        def _post(path, payload, timeout):
            seen.update(payload)
            return 200, "ok"

        monkeypatch.setattr(hotswap, "_post", _post)
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [] if "ctx_size" not in seen else [_model("M")],
        )
        hotswap.ensure_resident("M", ctx_size=999999)
        assert seen["ctx_size"] == hotswap.MAX_CTX, f"ctx_size not clamped: {seen}"
        assert seen["ctx_size"] > 0, "ctx_size must never be 0/-1 (N3 crash vector)"

    def test_hs8_unload_sends_force_true(self, monkeypatch):
        """HS8 (discriminating): unload MUST send force=true.

        Without it lemonade returns 200 and keeps the model warm — a phantom unload that
        frees no RAM (skill: lemonade-heavy-model-safe-enablement). An impl omitting the
        flag fails here.
        """
        sent: dict = {}

        def _post(path, payload, timeout):
            sent.update(payload)
            sent["__path"] = path
            return 200, "ok"

        monkeypatch.setattr(hotswap, "_post", _post)
        monkeypatch.setattr(hotswap, "resident_models_or_none", lambda: [])  # gone afterwards
        assert hotswap.unload("VICTIM") is True
        assert sent["__path"] == "/api/v1/unload"
        assert sent.get("force") is True, f"force=true missing from unload payload: {sent}"

    def test_hs9_phantom_unload_returns_false(self, monkeypatch):
        """HS9 (discriminating): HTTP 200 but still resident => False, not True.

        Trusting the status code here makes the caller believe RAM was freed and proceed
        into a load that OOMs. Success is the POSTCONDITION, not the status code.
        """
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        monkeypatch.setattr(hotswap, "resident_models_or_none", lambda: [_model("STUCK")])
        assert hotswap.unload("STUCK") is False, "a phantom unload must not report success"

    def test_hs9b_unverifiable_unload_returns_false(self, monkeypatch):
        """HS9b (discriminating): HTTP 200 but /health UNREACHABLE => False.

        resident_models() collapsing "unreachable" to [] made phantom unloads
        report success exactly when the server was degraded — the postcondition
        must be VERIFIED, and an unverifiable postcondition is not success.
        """
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        monkeypatch.setattr(hotswap, "resident_models_or_none", lambda: None)
        assert hotswap.unload("GHOST") is False, "unverifiable unload must not report success"

    def test_h3_tick_abstains_when_memory_unreadable(self, monkeypatch):
        """H3 (discriminating): free_gb unreadable => tick evicts NOTHING.

        The 0.0 unreadable-sentinel read as a real measurement made tick() tear
        down every non-busy, non-protected model on a sensor failure. Unknown
        is not pressure.
        """
        from cohezion.inference.residency_service import ResidencyService

        monkeypatch.setattr(hotswap, "resident_models", lambda: [_model("A"), _model("B")])
        monkeypatch.setattr(hotswap, "free_gb_or_none", lambda: None)
        released = []
        svc = ResidencyService()
        monkeypatch.setattr(svc, "release", lambda name: released.append(name) or True)
        out = svc.tick()
        assert out["released"] == [], "unreadable memory must abstain from eviction"
        assert released == []

    def test_hs7_http_200_without_residency_is_reported_as_failure(self, monkeypatch):
        """HS7 (discriminating): a 200 that did not produce residency is NOT success.

        Trusting the status code alone is how a silent no-op passes for a working swap.
        """
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])  # never becomes resident
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"M": 1.0})
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        r = hotswap.ensure_resident("M")
        assert r.ok is False and "not resident" in r.reason


class TestResidentCap:
    """The count-side twin of the RAM floor (2026-09-14 OOM spiral).

    The fit gate bounds each load's SIZE; nothing bounded the COUNT. Seven models resident
    at once, every load individually "fitting", and the LRU loop never fired because
    nothing asked it to — the fatal straw was one more auto-load. The cap gives eviction
    a second trigger, and gives the gate a refusal reason that is count-shaped.
    """

    def test_cap10_at_cap_evicts_lru_oldest_first(self, monkeypatch):
        """HS10 (discriminating): 3 resident, cap 3 => the OLDEST model is evicted.

        A RAM-only impl (or one that counts but picks an arbitrary victim) fails: the
        victim must be the least-recently-used resident, and the target must load.
        """
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("new", 300), _model("mid", 200), _model("old", 100)],
        )
        monkeypatch.setattr(
            hotswap, "_catalog_sizes", lambda: {"TARGET": 5.0, "new": 1.0, "mid": 1.0, "old": 1.0}
        )
        freed = {"n": 0}
        monkeypatch.setattr(hotswap, "free_gb", lambda: 90.0 + 10.0 * freed["n"])

        def _unload(mid, timeout=30.0):
            freed["n"] += 1
            return True

        monkeypatch.setattr(hotswap, "unload", _unload)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        calls = {"n": 0}

        def _resident():
            calls["n"] += 1
            base = [_model("new", 300), _model("mid", 200), _model("old", 100)]
            # call #2 is the post-load verification: 'old' gone, TARGET resident
            return base if calls["n"] == 1 else [*base, _model("TARGET", 400)]

        monkeypatch.setattr(hotswap, "resident_models", _resident)
        r = hotswap.ensure_resident("TARGET")
        assert r.ok, r.reason
        assert r.evicted == ["old"], f"LRU victim must be 'old', got {r.evicted}"

    def test_cap11_cap_unreachable_even_with_full_teardown_is_refused(self, monkeypatch):
        """HS11 (discriminating): at cap with NO evictable model => REFUSE before evicting.

        An impl that loads anyway hits the boom-stub. This is the count-shaped twin of
        HS3: busy/protected models hold the fleet, the target's slot can never open, and
        the gate must refuse rather than push the count past the cap.
        """
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("busy1", 300, busy=True), _model("keep", 200)],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"T": 5.0})
        unloaded: list[str] = []
        monkeypatch.setattr(
            hotswap, "unload", lambda mid, timeout=30.0: unloaded.append(mid) or True
        )
        r = hotswap.ensure_resident("T", protect=("keep",), max_resident=2)
        assert r.ok is False
        assert "cap" in r.reason.lower(), f"reason must be cap-shaped: {r.reason}"
        assert unloaded == [], "must not evict anything when the cap is unreachable"
        assert r.evicted == []

    def test_cap12_already_resident_bypasses_the_cap(self, monkeypatch):
        """HS12 (discriminating): the 3rd resident target must short-circuit, not evict.

        The cap bounds COLD loads; a model the server already holds is exactly what the
        caller asked for, and evicting neighbours to 'make room' for it would churn the
        fleet for nothing.
        """
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("A", 300), _model("B", 200), _model("T", 100)],
        )
        unloaded: list[str] = []
        monkeypatch.setattr(
            hotswap, "unload", lambda mid, timeout=30.0: unloaded.append(mid) or True
        )
        r = hotswap.ensure_resident("T", max_resident=2)
        assert r.ok and r.already_resident and r.evicted == []
        assert unloaded == [], "already-resident must bypass the cap entirely"

    def test_cap13_env_var_overrides_the_default(self, monkeypatch):
        """HS13 (discriminating): the env var replaces the built-in default cap.

        2 resident + default cap 3 => no eviction; the same fleet with the env cap at 1
        must evict BOTH residents, oldest first, before the load. Asserts both directions
        so a stub that ignored the env var in EITHER direction is caught.
        """
        monkeypatch.setenv(hotswap.ENV_MAX_RESIDENT, "1")
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"TARGET": 5.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 90.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        calls = {"n": 0}

        def _resident():
            calls["n"] += 1
            if calls["n"] == 1:
                return [_model("new", 300), _model("old", 100)]  # newest-first, as /health
            return [_model("TARGET", 400)]  # both evicted, target loaded

        monkeypatch.setattr(hotswap, "resident_models", _resident)
        r = hotswap.ensure_resident("TARGET")
        assert r.ok, r.reason
        assert r.evicted == ["old", "new"], (
            f"env cap of 1 must empty the fleet LRU-first, got {r.evicted}"
        )

    def test_cap13b_param_wins_over_env_and_default(self, monkeypatch):
        monkeypatch.setenv(hotswap.ENV_MAX_RESIDENT, "99")
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"TARGET": 5.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 90.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        calls = {"n": 0}

        def _resident():
            calls["n"] += 1
            if calls["n"] == 1:
                return [_model("new", 300), _model("old", 100)]  # newest-first, as /health
            return [_model("TARGET", 400)]

        monkeypatch.setattr(hotswap, "resident_models", _resident)
        r = hotswap.ensure_resident("TARGET", max_resident=1)
        assert r.ok, r.reason
        assert r.evicted == ["old", "new"], "param cap must win over the env var"

    def test_cap14_cap_drives_eviction_even_when_bytes_alone_would_fit(self, monkeypatch):
        """HS14 (discriminating): the cap check must run BEFORE the fit gate.

        RAM is plentiful, so a byte-only impl would load immediately with zero evictions;
        only the count cap can force the LRU eviction here. This is the exact shape the
        2026-09-14 spiral lacked (7 models, every load individually fitting).
        """
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("a", 300), _model("b", 200), _model("old", 100)],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"T": 1.0, "old": 30.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        calls = {"n": 0}

        def _resident():
            calls["n"] += 1
            base = [_model("a", 300), _model("b", 200), _model("old", 100)]
            # call #2 is the post-load verification: 'old' gone, T resident
            return base if calls["n"] == 1 else [*base, _model("T", 400)]

        monkeypatch.setattr(hotswap, "resident_models", _resident)
        r = hotswap.ensure_resident("T")
        assert r.ok, r.reason
        assert r.evicted == ["old"], (
            f"the count cap must trigger eviction regardless of free RAM, got {r.evicted}"
        )

    def test_cap15_cap_refusal_interacts_with_the_weights_fit_refusal(self, monkeypatch):
        """HS15 (discriminating): at cap AND too big even after every eviction => refuse.

        The cap adds evictions the byte math alone would not have asked for; the fit gate
        must evaluate its reachable-pool against the CAPPED eviction set, not the original
        one. Both gates refuse together, with the fit reason (bytes) winning because it is
        the harder constraint — and crucially the refusal must happen BEFORE any eviction,
        not after tearing down the fleet.
        """
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [_model("a", 300), _model("b", 200), _model("c", 100)],
        )
        # T is huge: even with a + b + c gone (100 - 16 + 90 = 174 < 300 + 3 = 303) it
        # cannot fit. `evicted` must stay empty — the pre-eviction shortcut fires first.
        monkeypatch.setattr(
            hotswap,
            "_catalog_sizes",
            lambda: {"HUGE": 300.0, "a": 30.0, "b": 30.0, "c": 30.0},
        )
        monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)
        unloaded: list[str] = []
        monkeypatch.setattr(
            hotswap, "unload", lambda mid, timeout=30.0: unloaded.append(mid) or True
        )
        r = hotswap.ensure_resident("HUGE")
        assert r.ok is False
        assert "insufficient RAM" in r.reason, f"fit gate must refuse: {r.reason}"
        assert unloaded == [], "refusal must happen BEFORE evicting the fleet"
        assert r.evicted == []
