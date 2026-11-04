"""Offline tests for research/artemis2/verifiable_tasks.py (no network, synthetic data).

The builder's value is that it REJECTS tasks: one whose winner does not clear the margin, and one
where the two implementations disagree. Each test below fails if one of those gates is removed.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest


_DIR = Path(__file__).resolve().parents[3] / "research" / "artemis2"
sys.path.insert(0, str(_DIR))
_spec = importlib.util.spec_from_file_location("verifiable_tasks", _DIR / "verifiable_tasks.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)

SPEC = {
    "id": "t", "question": "q", "unit": "u", "tolerance": 0.01, "decimals": 2,
    "margin": 0.1, "relative_margin": False, "sources": [],
}  # fmt: skip


def test_margin_gate_rejects_near_tie():
    """The real SN1105 daily ranges 3.07 vs 3.04 degC must not yield a task at a 0.1 margin."""
    scores = {"2026-04-09": 3.07, "2026-04-10": 3.04}
    rec = vt.make_task(SPEC, (scores, 3.07), (dict(scores), 3.07))
    assert "rejected_because" in rec
    assert rec["checks"]["two_implementations_agree"] is True


def test_clear_winner_is_kept():
    scores = {"a": 5.0, "b": 1.0}
    rec = vt.make_task(SPEC, (scores, 2.5), (dict(scores), 2.5))
    assert "rejected_because" not in rec
    assert (rec["selected_entity"], rec["runner_up"], rec["answer"]) == ("a", "b", 2.5)


def test_disagreeing_implementations_are_rejected():
    scores = {"a": 5.0, "b": 1.0}
    rec = vt.make_task(SPEC, (scores, 2.5), (dict(scores), 2.6))
    assert rec["checks"]["two_implementations_agree"] is False
    assert any("disagree" in r for r in rec["rejected_because"])


def test_implementations_picking_different_entities_are_rejected():
    rec = vt.make_task(SPEC, ({"a": 5.0, "b": 1.0}, 2.5), ({"a": 1.0, "b": 5.0}, 2.5))
    assert any("different entities" in r for r in rec["rejected_because"])


def test_relative_margin():
    assert vt.pick({"a": 12.3, "b": 4.7}, 1.0, relative=True)[2] is True
    assert vt.pick({"a": 565.7, "b": 509.7}, 0.15, relative=True)[2] is False


@pytest.mark.parametrize(("t", "rh"), [(22.0, 25.0), (24.77, 37.1), (-1.5, 80.0)])
def test_stdlib_absolute_humidity_matches_polars(t, rh):
    df = vt.hobo.with_derived(pl.DataFrame({"T": [t], "RH": [rh]}))
    assert vt.std_abs_humidity(t, rh) == pytest.approx(df["AH"][0], rel=1e-12)


def test_stdlib_hobo_reader_matches_polars_reader(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        '#,Date-Time (CDT),"Temperature , deg C","RH , %","Dew Point , deg C"\n'
        "1,04/01/2026 17:35:12,21.13,28.253,2.05\n"
        "2,04/01/2026 17:36:12,21.15,28.300,2.07\n"
    )
    std = vt.std_hobo(p)
    pol = vt.hobo.load(p)
    assert [r[0] for r in std] == list(pol["utc"])
    assert std[0][0] == datetime(2026, 4, 1, 22, 35, 12, tzinfo=UTC)
    assert [r[2] for r in std] == list(pol["RH"])


def test_word_count_drops_editorial_annotations():
    assert vt.words("Copy that [[inaudible]] Houston") == 3
    assert vt.words("  ") == 0


def test_relative_margin_boundary_is_inclusive():
    assert vt.pick({"a": 2.0, "b": 1.0}, 1.0, relative=True)[2] is True
    assert vt.pick({"a": 1.99, "b": 1.0}, 1.0, relative=True)[2] is False


def test_disagreeing_runner_up_scores_are_rejected():
    """Same winner and answer, but the independent runner-up would fail the margin."""
    rec = vt.make_task(SPEC, ({"a": 10.0, "b": 1.0}, 5.0), ({"a": 10.0, "b": 9.95}, 5.0))
    assert rec["checks"]["two_implementations_agree"] is False
    assert any("selection scores" in r for r in rec["rejected_because"])


def test_question_text_matches_the_constants_the_code_uses():
    """A changed launch time or cut threshold must not leave the question text behind."""
    texts = {
        "rh": vt.task_rh_jump.__code__.co_consts,
        "cut": vt.task_largest_cut.__code__.co_consts,
    }
    joined = " ".join(str(c) for consts in texts.values() for c in consts)
    assert vt.LAUNCH.strftime("%Y-%m-%d %H:%M:%S") in joined
    assert vt.SPLASHDOWN.strftime("%Y-%m-%d %H:%M:%S") in joined
    assert f"more than {vt.trn.CUT_S} seconds" in joined


def _hobo_pair(jumps_at: dict[str, list[tuple[datetime, float]]]):
    """Synthetic loggers: flat 20 % RH, 22 degC, with RH steps at given times."""
    from datetime import timedelta

    dfs, raw = {}, {}
    start = vt.LAUNCH - timedelta(minutes=30)
    for sn, steps in jumps_at.items():
        t = [start + timedelta(minutes=i) for i in range(120)]
        rh = [20.0] * 120
        temp = [22.0 + i / 1000 for i in range(120)]
        for when, size in steps:
            i = t.index(when)
            rh[i] += size
        df = pl.DataFrame({"utc": t, "T": temp, "RH": rh}).with_columns(
            pl.col("utc").dt.cast_time_unit("us")
        )
        dfs[sn] = vt.hobo.with_derived(df)
        raw[sn] = list(zip(t, temp, rh, strict=True))
    return dfs, raw


def test_rh_jump_ignores_a_bigger_jump_before_launch():
    from datetime import timedelta

    before = vt.LAUNCH - timedelta(minutes=10)  # on the synthetic minute grid
    during = vt.LAUNCH + timedelta(minutes=20)
    dfs, raw = _hobo_pair({"A": [(before, 50.0), (during, 3.0)], "B": [(during, 10.0)]})
    rec = vt.task_rh_jump(dfs, raw)
    assert rec["selected_entity"] == "B"  # A's 50 % jump was on the pad, not in flight
    assert "rejected_because" not in rec
