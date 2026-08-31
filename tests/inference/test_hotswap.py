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
