"""Consumption test: NO caller of the tier-0 id overrides its ctx or backend.

Single ctx authority: lemonade's saved per-model recipe (compound.lemonade_recipes.BASE_RECIPES,
applied by scripts/apply_lemonade_recipes.py) is the only ctx/backend authority for tier 0. Any
caller that loads the tier-0 id with its own ``--ctx-size`` / ``--llamacpp`` / ``ctx_size`` /
``llamacpp_backend`` is a second authority: lemond reloads the model whenever two callers
disagree (the slot thrash moving tier 0 off the NPU exists to remove).

test_tier0_single_ctx_authority.py covers the chat callers (cascade, Flume, CLR). This file
drives the remaining callers' REAL request paths -- autonomous-loop warmup and recovery, the
Quarter-on-a-String "review" lane, and the silicon supervisor's residency plan + --heal
applier -- against a recording fake lemonade / recording subprocess, outbound INET blocked.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest

from cohezion.config.defaults import DEFAULT_TIER0_MODEL
from tests.inference import test_tier0_single_ctx_authority as _auth
from tests.inference.test_tier0_single_ctx_authority import _load_calls


@pytest.fixture
def fake_lemonade_raw(monkeypatch):
    """The recording fake lemonade (outbound INET refused and recorded) for raw-HTTP callers."""
    with _auth._fake_lemonade(monkeypatch, expect_gaia_client=False) as handle:
        yield handle


TIER0 = DEFAULT_TIER0_MODEL
_OVERRIDE_FLAGS = ("--ctx-size", "--llamacpp", "--llamacpp-args", "--ctx")
_OVERRIDE_KEYS = ("ctx_size", "llamacpp_backend", "llamacpp_args", "recipe_options")
REPO = Path(__file__).resolve().parents[2]


def _assert_no_override_argv(argv: list[str]) -> None:
    bad = [a for a in argv if a.split("=", 1)[0] in _OVERRIDE_FLAGS]
    assert not bad, f"tier-0 CLI call pins ctx/backend: {argv}"


def _assert_no_override_body(body: dict) -> None:
    bad = sorted(k for k in _OVERRIDE_KEYS if k in body)
    assert not bad, f"tier-0 request pins ctx/backend {bad}: {body}"


def _tier0_requests(calls):
    return [
        c
        for c in calls
        if c[0] == "POST" and (c[2].get("model") == TIER0 or c[2].get("model_name") == TIER0)
    ]


# ── autonomous loop: warmup + in-flight recovery ─────────────────────────────


def test_warmup_loads_tier0_without_ctx_or_backend(monkeypatch, no_network):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    from cohezion.compound.autonomous_loop import local_executor as le

    argvs: list[list[str]] = []

    class _Done:
        returncode = 0
        stderr = ""

    def _record(cmd, **_kw):
        argvs.append(list(cmd))
        return _Done()

    monkeypatch.setattr(le.subprocess, "run", _record)
    le.warmup_tiers("http://localhost:13305")
    tier0 = [a for a in argvs if TIER0 in a]
    assert tier0, f"warmup never touched tier 0 -- test is vacuous: {argvs}"
    for argv in tier0:
        _assert_no_override_argv(argv)


def test_recover_tier0_reloads_without_ctx_or_backend(fake_lemonade_raw):
    base, calls = fake_lemonade_raw
    from cohezion.compound.autonomous_loop.local_executor import _recover_model

    assert _recover_model(base, TIER0) is True
    loads = [c for c in _load_calls(calls) if c[1].rstrip("/").endswith("/load")]
    assert loads, f"recovery sent no load -- test is vacuous: {calls}"
    for _m, _p, body in _tier0_requests(calls):
        _assert_no_override_body(body)


# ── Quarter-on-a-String "review" lane (direct_tier) ──────────────────────────


def test_quarter_review_lane_uses_saved_recipe(fake_lemonade_raw):
    base, calls = fake_lemonade_raw
    from cohezion.inference.direct_tier import quarter_on_a_string_tier

    tier = quarter_on_a_string_tier("review", port=int(base.rsplit(":", 1)[1]))
    assert tier.model_id == TIER0, "review lane no longer the tier-0 id -- update this test"
    tier._base_url = f"{base}/v1/chat/completions"  # 127.0.0.1, the only host the guard allows
    out = tier.call("Review: is this diff safe?")
    assert out["error"] is None, out["error"]
    reqs = _tier0_requests(calls)
    assert reqs, f"review lane never reached the fake: {calls}"
    for _m, _p, body in reqs:
        _assert_no_override_body(body)
    assert not _load_calls(calls), f"review lane issued load/unload: {_load_calls(calls)}"


# ── silicon supervisor: residency plan + --heal applier ──────────────────────


def _empty_census_plan():
    from cohezion.inference.silicon_policy import DEFAULT_POLICY, plan_residency
    from cohezion.inference.silicon_residency import parse_census

    catalog = [{"id": s.model, "size": 1.0} for s in DEFAULT_POLICY.slots]
    census = parse_census({"all_models_loaded": []}, catalog=catalog)
    return plan_residency(census, catalog=catalog, available_gb=200.0)


def test_policy_tier0_slot_is_tier0_model_with_recipe_ctx():
    from cohezion.inference.silicon_policy import DEFAULT_POLICY

    slots = [s for s in DEFAULT_POLICY.slots if s.model == TIER0]
    assert len(slots) == 1, [s.model for s in DEFAULT_POLICY.slots]
    assert slots[0].ctx_size is None, "the policy must not pin tier-0 ctx (recipe is the authority)"


def test_policy_load_command_for_tier0_has_no_ctx():
    plan = _empty_census_plan()
    loads = [a for a in plan.of("load") if a.model == TIER0]
    assert loads, f"no tier-0 load planned -- test is vacuous: {plan.actions}"
    for action in loads:
        _assert_no_override_argv(action.as_command().split())


def test_supervisor_heal_loads_tier0_without_ctx(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "_silicon_daemon_t0", REPO / "scripts" / "ops" / "silicon_supervisor_daemon.py"
    )
    assert spec is not None and spec.loader is not None
    daemon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daemon)

    argvs: list[list[str]] = []

    async def _record(args, _label):
        argvs.append(list(args))
        return True

    monkeypatch.setattr(daemon, "_run_lemonade", _record)
    asyncio.run(daemon._apply_plan(_empty_census_plan(), apply_pins=False, heal=True, quiet=True))
    tier0 = [a for a in argvs if TIER0 in a]
    assert tier0, f"--heal never loaded tier 0 -- test is vacuous: {argvs}"
    for argv in tier0:
        _assert_no_override_argv(argv)
    # Other slots keep their explicit, policy-bounded ctx.
    assert any("--ctx-size" in a for a in argvs if TIER0 not in a)


@pytest.mark.parametrize("flag", ["--ctx-size", "--llamacpp"])
def test_argv_check_is_discriminating(flag):
    with pytest.raises(AssertionError):
        _assert_no_override_argv(["lemonade", "load", TIER0, flag, "x"])


def test_body_check_is_discriminating():
    with pytest.raises(AssertionError):
        _assert_no_override_body({"model_name": TIER0, "ctx_size": 16384})
