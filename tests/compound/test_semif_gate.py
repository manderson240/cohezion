"""SemIf DQA veto: it must REJECT confabulations, and be INVISIBLE when the judge is unavailable.

A test that only checks "the veto fires" would pass for an implementation that rejects everything,
and one that only checks fail-open would pass for a veto wired to nothing. Both directions are here,
plus a consumption test that goes red if the call site is removed from AutoDQA.evaluate.
"""

from __future__ import annotations

import inspect

import pytest

from cohezion.compound import autodqa as autodqa_mod
from cohezion.compound.autodqa import AutoDQA
from cohezion.compound.semif_gate import semif_veto


# Shaped after the measured confabulation class (a 1B model's confident invented research summary).
# The ACTUAL row scores von=0.873 (accept) / semif=0.0021 (reject) -- verified live 2026-09-22.
# This abridged version scores ABOVE the veto threshold, so it is fixture text for the injected
# scorer only: do not read it as evidence the judge catches every confabulation.
CONFABULATION = (
    "**Action Research Item: SRPO: Setwise Relative Policy Optimization for "
    "Multi-Path Adaptive Network Edge Onloading**\n\nThis work introduces a novel "
    "framework achieving 41% improvement across all benchmarks."
)
REAL_ANSWER = "Paris."
TASK = "What is the capital of France?"


def test_veto_fires_on_a_confident_wrong_answer():
    vetoed, p = semif_veto(TASK, CONFABULATION, scorer=lambda *_: 0.002)
    assert vetoed and p == 0.002


def test_veto_does_not_fire_on_a_correct_answer():
    vetoed, p = semif_veto(TASK, REAL_ANSWER, scorer=lambda *_: 0.991)
    assert not vetoed and p == 0.991


def test_unavailable_judge_is_unknown_not_reject():
    """None must never be read as 0.0: a transport fault is not a verdict."""
    vetoed, p = semif_veto(TASK, CONFABULATION, scorer=lambda *_: None)
    assert vetoed is False and p is None


def test_threshold_boundary_is_strict():
    assert semif_veto(TASK, "x", scorer=lambda *_: 0.3, threshold=0.3)[0] is False
    assert semif_veto(TASK, "x", scorer=lambda *_: 0.29999, threshold=0.3)[0] is True


@pytest.fixture
def dqa():
    return AutoDQA(persist=False, notify_on_reject=False)


def test_autodqa_rejects_when_the_judge_vetoes(dqa, monkeypatch):
    monkeypatch.setattr(autodqa_mod, "semif_veto", lambda *_a, **_k: (True, 0.002))
    r = dqa.evaluate(CONFABULATION, TASK)
    assert not r.verdict.accept
    assert "semif" in r.verdict.reason


def test_autodqa_verdict_is_untouched_when_the_judge_is_down(dqa, monkeypatch):
    """Fail-open must be IDENTICAL to no gate -- same accept AND same score AND same reason."""
    monkeypatch.setattr(autodqa_mod, "semif_veto", lambda *_a, **_k: (False, None))
    down = dqa.evaluate(REAL_ANSWER, TASK).verdict
    monkeypatch.setattr(autodqa_mod, "semif_veto", lambda *_a, **_k: (False, 0.99))
    up_ok = dqa.evaluate(REAL_ANSWER, TASK).verdict
    assert (down.accept, down.score, down.reason) == (up_ok.accept, up_ok.score, up_ok.reason)


def test_veto_can_only_lower_never_raise(dqa, monkeypatch):
    """The judge must not rescue an output the length gate rejected."""
    monkeypatch.setattr(autodqa_mod, "semif_veto", lambda *_a, **_k: (False, 0.999))
    assert not dqa.evaluate("", TASK).verdict.accept


def test_consumption_autodqa_actually_calls_the_gate():
    """Red if the call site is deleted from evaluate() -- the defect this repo keeps catching."""
    src = inspect.getsource(AutoDQA.evaluate)
    assert "semif_veto(" in src, "AutoDQA.evaluate no longer consults the SemIf judge"


def test_sycophancy_invariant_i6_still_holds(dqa, monkeypatch):
    """I6: empty/sycophantic output stays rejected, judge up or down."""
    for ret in ((False, None), (False, 0.99), (True, 0.01)):
        monkeypatch.setattr(autodqa_mod, "semif_veto", lambda *_a, _r=ret, **_k: _r)
        assert not dqa.evaluate("", "analyze this").verdict.accept
