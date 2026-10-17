"""RQ: RubricMiddleware must earn the right to gate learning (salted calibration, from GEMS desk 2026-10-16).

  RQ1 qualify() scores the judge on known-good / known-bad outputs by balanced accuracy and sets `qualified`
  RQ2 a judge that FAILS qualification never gates: evaluate() returns passed=True without calling inference
  RQ3 require_qualification=True: an un-qualified (never run) judge never gates either
  RQ4 unparseable answers on gold items count against the judge (fail-open parsing must not inflate its score)
  RQ5 qualification needs both classes (a one-class gold set cannot qualify anything)
Default (require_qualification=False, never qualified) keeps the historic behaviour (MD1-MD7 unchanged).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from cohezion.compound.rubric_middleware import RubricMiddleware


GOLD = [(f"good {i}", "", False) for i in range(4)] + [(f"bad {i}", "", True) for i in range(4)]


def _judge(answer):
    """Patch inference: answer(output) -> perceived_error (True/False) or None for an unparseable reply."""

    def fake(self, task_output, task_context):
        v = answer(task_output)
        return "not json" if v is None else json.dumps({"perceived_error": v, "reason": "r"})

    return patch.object(RubricMiddleware, "_call_inference", fake)


def test_rq1_accurate_judge_qualifies():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: o.startswith("bad")):
        assert rm.qualify(GOLD) == 1.0
    assert rm.qualified is True


def test_rq1_rq2_coin_flip_judge_fails_and_then_never_gates():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: True):  # rejects everything: balanced accuracy 0.5
        assert rm.qualify(GOLD) == 0.5
        assert rm.qualified is False
        v = rm.evaluate("bad output")
    assert v.passed is True and "unqualified" in v.reason


def test_rq2_failed_judge_does_not_call_inference():
    rm = RubricMiddleware(rubric="x")
    rm.qualified = False
    calls = []
    with patch.object(
        RubricMiddleware,
        "_call_inference",
        lambda self, o, c: calls.append(o) or '{"perceived_error": true}',
    ):
        assert rm.evaluate("anything").passed is True
    assert (
        calls == []
    )  # evaluate's fail-open except would hide a raising mock, so count calls instead


def test_rq3_required_but_never_qualified_does_not_gate():
    rm = RubricMiddleware(rubric="x", require_qualification=True)
    with _judge(lambda o: True):
        assert rm.evaluate("bad output").passed is True


def test_rq3_required_and_qualified_does_gate():
    rm = RubricMiddleware(rubric="x", require_qualification=True)
    with _judge(lambda o: o.startswith("bad")):
        rm.qualify(GOLD)
        assert rm.evaluate("bad output").passed is False
        assert rm.evaluate("good output").passed is True


def test_rq4_unparseable_gold_answers_count_against_the_judge():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: None):  # fail-open parse would read every one as "passed"
        assert rm.qualify(GOLD) < 0.8
    assert rm.qualified is False


def test_rq5_one_class_gold_set_cannot_qualify():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: False), pytest.raises(ValueError):
        rm.qualify([g for g in GOLD if not g[2]])


# ── review findings (adversarial pass 2026-10-16) ─────────────────────────────


def test_rq4_unparseable_on_good_items_only_is_not_rescued_by_fail_open():
    """Correct on bad items, 'not json' on good ones: right answer 0.5; a fail-open reader would score 1.0."""
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: True if o.startswith("bad") else None):
        assert rm.qualify(GOLD) == 0.5
    assert rm.qualified is False


def test_rq1_balanced_not_plain_accuracy_on_skewed_gold():
    """2 bad / 9 good, judge passes everything: plain accuracy 0.82 would qualify, balanced is 0.5."""
    gold = [(f"bad {i}", "", True) for i in range(2)] + [(f"good {i}", "", False) for i in range(9)]
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: False):
        assert rm.qualify(gold) == 0.5
    assert rm.qualified is False


def test_rq6_string_perceived_error_is_wrong_not_coerced():
    rm = RubricMiddleware(rubric="x")

    def fake(self, o, c):
        return json.dumps({"perceived_error": "true" if o.startswith("bad") else "false"})

    with patch.object(RubricMiddleware, "_call_inference", fake):
        assert rm.qualify(GOLD) == 0.0


def test_rq5_both_one_class_directions_refused_and_state_untouched():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: o.startswith("bad")):
        for subset in (
            [g for g in GOLD if g[2]],
            [g for g in GOLD if not g[2]],
            GOLD[:1] + GOLD[4:5],
        ):
            with pytest.raises(ValueError):
                rm.qualify(subset)
    assert rm.qualified is None


def test_rq7_threshold_must_exceed_chance():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: True), pytest.raises(ValueError):
        rm.qualify(GOLD, threshold=0.5)


def test_rq7_score_equal_to_threshold_qualifies():
    gold = [(f"bad {i}", "", True) for i in range(5)] + [(f"good {i}", "", False) for i in range(5)]
    rm = RubricMiddleware(rubric="x")
    # bad: 3/5 correct, good: 5/5 -> (0.6 + 1.0) / 2 = 0.8 exactly
    with _judge(lambda o: o in ("bad 0", "bad 1", "bad 2")):
        assert abs(rm.qualify(gold) - 0.8) < 1e-12
    assert rm.qualified is True


def test_rq8_changing_the_judge_after_qualifying_invalidates_it():
    rm = RubricMiddleware(rubric="x", require_qualification=True)
    with _judge(lambda o: o.startswith("bad")):
        rm.qualify(GOLD)
        assert rm.evaluate("bad output").passed is False
        rm.rubric = "a different rubric"
        assert rm.evaluate("bad output").passed is True
    hand = RubricMiddleware(rubric="x", require_qualification=True)
    hand.qualified = True  # set by hand, never measured
    with _judge(lambda o: True):
        assert hand.evaluate("bad output").passed is True


# --- RQ6: rank-based AUC qualification (GEMS desk round qd, 2026-10-17) -------------------------------------------
# An Opus judge ranked its gold set perfectly (AUC 1.00) but its scores sat below a fixed cut, so balanced accuracy
# was 0.50 and it was wrongly disqualified. metric="auc" qualifies the RANKING.


def _scored(score_of, flag=lambda o: False):
    """Patch inference with a judge replying {"perceived_error": flag, "score": score_of(output)}.

    score_of may return a number, None (key omitted) or any raw value (e.g. a string)."""

    def fake(self, task_output, task_context):
        s = score_of(task_output)
        body = {"perceived_error": flag(task_output), "reason": "r"}
        if s is not None:
            body["score"] = s
        return json.dumps(body)

    return patch.object(RubricMiddleware, "_call_inference", fake)


def _rank(o):
    """Perfect ordering, but every score is far below a 0.5 cut: bad i 0.30..0.33, good i 0.01..0.04."""
    i = int(o.split()[1])
    return 0.30 + 0.01 * i if o.startswith("bad") else 0.01 + 0.01 * i


def test_rq6_offset_but_perfect_ranking_fails_balanced_accuracy_and_passes_auc():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank):  # perceived_error always False: the fixed cut never fires
        assert rm.qualify(GOLD) == 0.5
        assert rm.qualified is False
    with _scored(_rank):
        assert rm.qualify(GOLD, metric="auc") == 1.0
    assert rm.qualified is True and rm.is_qualified() is True


def test_rq6_reversed_ranking_fails_auc():
    rm = RubricMiddleware(rubric="x")
    with _scored(lambda o: 1.0 - _rank(o)):
        assert rm.qualify(GOLD, metric="auc") == 0.0
    assert rm.qualified is False


def test_rq6_constant_scores_are_all_ties_and_fail():
    rm = RubricMiddleware(rubric="x")
    with _scored(lambda o: 0.7):
        assert rm.qualify(GOLD, metric="auc") == 0.5
    assert rm.qualified is False


@pytest.mark.parametrize("bad_value", [None, "0.9", True, "nan", [1], float("nan")])
def test_rq6_unusable_score_on_known_bad_lowers_auc_never_raises_it(bad_value):
    rm = RubricMiddleware(rubric="x")
    # Known-bad "bad 0" gets an unusable score: it must rank BELOW every known-good item (worst), costing 4 of 16 pairs.
    with _scored(lambda o: bad_value if o == "bad 0" else _rank(o)):
        assert rm.qualify(GOLD, metric="auc") == pytest.approx(12 / 16)
    assert rm.qualified is False  # 0.75 < 0.8


def test_rq6_infinite_score_is_unusable_not_a_free_win():
    rm = RubricMiddleware(rubric="x")
    # json.dumps emits Infinity for float("inf"); a known-bad item must not buy top rank with it.
    with _scored(lambda o: float("inf") if o == "bad 0" else _rank(o)):
        assert rm.qualify(GOLD, metric="auc") == pytest.approx(12 / 16)


def test_rq6_unusable_score_on_known_good_lowers_auc_never_raises_it():
    rm = RubricMiddleware(rubric="x")
    # Known-good "good 0" with no score ranks ABOVE every known-bad item (most suspicious): 4 of 16 pairs lost.
    with _scored(lambda o: None if o == "good 0" else _rank(o)):
        assert rm.qualify(GOLD, metric="auc") == pytest.approx(12 / 16)


def test_rq6_raising_or_garbage_reply_is_worst_rank():
    rm = RubricMiddleware(rubric="x")

    def fake(self, o, c):
        if o == "bad 1":
            raise RuntimeError("down")
        if o == "bad 2":
            return "not json"
        return json.dumps({"perceived_error": False, "score": _rank(o)})

    with patch.object(RubricMiddleware, "_call_inference", fake):
        assert rm.qualify(GOLD, metric="auc") == pytest.approx(8 / 16)


def test_rq6_ties_between_classes_count_half():
    rm = RubricMiddleware(rubric="x")
    # bad 0 ties good 0 at 0.5 (half a win); good 0 also outranks bad 1-3 (3 losses); all other pairs are wins
    with _scored(lambda o: 0.5 if o in ("bad 0", "good 0") else _rank(o)):
        assert rm.qualify(GOLD, metric="auc") == pytest.approx(12.5 / 16)


def test_rq6_auc_threshold_boundary_and_fingerprint_semantics():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank):
        rm.qualify(GOLD, threshold=1.0, metric="auc")
    assert rm.is_qualified() is True
    rm.rubric = "changed"  # the measurement was of another judge
    assert rm.is_qualified() is False


def test_rq6_auc_mode_asks_the_judge_for_a_score_and_default_mode_does_not():
    rm = RubricMiddleware(rubric="x")
    assert "score" not in rm._build_messages("o", "")[0]["content"]
    seen = []

    def fake(self, o, c):
        seen.append(self._build_messages(o, c)[0]["content"])
        return json.dumps({"perceived_error": False, "score": _rank(o)})

    with patch.object(RubricMiddleware, "_call_inference", fake):
        rm.qualify(GOLD, metric="auc")
    assert seen and all('"score"' in s for s in seen)
    assert "score" not in rm._build_messages("o", "")[0]["content"]  # flag restored


def test_rq6_unknown_metric_and_class_floor_still_enforced():
    rm = RubricMiddleware(rubric="x")
    with pytest.raises(ValueError):
        rm.qualify(GOLD, metric="f1")
    with pytest.raises(ValueError):
        rm.qualify(GOLD[:5], metric="auc")  # one-class set cannot qualify
    with pytest.raises(ValueError):
        rm.qualify(GOLD, threshold=0.5, metric="auc")


def test_rq6_default_mode_is_unchanged_by_scores_in_the_reply():
    rm = RubricMiddleware(rubric="x")
    # a perfect-RANKING judge whose boolean verdicts are right: default mode ignores `score` entirely
    with _scored(lambda o: 0.0, flag=lambda o: o.startswith("bad")):
        assert rm.qualify(GOLD) == 1.0


# --- RQ7: an AUC-qualified judge gates on a LEARNED SCORE CUT, never on its own boolean --------------------------
# AUC never measured `perceived_error`; gating on it after an AUC pass rejected known-good output (adversarial review
# of 553ed02a1). The cut is Youden-optimal on the gold scores (derived from measured outcomes, GEMS lesson 29).


def test_rq7_always_flagging_judge_with_perfect_ranking_does_not_reject_good_output():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank, flag=lambda o: True):  # boolean says "error" for everything
        assert rm.qualify(GOLD, metric="auc") == 1.0
        assert rm.is_qualified() is True
        assert rm.evaluate("good 0").passed is True
        assert rm.evaluate("bad 0").passed is False


def test_rq7_offset_scores_reject_bad_and_pass_good_via_the_learned_cut():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank):  # booleans always False, scores far below 0.5
        rm.qualify(GOLD, metric="auc")
        assert rm.evaluate("bad 2").passed is False
        assert rm.evaluate("good 3").passed is True
    assert rm._score_cut == pytest.approx(0.30)  # not a fixed 0.5


def test_rq7_cut_ties_break_toward_the_higher_cut():
    rm = RubricMiddleware(rubric="x")
    scores = {"bad 0": 0.3, "bad 1": 0.9, "good 0": 0.1, "good 1": 0.6}
    gold = [(k, "", k.startswith("bad")) for k in scores]
    with _scored(lambda o: scores[o]):
        rm.qualify(gold, metric="auc", threshold=0.6)
    assert rm._score_cut == 0.9  # J(0.3) == J(0.9) == 0.5; fewer false rejections wins


def test_rq7_unusable_score_in_evaluate_never_rejects():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank):
        rm.qualify(GOLD, metric="auc")
    for bad_reply in (
        "not json",
        json.dumps({"perceived_error": True}),
        json.dumps({"score": "9"}),
    ):
        with patch.object(RubricMiddleware, "_call_inference", lambda self, o, c, r=bad_reply: r):
            assert rm.evaluate("bad 0").passed is True

    def boom(self, o, c):
        raise RuntimeError("down")

    with patch.object(RubricMiddleware, "_call_inference", boom):
        assert rm.evaluate("bad 0").passed is True


def test_rq7_fingerprint_includes_metric_and_cut():
    rm = RubricMiddleware(rubric="x")
    with _scored(_rank):
        rm.qualify(GOLD, metric="auc")
    assert rm.is_qualified() is True
    rm._score_cut = 0.0  # tampered cut without re-qualifying
    assert rm.is_qualified() is False
    rm._score_cut = 0.30
    assert rm.is_qualified() is True
    rm._metric = "balanced_accuracy"
    assert rm.is_qualified() is False
    with _judge(lambda o: o.startswith("bad")):
        rm.qualify(GOLD)  # re-qualify by balanced accuracy: boolean path, no cut
    assert rm._score_cut is None and rm.is_qualified() is True


def test_rq7_balanced_accuracy_qualification_still_gates_on_the_boolean():
    rm = RubricMiddleware(rubric="x")
    with _judge(lambda o: o.startswith("bad")):
        rm.qualify(GOLD)
        assert rm.evaluate("bad 1").passed is False
        assert rm.evaluate("good 1").passed is True


def test_rq7_evaluate_asks_for_a_score_only_when_auc_qualified():
    rm = RubricMiddleware(rubric="x")
    seen = []

    def fake(self, o, c):
        seen.append('"score"' in self._build_messages(o, c)[0]["content"])
        return json.dumps({"perceived_error": o.startswith("bad"), "score": _rank(o)})

    with patch.object(RubricMiddleware, "_call_inference", fake):
        rm.qualify(GOLD, metric="auc")
        seen.clear()
        rm.evaluate("good 0")
        assert seen == [True]
        assert '"score"' not in rm._build_messages("o", "")[0]["content"]  # flag restored
        rm.qualify(GOLD)  # balanced accuracy: historic prompt in evaluate
        seen.clear()
        rm.evaluate("good 0")
        assert seen == [False]
