"""Guards for docs/benchmarks/compound_loop/results.ndjson and the verdict rule behind it.

The README cites numbers from this artifact. These tests keep it honest: the file must exist
(the README links it), every (arm, session) record carries the fields the README table is built
from, the per-session counts re-derive from the per-task records, the verdict's poolings equal
the session records, and the claim flag follows from the recorded data by the documented rule.
A hand-edit, a half-written run, or a silent rule change goes red here.

The rule itself is tested with synthetic rows in both directions: it must be able to say True
when treatment genuinely wins, and False when it does not.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
# COMPOUND_LOOP_RESULTS lets a fresh run be validated before it is copied into docs/.
RESULTS = Path(
    os.environ.get(
        "COMPOUND_LOOP_RESULTS",
        REPO_ROOT / "docs" / "benchmarks" / "compound_loop" / "results.ndjson",
    )
)
SCRIPT = REPO_ROOT / "scripts" / "experiments" / "compound_loop_evidence.py"
ARMS = {"treatment", "frozen", "placebo"}

SESSION_FIELDS: dict[str, type | tuple[type, ...]] = {
    "schema_version": int,
    "record_type": str,
    "run_id": str,
    "ts": str,
    "model": str,
    "max_tokens": int,
    "adversarial_gate": str,
    "arm": str,
    "session": int,
    "worker_failed": bool,
    "n_tasks": int,
    "n_tasks_scored": int,
    "excluded_task_ids": list,
    "n_pass": int,
    "n_transport_error": int,
    "n_guardrail_blocked": int,
    "n_output_filtered": int,
    "n_valid": int,
    "pass_rate": (int, float),
    "prompt_tokens": int,
    "completion_tokens": int,
    "wall_s": (int, float),
    "refinements_before": int,
    "refinements_after": int,
    "refinements_added": int,
    "refinements_in_prompt_max": int,
    "refine_calls": int,
    "refine_written": int,
    "blocked": dict,
    "prime_version": str,
    "tasks": list,
}

VERDICT_FIELDS: dict[str, type | tuple[type, ...]] = {
    "schema_version": int,
    "record_type": str,
    "run_id": str,
    "model": str,
    "sessions": int,
    "sessions_planned": int,
    "worker_failures": int,
    "n_tasks": int,
    "n_tasks_scored": int,
    "excluded_task_ids": list,
    "min_valid": int,
    "rule": str,
    "curves_raw": dict,
    "curves_valid": dict,
    "measured_sessions": dict,
    "pooled_valid_measured": dict,
    "pooled_valid_all": dict,
    "pooled_raw": dict,
    "treatment_slope": (int, float),
    "frozen_noise_floor": (int, float),
    "treatment_refinements_total": int,
    "claim_supported": bool,
}


def _script():
    spec = importlib.util.spec_from_file_location("compound_loop_evidence", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load() -> tuple[list[dict], dict]:
    assert RESULTS.exists(), f"{RESULTS} is cited by the README but missing"
    rows = [
        json.loads(line)
        for line in RESULTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sessions = [r for r in rows if r.get("record_type") == "session"]
    verdicts = [r for r in rows if r.get("record_type") == "verdict"]
    assert len(verdicts) == 1, f"expected exactly one verdict record, found {len(verdicts)}"
    assert sessions, "no session records"
    return sessions, verdicts[0]


def _valid(t: dict) -> bool:
    return not (t.get("guardrail_blocked") or t.get("transport_error") or t.get("output_filtered"))


def test_session_records_have_schema_and_recount_from_tasks() -> None:
    sessions, verdict = _load()
    excluded = set(verdict["excluded_task_ids"])
    for row in sessions:
        for key, typ in SESSION_FIELDS.items():
            assert key in row, f"session record missing {key!r}"
            assert isinstance(row[key], typ), f"{key}={row[key]!r} is not {typ}"
        assert row["arm"] in ARMS
        assert row["excluded_task_ids"] == verdict["excluded_task_ids"]
        if row["worker_failed"]:
            assert row["n_valid"] == 0 and row["n_pass"] == 0
            continue
        scored = [t for t in row["tasks"] if t["id"] not in excluded]
        assert len(row["tasks"]) == row["n_tasks"]
        assert row["n_tasks_scored"] == len(scored)
        valid = [t for t in scored if _valid(t)]
        assert row["n_valid"] == len(valid)
        assert row["n_pass"] == sum(1 for t in valid if t["pass"])
        assert all(not t["pass"] for t in scored if not _valid(t)), "invalid call scored a pass"
        assert row["n_transport_error"] == sum(1 for t in scored if t.get("transport_error"))
        assert row["n_guardrail_blocked"] == sum(1 for t in scored if t.get("guardrail_blocked"))
        assert row["n_output_filtered"] == sum(1 for t in scored if t.get("output_filtered"))
        assert abs(row["pass_rate"] - row["n_pass"] / row["n_tasks_scored"]) < 1e-4
        assert row["refinements_added"] == row["refinements_after"] - row["refinements_before"]


def test_every_arm_has_every_session() -> None:
    sessions, verdict = _load()
    for arm in ARMS:
        idx = sorted(r["session"] for r in sessions if r["arm"] == arm)
        assert idx == list(range(verdict["sessions"])), f"{arm}: sessions {idx}"
    assert verdict["sessions"] <= verdict["sessions_planned"]


def _pool(rows: list[dict]) -> float | None:
    v = sum(r["n_valid"] for r in rows)
    return round(sum(r["n_pass"] for r in rows) / v, 4) if v else None


def test_verdict_matches_session_records() -> None:
    sessions, v = _load()
    for key, typ in VERDICT_FIELDS.items():
        assert key in v, f"verdict missing {key!r}"
        assert isinstance(v[key], typ), f"{key}={v[key]!r} is not {typ}"
    ordered = sorted(sessions, key=lambda r: r["session"])
    for arm in ARMS:
        rows = [r for r in ordered if r["arm"] == arm]
        live = [r for r in rows if not r["worker_failed"]]
        meas = [r for r in live if r["n_valid"] >= v["min_valid"]]
        assert v["measured_sessions"][arm] == [r["session"] for r in meas]
        assert v["pooled_valid_measured"][arm] == _pool(meas), f"{arm}: measured pooling"
        assert v["pooled_valid_all"][arm] == _pool(live), f"{arm}: all-valid pooling"
        scored = sum(r["n_tasks_scored"] for r in live)
        raw = round(sum(r["n_pass"] for r in live) / scored, 4) if scored else None
        assert v["pooled_raw"][arm] == raw, f"{arm}: raw pooling"
        assert v["curves_raw"][arm] == [r["pass_rate"] for r in rows]
        for r, cv in zip(rows, v["curves_valid"][arm], strict=True):
            if r in meas:
                assert cv == round(r["n_pass"] / r["n_valid"], 4)
            else:
                assert cv is None
    # The frozen arm is the no-intervention control: its skill file must never change.
    assert all(r["refinements_added"] == 0 for r in ordered if r["arm"] == "frozen")
    # The placebo arm must mirror the treatment arm's prompt growth session by session.
    by = {(r["arm"], r["session"]): r for r in sessions}
    for s in range(v["sessions"]):
        assert by[("placebo", s)]["refinements_added"] == by[("treatment", s)]["refinements_added"]


def test_verdict_rule_is_reproducible_from_records() -> None:
    """The claim flag must follow from the recorded data, not from a hand edit."""
    _, v = _load()
    t = [x for x in v["curves_valid"]["treatment"] if x is not None]
    f = [x for x in v["curves_valid"]["frozen"] if x is not None]
    noise = (max(f) - min(f)) if len(f) >= 2 else 0.0
    assert abs(v["frozen_noise_floor"] - noise) < 1e-6
    n = len(t)
    if n >= 2:
        xbar = (n - 1) / 2
        ybar = sum(t) / n
        slope = sum((i - xbar) * (t[i] - ybar) for i in range(n)) / sum(
            (i - xbar) ** 2 for i in range(n)
        )
        assert abs(v["treatment_slope"] - slope) < 1e-4
    p = v["pooled_valid_measured"]
    expected = (
        n >= 2
        and None not in (p["treatment"], p["frozen"], p["placebo"])
        and v["treatment_slope"] >= 0
        and p["treatment"] - p["frozen"] > noise
        and p["treatment"] - p["placebo"] > noise
    )
    assert v["claim_supported"] is bool(expected)


# ───────────────────── the rule itself, on synthetic rows ─────────────────────


def _row(arm: str, session: int, n_pass: int, n_valid: int, failed: bool = False) -> dict:
    return {
        "record_type": "session",
        "run_id": "synthetic",
        "model": "m",
        "max_tokens": 1,
        "adversarial_gate": "fail-open",
        "arm": arm,
        "session": session,
        "worker_failed": failed,
        "n_tasks": 16,
        "n_tasks_scored": 16,
        "excluded_task_ids": [],
        "n_pass": n_pass,
        "n_valid": n_valid,
        "pass_rate": round(n_pass / 16, 4),
        "refinements_after": 5 if arm != "frozen" else 0,
    }


def _rows(spec: dict[str, list[tuple[int, int]]]) -> list[dict]:
    return [_row(arm, s, p, v) for arm, pts in spec.items() for s, (p, v) in enumerate(pts)]


def test_rule_can_return_true_when_treatment_really_wins() -> None:
    mod = _script()
    rows = _rows(
        {
            "treatment": [(10, 16), (13, 16), (15, 16)],
            "frozen": [(8, 16), (8, 16), (8, 16)],
            "placebo": [(8, 16), (9, 16), (8, 16)],
        }
    )
    v = mod.compute_verdict(rows, sessions_planned=3, run_id="synthetic")
    assert v["claim_supported"] is True
    assert v["frozen_noise_floor"] == 0.0


def test_rule_returns_false_when_placebo_matches_treatment() -> None:
    mod = _script()
    rows = _rows(
        {
            "treatment": [(14, 16), (14, 16), (15, 16)],
            "frozen": [(6, 16), (8, 16), (9, 16)],
            "placebo": [(14, 16), (15, 16), (14, 16)],
        }
    )
    v = mod.compute_verdict(rows, sessions_planned=3, run_id="synthetic")
    assert v["claim_supported"] is False


def test_killed_worker_is_unmeasured_not_a_zero_session() -> None:
    """A SIGKILLed worker must not enter the curve as 0/16 (it would fake a collapse)."""
    mod = _script()
    rows = _rows(
        {
            "treatment": [(14, 16), (15, 16)],
            "frozen": [(8, 16), (8, 16)],
            "placebo": [(8, 16), (8, 16)],
        }
    )
    rows.append(_row("treatment", 2, 0, 0, failed=True))
    rows.append(_row("frozen", 2, 8, 16))
    rows.append(_row("placebo", 2, 8, 16))
    v = mod.compute_verdict(rows, sessions_planned=3, run_id="synthetic")
    assert v["measured_sessions"]["treatment"] == [0, 1]
    assert v["curves_valid"]["treatment"][2] is None
    assert v["pooled_valid_measured"]["treatment"] == round(29 / 32, 4)
    assert v["worker_failures"] == 1
    assert v["claim_supported"] is True


def test_unmeasured_sessions_are_excluded_from_the_verdict_pool() -> None:
    mod = _script()
    rows = _rows(
        {
            "treatment": [(14, 16), (14, 16)],
            "frozen": [(8, 16), (8, 16)],
            "placebo": [(2, 3), (14, 16)],  # session 0 has only 3 valid calls
        }
    )
    v = mod.compute_verdict(rows, sessions_planned=2, run_id="synthetic")
    assert v["measured_sessions"]["placebo"] == [1]
    assert v["pooled_valid_measured"]["placebo"] == round(14 / 16, 4)
    assert v["pooled_valid_all"]["placebo"] == round(16 / 19, 4)


def test_output_filter_block_is_not_a_valid_call() -> None:
    mod = _script()
    tasks = [
        {"id": "a", "pass": True},
        {"id": "b", "pass": False, "output_filtered": True},
        {"id": "c", "pass": False, "transport_error": "HTTP 503"},
        {"id": "d", "pass": False, "guardrail_blocked": True},
        {"id": "e", "pass": False},
    ]
    counts = mod.recount(tasks, 5, ())
    assert counts["n_valid"] == 2 and counts["n_pass"] == 1
    assert counts["n_output_filtered"] == 1
    assert counts["pass_rate_valid"] == 0.5
    assert mod.recount(tasks, 5, ("e",))["n_tasks_scored"] == 4


@pytest.mark.parametrize(
    ("text", "expected", "want"),
    [
        (
            "A sorting algorithm is asked to repeatedly merge sorted sublists.",
            ("merge sort", "mergesort"),
            0.0,
        ),
        ("That is Merge Sort.", ("merge sort", "mergesort"), 1.0),
        ("Error 4040 is not it", ("404",), 0.0),
        ("the class keyword", ("ss",), 0.0),
    ],
)
def test_scorer_is_whole_token(text: str, expected: tuple[str, ...], want: float) -> None:
    mod = _script()
    assert mod.score_answer(text, expected) == want
