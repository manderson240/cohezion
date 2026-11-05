"""Offline tests for research/artemis2/study_goals.py.

The goals layer is only worth having if a goal FAILS when its claim stops holding. Each test
breaks one claim or one loop mechanism and checks that the goal reports it.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest


_DIR = Path(__file__).resolve().parents[3] / "research" / "artemis2"
_spec = importlib.util.spec_from_file_location("study_goals", _DIR / "study_goals.py")
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)


class FakeStudy:
    def __init__(self, hobo=None):
        self.cache = {}
        self._hobo = hobo

    def hobo(self):
        return self._hobo


def _run(checks, factory=FakeStudy, max_cycles=2):
    orch = sg.GoalsAndLoopsOrchestrator()
    spec = ("g", "title", "objective", checks, False)
    return asyncio.run(sg.run_goal(orch, spec, factory, max_cycles))


def _hobo(pad: float, flight: float) -> dict:
    return {
        "SN1104": {"abs_humidity_by_phase_gm3": {"1 pre-launch (pad)": pad, "2 flight": flight}}
    }


def test_dry_locker_claim_holds_on_real_values():
    assert sg.locker_dry_in_flight(FakeStudy(_hobo(5.07, 5.11)))[0] is True


def test_dry_locker_claim_fails_when_flight_was_humid():
    ok, evidence = sg.locker_dry_in_flight(FakeStudy(_hobo(5.07, 9.0)))
    assert ok is False
    assert "9.0" in evidence


def test_far_side_claim_fails_if_a_flash_moves_onto_the_near_side(monkeypatch):
    flashes = {"1": {"models": {"A": {"lon_E": 140.0, "lat": -20.0}, "B": {"lon_E": 141.0, "lat": -20.0}}},
               "2": {"models": {"A": {"lon_E": 95.0, "lat": -15.0}, "B": {"lon_E": 96.0, "lat": -15.0}}},
               "3": {"models": None}}  # fmt: skip
    data = {"flashes": flashes, "earth_view": {"sub_lon": 359.18, "sub_lat": 6.72}}
    monkeypatch.setattr(sg, "committed", lambda name: data)
    ok, evidence = sg.flashes_far_side(None)
    assert ok is False
    assert "'2': 7.3" in evidence  # 7.3 deg beyond the limb, short of the required 10


def test_far_side_claim_holds_on_the_committed_map():
    assert sg.flashes_far_side(None)[0] is True


def test_goal_is_satisfied_only_when_every_criterion_passes():
    out = _run(
        [("A", "passes", lambda s: (True, "fine")), ("B", "fails", lambda s: (False, "broken"))]
    )
    assert out["status"] == "blocked"
    assert out["cycles"] == 2
    assert [c["verified"] for c in out["criteria"]] == [True, False]
    assert out["criteria"][1]["evidence"] == "broken"


def test_transient_failure_converges_on_a_later_cycle_with_a_fresh_study():
    made = []

    def factory():
        made.append(FakeStudy())
        return made[-1]

    def flaky(s):
        return (len(made) >= 2, f"study #{len(made)}")

    out = _run([("A", "flaky", flaky)], factory=factory)
    assert out["status"] == "satisfied"
    assert out["cycles"] == 2
    assert made[0] is not made[1]  # each cycle recomputes instead of reusing the first result


def test_a_crashing_check_is_recorded_not_raised():
    def boom(s):
        raise KeyError("missing field")

    out = _run([("A", "crashes", boom)], max_cycles=1)
    assert out["status"] == "blocked"
    assert out["criteria"][0]["evidence"].startswith("KeyError")


@pytest.mark.parametrize("goal", sg.GOALS, ids=[g[0] for g in sg.GOALS])
def test_every_goal_has_distinct_criteria_ids(goal):
    ids = [cid for cid, _d, _fn in goal[3]]
    assert ids and len(ids) == len(set(ids))


def test_rotation_check_fails_if_flash_1_is_far_from_the_view_centre(monkeypatch):
    real = sg.committed("flash_annotations.json")
    moved = {**real, "flashes": {**real["flashes"]}}
    moved["flashes"]["1"] = {"models": {"A": {"lon_E": 123.0, "lat": -50.0}}}  # ~46 deg from centre
    monkeypatch.setattr(sg, "committed", lambda name: moved)
    ok, evidence = sg.flashes_far_side_any_rotation(None)
    assert ok is False
    assert "'1': 46" in evidence


def test_rotation_check_passes_on_the_committed_map():
    assert sg.flashes_far_side_any_rotation(None)[0] is True


def test_writeup_check_fails_when_the_json_no_longer_supports_a_phrase(monkeypatch):
    monkeypatch.setattr(sg, "README_REGISTER", [("6,355", lambda: False)])
    ok, evidence = sg.readme_numbers_trace(None)
    assert ok is False
    assert "6,355" in evidence


def test_writeup_check_fails_when_the_phrase_left_the_readme(monkeypatch):
    monkeypatch.setattr(sg, "README_REGISTER", [("a phrase the README never says", lambda: True)])
    assert sg.readme_numbers_trace(None)[0] is False


def test_writeup_register_holds_on_the_committed_files():
    ok, evidence = sg.readme_numbers_trace(None)
    assert ok, evidence


def test_trajectory_check_fails_if_spice_and_horizons_disagree(monkeypatch):
    d = {"orion_sub_lon_deg": 0.3, "orion_sub_lat_deg": 0.0, "orion_range_km": 1.0,
         "earth_sub_lon_deg": 0.0, "note": ""}  # fmt: skip
    monkeypatch.setattr(sg, "committed", lambda name: {"horizons_cross_check": d})
    assert sg.trajectory_matches_horizons(None)[0] is False


def test_trajectory_check_passes_on_the_committed_map():
    ok, evidence = sg.trajectory_matches_horizons(None)
    assert ok, evidence
