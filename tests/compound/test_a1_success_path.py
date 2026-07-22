"""A1 — success-path re-enablement (crash guard) + bounded refinement chain (option b).

Discriminating tests (verification-depth.md corrective #1: test the CLAIM, not the component):
  - the crash test FAILS today (AttributeError) and passes only after the None-guard.
  - the interval test FAILS for a wrong impl that ignores _refine_interval (runs every time).
"""

from __future__ import annotations

from cohezion.compound.skill_refiner import SkillRefiner, SkillRefinerFactory


class TestCrashGuard:
    def test_extract_metrics_explicit_none_token_metrics_does_not_raise(self):
        """The default make_executor()/unconfigured path emits an EXPLICIT token_metrics=None
        (and can emit metrics=None). _extract_metrics must not crash — that AttributeError,
        caught non-blocking, is what silently no-op'd the SUCCESS half of the loop.

        This test raises AttributeError against the pre-fix `.get("token_metrics", {})` impl
        (key present, value None -> None.get(...) explodes)."""
        sr = SkillRefiner()
        m = sr._extract_metrics(
            {
                "success": True,
                "token_metrics": None,  # explicit None, key PRESENT — the failing case
                "metrics": None,
                "duration_seconds": 1.0,
            }
        )
        assert m.success is True
        assert m.tokens_used == 0
        assert m.cached_hits == 0

    def test_extract_metrics_absent_keys_still_works(self):
        """Regression guard: the original absent-key path must still default cleanly."""
        sr = SkillRefiner()
        m = sr._extract_metrics({"success": True, "duration_seconds": 0.5})
        assert m.success is True
        assert m.tokens_used == 0


class TestBoundedRefinementChain:
    def test_interval_three_runs_chain_one_in_three(self):
        """option b: interval N runs the expensive chain on every Nth signal. A wrong impl
        that ignores _refine_interval returns [True]*6 and fails this exact-pattern assertion."""
        sr = SkillRefiner(refine_interval=3)
        pattern = [sr._should_run_refinement_chain() for _ in range(6)]
        assert pattern == [False, False, True, False, False, True]

    def test_interval_one_runs_every_signal(self):
        """Default interval 1 preserves unchanged behavior — every reached refine runs."""
        sr = SkillRefiner(refine_interval=1)
        assert all(sr._should_run_refinement_chain() for _ in range(5))

    def test_interval_floored_at_one(self):
        """A 0/negative interval must not divide-by-zero or disable refinement — floored to 1."""
        sr = SkillRefiner(refine_interval=0)
        assert sr._refine_interval == 1
        assert sr._should_run_refinement_chain() is True

    def test_production_factory_bounds_the_chain(self):
        """The production factory (what make_executor uses) must set a BOUNDED interval (>1),
        so re-enabling the loop does not fire the expensive gates on every default success."""
        refiner = SkillRefinerFactory.create()
        assert refiner._refine_interval > 1
