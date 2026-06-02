"""Tests for cohezion.inference.clasp_tier (CLaSp speculative iGPU tier).

Covers CLaSpStats math (acceptance_rate, speedup_vs_verify_only, summary with
its division guards), the module-level get_clasp_stats() singleton, the
build_clasp_igpu_tier() factory (patched to stay offline), and CLaSpTier.run().

KNOWN SOURCE BUG (documented via xfail, not worked around):
    CLaSpTier.run() constructs OrchestrationResult with kwargs ``model=`` and
    ``total_ms=`` which do not exist on the dataclass (it requires
    ``primary_model``/``final_model``/``escalation_count`` and uses
    ``latency_ms``), and reads ``draft_result.model`` which is also absent.
    Every return path of run() therefore raises AttributeError. The three
    tests that assert run()'s *return value* are xfail(strict=True) so they
    flip to XPASS the day run() is fixed. The stat side-effects (total_calls,
    total_draft_ms, total_verify_ms, draft_rejected) all happen *before* the
    crashing construction, so those tests pass by tolerating the raise.
"""

from __future__ import annotations

import inspect

import pytest

import cohezion.inference.clasp_tier as clasp_tier_mod
from cohezion.inference.clasp_tier import (
    CLaSpStats,
    CLaSpTier,
    build_clasp_igpu_tier,
    get_clasp_stats,
)
from cohezion.inference.orchestrator import OrchestrationResult, QualityGate


def _make_result(text: str, *, cost: float = 0.001, ttft: float = 1.0) -> OrchestrationResult:
    """Build a valid OrchestrationResult that fake tiers can return."""
    return OrchestrationResult(
        text=text,
        primary_model="fake",
        final_model="fake",
        escalation_count=0,
        cost_usd=cost,
        ttft_ms=ttft,
    )


class _FakeTier:
    """Minimal tier stub: records call count, returns a fixed result."""

    def __init__(self, text: str, *, cost: float = 0.001) -> None:
        self._text = text
        self._cost = cost
        self.calls = 0

    async def run(self, prompt: str, **_kwargs) -> OrchestrationResult:
        self.calls += 1
        return _make_result(self._text, cost=self._cost)


class _RaisingTier:
    """Tier stub whose run() always raises (simulates unavailable draft)."""

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, prompt: str, **_kwargs) -> OrchestrationResult:
        self.calls += 1
        raise RuntimeError("draft port unavailable")


@pytest.fixture(autouse=True)
def _reset_clasp_stats():
    """conftest does not reset the clasp singleton; do it here for isolation."""
    clasp_tier_mod._clasp_stats = CLaSpStats()
    yield
    clasp_tier_mod._clasp_stats = CLaSpStats()


# --------------------------------------------------------------------------
# CLaSpStats.acceptance_rate
# --------------------------------------------------------------------------
def test_acceptance_rate_zero_calls_returns_zero():
    stats = CLaSpStats()
    assert stats.total_calls == 0
    assert stats.acceptance_rate == 0.0


def test_acceptance_rate_happy_path():
    stats = CLaSpStats(total_calls=10, draft_accepted=6)
    assert stats.acceptance_rate == pytest.approx(0.6)


def test_acceptance_rate_all_accepted_is_one():
    stats = CLaSpStats(total_calls=7, draft_accepted=7)
    assert stats.acceptance_rate == 1.0


def test_acceptance_rate_none_accepted_is_zero():
    stats = CLaSpStats(total_calls=5, draft_accepted=0)
    assert stats.acceptance_rate == 0.0


# --------------------------------------------------------------------------
# CLaSpStats.speedup_vs_verify_only
# --------------------------------------------------------------------------
def test_speedup_zero_calls_returns_one():
    stats = CLaSpStats()
    assert stats.speedup_vs_verify_only == 1.0


def test_speedup_zero_verify_ms_returns_one():
    # total_calls > 0 but no verify time recorded -> neutral default
    stats = CLaSpStats(total_calls=5, total_draft_ms=100.0, total_verify_ms=0.0)
    assert stats.speedup_vs_verify_only == 1.0


def test_speedup_happy_path_value():
    # Known inputs: 10 calls, draft mostly accepted (2 rejected).
    # verify_per_call = total_verify_ms / max(draft_rejected, 1) = 200 / 2 = 100
    # hypothetical_verify_only = total_calls * verify_per_call = 10 * 100 = 1000
    # actual_time = total_draft_ms + total_verify_ms = 50 + 200 = 250
    # speedup = 1000 / max(250, 1.0) = 4.0  (> 1.0, drafting helped)
    stats = CLaSpStats(
        total_calls=10,
        draft_accepted=8,
        draft_rejected=2,
        total_draft_ms=50.0,
        total_verify_ms=200.0,
    )
    assert stats.speedup_vs_verify_only == pytest.approx(4.0)


def test_speedup_draft_rejected_zero_uses_max_guard():
    # draft_rejected == 0 -> max(0, 1) == 1 in verify_per_call; no ZeroDivisionError.
    # verify_per_call = 120 / 1 = 120; hypothetical = 5 * 120 = 600
    # actual = 30 + 120 = 150; speedup = 600 / 150 = 4.0
    stats = CLaSpStats(
        total_calls=5,
        draft_accepted=5,
        draft_rejected=0,
        total_draft_ms=30.0,
        total_verify_ms=120.0,
    )
    value = stats.speedup_vs_verify_only
    import math

    assert math.isfinite(value)
    assert value == pytest.approx(4.0)


def test_speedup_tiny_actual_time_uses_floor_denominator():
    # total_draft_ms + total_verify_ms < 1.0 -> denominator floored at 1.0.
    # verify_per_call = 0.5 / max(1, 1) = 0.5; hypothetical = 3 * 0.5 = 1.5
    # actual = 0.2 + 0.5 = 0.7 < 1.0 -> max(0.7, 1.0) = 1.0
    # speedup = 1.5 / 1.0 = 1.5
    stats = CLaSpStats(
        total_calls=3,
        draft_rejected=1,
        total_draft_ms=0.2,
        total_verify_ms=0.5,
    )
    assert stats.speedup_vs_verify_only == pytest.approx(1.5)


# --------------------------------------------------------------------------
# CLaSpStats.summary
# --------------------------------------------------------------------------
def test_summary_keys_and_rounding():
    stats = CLaSpStats(
        total_calls=3,
        draft_accepted=2,
        draft_rejected=1,
        total_draft_ms=12.34,
        total_verify_ms=200.0,
    )
    summary = stats.summary()
    assert set(summary.keys()) == {
        "total_calls",
        "draft_accepted",
        "acceptance_rate",
        "speedup_vs_verify_only",
        "avg_draft_ms",
    }
    # acceptance_rate = 2/3 = 0.6666... -> rounded to 3 dp
    assert summary["acceptance_rate"] == round(2 / 3, 3)
    assert summary["speedup_vs_verify_only"] == round(stats.speedup_vs_verify_only, 3)
    # avg_draft_ms = 12.34 / 3 -> rounded to 1 dp
    assert summary["avg_draft_ms"] == round(12.34 / 3, 1)


def test_summary_zero_state():
    summary = CLaSpStats().summary()
    assert summary["acceptance_rate"] == 0.0
    assert summary["speedup_vs_verify_only"] == 1.0
    assert summary["avg_draft_ms"] == 0.0


def test_summary_avg_draft_ms_division_guard():
    # total_calls == 0 with nonzero draft_ms: max(total_calls, 1) prevents ZeroDivisionError.
    stats = CLaSpStats(total_calls=0, total_draft_ms=42.0)
    summary = stats.summary()  # must not raise
    assert summary["avg_draft_ms"] == round(42.0 / 1, 1)


# --------------------------------------------------------------------------
# get_clasp_stats() module singleton
# --------------------------------------------------------------------------
def test_get_clasp_stats_returns_module_singleton():
    first = get_clasp_stats()
    second = get_clasp_stats()
    assert first is second
    assert first is clasp_tier_mod._clasp_stats


def test_get_clasp_stats_type():
    assert isinstance(get_clasp_stats(), CLaSpStats)


# --------------------------------------------------------------------------
# build_clasp_igpu_tier() — patched to avoid spinning up real GAIA agents
# --------------------------------------------------------------------------
def _patch_gaia(monkeypatch):
    """Patch build_gaia_native_tier where it is imported (gaia_adapter) and
    record its calls. Returns the list of (args, kwargs) captured."""
    calls: list[tuple[tuple, dict]] = []

    def _fake_build(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeTier("stub")

    monkeypatch.setattr(
        "cohezion.inference.gaia_adapter.build_gaia_native_tier",
        _fake_build,
    )
    return calls


def test_build_clasp_igpu_tier_defaults(monkeypatch):
    _patch_gaia(monkeypatch)
    tier = build_clasp_igpu_tier()
    assert isinstance(tier, CLaSpTier)
    assert tier.draft_gate.min_chars == 200
    assert tier.label.startswith("clasp:")
    assert tier.draft_tier is not None
    assert tier.verify_tier is not None


def test_build_clasp_igpu_tier_custom_acceptance_chars(monkeypatch):
    _patch_gaia(monkeypatch)
    tier = build_clasp_igpu_tier(draft_acceptance_chars=50)
    assert tier.draft_gate.min_chars == 50


def test_build_clasp_igpu_tier_label_from_model_names(monkeypatch):
    _patch_gaia(monkeypatch)
    draft_model = "DraftModelX"
    verify_model = "VerifyModelY"
    tier = build_clasp_igpu_tier(draft_model=draft_model, verify_model=verify_model)
    # Source uses the unicode arrow (→), not "->" — match source ground truth.
    assert tier.label == f"clasp:{draft_model[:6]}→{verify_model[:6]}"


def test_build_clasp_igpu_tier_offline_no_network(monkeypatch):
    calls = _patch_gaia(monkeypatch)
    build_clasp_igpu_tier()
    # build_gaia_native_tier called exactly twice (draft + verify), both with
    # localhost base_url on the expected ports — no live agent/network.
    assert len(calls) == 2
    base_urls = [kwargs.get("base_url") for _args, kwargs in calls]
    assert "http://localhost:13308/v1" in base_urls  # draft
    assert "http://localhost:13307/v1" in base_urls  # verify
    for url in base_urls:
        assert url is not None and "localhost" in url


# --------------------------------------------------------------------------
# CLaSpTier.run()
# --------------------------------------------------------------------------
def test_run_is_async():
    assert inspect.iscoroutinefunction(CLaSpTier.run)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="clasp_tier.run() builds OrchestrationResult with nonexistent "
    "model=/total_ms= kwargs and reads .model; raises AttributeError",
)
async def test_run_accept_path_increments_accepted_and_skips_verify():
    clasp_tier_mod._clasp_stats = CLaSpStats()
    draft = _FakeTier("x" * 300)  # passes gate of 200
    verify = _FakeTier("y" * 900)
    tier = CLaSpTier(draft_tier=draft, verify_tier=verify, draft_gate=QualityGate(min_chars=200))
    result = await tier.run("hello")
    stats = get_clasp_stats()
    assert stats.draft_accepted == 1
    assert verify.calls == 0
    assert result.text == "x" * 300


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="clasp_tier.run() builds OrchestrationResult with nonexistent "
    "model=/total_ms= kwargs; raises AttributeError on verify return path",
)
async def test_run_reject_path_calls_verify_and_increments_rejected():
    clasp_tier_mod._clasp_stats = CLaSpStats()
    draft = _FakeTier("short")  # fails gate of 200
    verify = _FakeTier("y" * 900)
    tier = CLaSpTier(draft_tier=draft, verify_tier=verify, draft_gate=QualityGate(min_chars=200))
    result = await tier.run("hello")
    stats = get_clasp_stats()
    assert verify.calls == 1
    assert stats.draft_rejected == 1
    assert result.text == "y" * 900


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="clasp_tier.run() builds OrchestrationResult with nonexistent "
    "model=/total_ms= kwargs; raises AttributeError on verify return path",
)
async def test_run_draft_exception_increments_unavailable_and_falls_through():
    clasp_tier_mod._clasp_stats = CLaSpStats()
    draft = _RaisingTier()
    verify = _FakeTier("y" * 900, cost=0.002)
    tier = CLaSpTier(draft_tier=draft, verify_tier=verify, draft_gate=QualityGate(min_chars=200))
    result = await tier.run("hello")
    stats = get_clasp_stats()
    assert stats.draft_unavailable == 1
    assert verify.calls == 1
    # draft_result is None, so cost_usd is verify-only (no draft contribution).
    assert result.cost_usd == pytest.approx(0.002)


@pytest.mark.asyncio
async def test_run_increments_total_calls():
    # total_calls is incremented at the top of run(), before any crashing
    # construction. Tolerate the known run() bug and assert the side-effect.
    clasp_tier_mod._clasp_stats = CLaSpStats()
    draft = _FakeTier("short")
    verify = _FakeTier("y" * 900)
    tier = CLaSpTier(draft_tier=draft, verify_tier=verify, draft_gate=QualityGate(min_chars=200))
    try:
        await tier.run("hello")
    except Exception:
        pass  # run() raises AttributeError post-increment (known bug)
    assert get_clasp_stats().total_calls == 1


@pytest.mark.asyncio
async def test_run_accumulates_draft_and_verify_ms():
    # Draft timing (line 123) and verify timing (line 154) both accumulate
    # before run()'s crashing return construction.
    clasp_tier_mod._clasp_stats = CLaSpStats()
    draft = _FakeTier("short")  # reject path: draft + verify both run
    verify = _FakeTier("y" * 900)
    tier = CLaSpTier(draft_tier=draft, verify_tier=verify, draft_gate=QualityGate(min_chars=200))
    try:
        await tier.run("hello")
    except Exception:
        pass  # known run() bug raises after ms accumulation
    stats = get_clasp_stats()
    assert stats.total_draft_ms >= 0.0
    assert stats.total_draft_ms > 0.0
    assert stats.total_verify_ms >= 0.0
    assert stats.total_verify_ms > 0.0
