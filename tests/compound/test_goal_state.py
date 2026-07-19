"""Discriminating tests for durable goal state."""

from __future__ import annotations

import json

import pytest

from cohezion.compound import goal_state as gs


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(gs, "STATE_DIR", tmp_path)
    monkeypatch.setattr(gs, "GOAL_FILE", tmp_path / "goal_state.json")


class TestSetGoal:
    def test_goal_survives_a_restart(self):
        """The whole point: tonight's goal lived only in the hook and died with it."""
        assert gs.set_goal("no more OOM") is True
        assert gs.status()["condition"] == "no more OOM"
        assert json.loads(gs.GOAL_FILE.read_text())["condition"] == "no more OOM"

    def test_empty_condition_rejected(self):
        assert gs.set_goal("  ") is False

    def test_replacing_a_goal_archives_the_old_one(self):
        """Discriminating: an impl that just overwrites loses the record of what was
        pursued and whether it was ever met."""
        gs.set_goal("first goal")
        gs.observe("some evidence")
        gs.set_goal("second goal")
        s = gs.status()
        assert s["condition"] == "second goal"
        assert s["archived"] == 1
        assert json.loads(gs.GOAL_FILE.read_text())["archive"][0]["condition"] == "first goal"

    def test_resetting_the_same_goal_does_not_archive(self):
        gs.set_goal("same")
        gs.set_goal("same")
        assert gs.status()["archived"] == 0


class TestObserve:
    def test_observation_without_a_goal_is_rejected(self):
        assert gs.observe("orphan note") is False

    def test_satisfied_none_records_evidence_without_a_verdict(self):
        """Discriminating and the core of the design: an impl that treats None as False
        makes 'checked, not met' identical to 'never checked' — the exact fail-open
        ambiguity that hid three defects this session."""
        gs.set_goal("no more OOM")
        gs.observe("PSI 0.00 across 401 samples")  # satisfied defaults to None
        s = gs.status()
        assert s["observations"] == 1
        assert s["satisfied"] is False  # verdict unchanged, NOT asserted as met
        assert json.loads(gs.GOAL_FILE.read_text())["observations"][0]["satisfied"] is None

    def test_explicit_satisfied_flips_the_verdict(self):
        gs.set_goal("no more OOM")
        gs.observe("48h clean", satisfied=True)
        assert gs.status()["satisfied"] is True
        assert "satisfied_at" in json.loads(gs.GOAL_FILE.read_text())

    def test_explicit_false_can_reopen_a_satisfied_goal(self):
        """A goal that cannot be reopened would hide a regression."""
        gs.set_goal("no more OOM")
        gs.observe("clean", satisfied=True)
        gs.observe("froze again", satisfied=False)
        assert gs.status()["satisfied"] is False

    def test_observations_are_bounded(self):
        gs.set_goal("long running")
        for i in range(gs.MAX_OBSERVATIONS + 10):
            gs.observe(f"obs {i}")
        assert gs.status()["observations"] == gs.MAX_OBSERVATIONS

    def test_newest_observation_is_kept_when_truncating(self):
        """Discriminating: an impl truncating the WRONG end keeps stale evidence and
        discards the most recent — worse than not truncating."""
        gs.set_goal("g")
        for i in range(gs.MAX_OBSERVATIONS + 5):
            gs.observe(f"obs {i}")
        assert gs.status()["last_note"] == f"obs {gs.MAX_OBSERVATIONS + 4}"


class TestStatus:
    def test_no_goal_returns_empty_condition_not_an_error(self):
        assert gs.status()["condition"] == ""

    def test_corrupt_file_does_not_raise(self):
        gs.GOAL_FILE.write_text("{ broken")
        assert gs.status()["condition"] == ""
