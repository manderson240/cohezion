"""Tests for the work-queue triage hop.

The load-bearing property is FAIL-SAFE: every failure mode must DEFER, never promote. A
wrong APPLY injects noise into an autonomous execution chain, so "leave it for next pass"
is always the safe answer. Several tests exist specifically to prove a plausible-but-wrong
implementation (one that guesses a verdict) would fail.
"""

from __future__ import annotations

from typing import Any

import pytest

from cohezion.actioner.triage import (
    TriageResult,
    classify_item,
    is_degenerate,
    parse_verdict,
    triage,
)


pytestmark = pytest.mark.unit


class _FakeAPI:
    def __init__(self, pending: list[dict[str, Any]] | None = None, fail_patch: bool = False):
        self._pending = pending or []
        self.fail_patch = fail_patch
        self.promoted: list[tuple[str, str]] = []

    def pending_items(self) -> list[dict[str, Any]]:
        return list(self._pending)

    def mark_reviewed(self, item_id: str, relevance: str, note: str) -> dict:
        if self.fail_patch:
            raise RuntimeError("PATCH failed")
        self.promoted.append((item_id, relevance))
        return {"id": item_id}


def _card(i: str = "a1", **kw) -> dict[str, Any]:
    return {"id": i, "type": "improvement", "title": "t", "description": "d", **kw}


class TestParseVerdict:
    def test_extracts_single_verdict(self) -> None:
        assert parse_verdict("APPLY") == "APPLY"
        assert parse_verdict("  monitor\n") == "MONITOR"

    def test_absent_verdict_returns_none(self) -> None:
        assert parse_verdict("I am not sure about this card") is None

    def test_ambiguous_reply_returns_none(self) -> None:
        # Two DIFFERENT verdicts = nothing was classified. An implementation that takes the
        # first match would return "APPLY" here and silently invent a decision.
        assert parse_verdict("APPLY or maybe SKIP") is None

    def test_repeated_same_verdict_is_not_ambiguous(self) -> None:
        assert parse_verdict("SKIP. Definitely SKIP.") == "SKIP"

    def test_does_not_match_inside_a_longer_word(self) -> None:
        # Substring matching would fire on "APPLYING" and misclassify.
        assert parse_verdict("we are APPLYING pressure") is None


class TestIsDegenerate:
    def test_one_word_reply_is_not_degenerate(self) -> None:
        # A single word is the CORRECT shape for this task; shortness must not be penalised.
        assert is_degenerate("APPLY") is None

    def test_normal_prose_passes(self) -> None:
        assert is_degenerate("This is a normal sentence with a reasonable set of words.") is None

    def test_repetition_loop_is_caught(self) -> None:
        assert is_degenerate("l l l " * 60) is not None

    def test_long_gibberish_without_function_words_is_caught(self) -> None:
        assert is_degenerate(" ".join(f"zx{i}qq" for i in range(40))) is not None


class TestClassifyItem:
    def test_happy_path(self) -> None:
        r = classify_item(_card(), lambda _p: "APPLY")
        assert r.verdict == "APPLY" and not r.deferred

    def test_inference_exception_defers(self) -> None:
        def boom(_p: str) -> str:
            raise ConnectionError("router down")

        r = classify_item(_card(), boom)
        assert r.deferred and "inference failed" in r.reason

    def test_empty_reply_defers(self) -> None:
        assert classify_item(_card(), lambda _p: "   ").deferred

    def test_degenerate_reply_defers(self) -> None:
        r = classify_item(_card(), lambda _p: "l l l " * 60)
        assert r.deferred and "degenerate" in r.reason

    def test_unparseable_reply_defers(self) -> None:
        r = classify_item(_card(), lambda _p: "it depends on several factors")
        assert r.deferred and "unparseable" in r.reason

    def test_ambiguous_reply_defers(self) -> None:
        assert classify_item(_card(), lambda _p: "APPLY or SKIP").deferred

    def test_card_content_is_passed_to_the_model(self) -> None:
        seen: list[str] = []

        def spy(p: str) -> str:
            seen.append(p)
            return "MONITOR"

        classify_item(_card(title="UNIQUE-TITLE-XYZ"), spy)
        assert "UNIQUE-TITLE-XYZ" in seen[0]


class TestTriage:
    def test_dry_run_promotes_nothing(self) -> None:
        api = _FakeAPI([_card("a"), _card("b")])
        out = triage(api, lambda _p: "APPLY", dry_run=True)
        assert out["promoted"] == 0
        assert api.promoted == [], "dry run must not mutate the queue"

    def test_wet_run_promotes_decided_items(self) -> None:
        api = _FakeAPI([_card("a"), _card("b")])
        out = triage(api, lambda _p: "APPLY", dry_run=False)
        assert out["promoted"] == 2
        assert api.promoted == [("a", "APPLY"), ("b", "APPLY")]

    def test_deferred_items_are_NOT_promoted(self) -> None:
        """The core safety property.

        An implementation that guessed a default verdict on unparseable output would
        promote here, so this fails against exactly the wrong-but-plausible version.
        """
        api = _FakeAPI([_card("a"), _card("b")])
        out = triage(api, lambda _p: "no idea", dry_run=False)
        assert out["promoted"] == 0
        assert out["deferred"] == 2
        assert api.promoted == []

    def test_relevance_written_matches_the_verdict(self) -> None:
        api = _FakeAPI([_card("a")])
        triage(api, lambda _p: "SKIP", dry_run=False)
        assert api.promoted == [("a", "SKIP")], "must not hardcode a relevance"

    def test_limit_is_respected(self) -> None:
        api = _FakeAPI([_card(str(i)) for i in range(10)])
        out = triage(api, lambda _p: "APPLY", limit=3, dry_run=False)
        assert out["promoted"] == 3

    def test_queue_read_failure_returns_empty_without_raising(self) -> None:
        class Broken:
            def pending_items(self):
                raise RuntimeError("queue unreachable")

            def mark_reviewed(self, *a, **k):
                raise AssertionError("must not be called")

        out = triage(Broken(), lambda _p: "APPLY", dry_run=False)
        assert out["promoted"] == 0 and "error" in out

    def test_one_failed_patch_does_not_abort_the_pass(self) -> None:
        api = _FakeAPI([_card("a"), _card("b")], fail_patch=True)
        out = triage(api, lambda _p: "APPLY", dry_run=False)
        assert out["promoted"] == 0  # both failed, but no exception escaped

    def test_empty_queue_is_a_no_op(self) -> None:
        out = triage(_FakeAPI([]), lambda _p: "APPLY", dry_run=False)
        assert out == {"promoted": 0, "deferred": 0, "results": [], "dry_run": False}


def test_triage_result_deferred_property() -> None:
    assert TriageResult("x", None, "r").deferred
    assert not TriageResult("x", "APPLY", "r").deferred
