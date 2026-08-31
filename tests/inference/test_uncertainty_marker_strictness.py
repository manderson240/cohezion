"""The strict-uncertainty set must be a NAMED group, not a positional slice.

`quality_eval` gates outputs on two different strengths of uncertainty signal:

  strict   -- the model explicitly disclaims knowledge ("i don't know").
              Presence is a HARD REJECT even in a short answer.
  hedging  -- ordinary qualifiers ("possibly", "unclear", "might be") that occur
              in legitimate prose. These must never hard-reject on their own.

The strict set was selected as `_UNCERTAINTY_MARKERS[:4]` at three call sites --
a positional slice masquerading as a strictness filter. Inserting a marker
anywhere in the first four silently promotes a hedging word into the hard-reject
window and demotes a real disclaimer out of it, with no test failing.

This is the SAME defect already fixed in `task_classifier` (`_CATEGORICAL_PATTERNS[:6]`
-> `_HIGH_CONF_CATEGORICAL`, derived from the confidence field, see the comment at
task_classifier.py:1465). It was fixed at the reported instance but not at the class,
so these three sites survived.

The discriminating tests below are BEHAVIORAL, not structural: they mutate the
marker table the way a future contributor would (adding a marker) and assert the
verdict does not change. Against the positional-slice implementation they fail;
against a named-group implementation they pass.
"""

from __future__ import annotations

import pytest

from cohezion.inference import quality_eval as qe


# A short answer that hedges but is NOT a knowledge disclaimer. Long enough to
# clear the 10-char floor so length is never the reason for a rejection.
_HEDGING_SHORT_ANSWER = "The result is possibly around 42 units."

# A medium-generation body that opens with a hedging word. Padded past the
# 100-char floor for `medium_generation` so length never decides the verdict.
_HEDGING_GENERATION = (
    "Possibly the most direct route is to cache the intermediate result, then "
    "reuse it on the next pass instead of recomputing the whole table again. "
    "That keeps the hot loop allocation-free."
)


class TestStrictSetIsOrderIndependent:
    """Adding a marker to the table must not change which markers hard-reject."""

    def test_prepending_a_hedging_marker_does_not_make_it_strict_short_answer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hedging word moved to the front of the table must stay hedging.

        Wrong impl (`_UNCERTAINTY_MARKERS[:4]`): "possibly" lands inside the
        first four and becomes a hard reject, so this short answer flips from
        accept to reject purely because of list ORDER.
        """
        baseline = qe.evaluate(_HEDGING_SHORT_ANSWER, "short_answer")
        assert baseline.accept, (
            "precondition: a hedging short answer is accepted before any reordering "
            f"(got {baseline.reason!r})"
        )

        monkeypatch.setattr(
            qe, "_UNCERTAINTY_MARKERS", ("possibly", *qe._UNCERTAINTY_MARKERS), raising=True
        )

        after = qe.evaluate(_HEDGING_SHORT_ANSWER, "short_answer")
        assert after.accept, (
            "reordering the marker table must not turn a hedging word into a "
            f"hard reject -- got {after.reason!r}"
        )

    def test_prepending_a_hedging_marker_does_not_make_it_strict_generation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same coupling at the `_eval_generation` call site (quality_eval.py:165)."""
        baseline = qe.evaluate(_HEDGING_GENERATION, "medium_generation")
        assert baseline.accept, (
            f"precondition: hedging generation is accepted (got {baseline.reason!r})"
        )

        monkeypatch.setattr(
            qe, "_UNCERTAINTY_MARKERS", ("possibly", *qe._UNCERTAINTY_MARKERS), raising=True
        )

        after = qe.evaluate(_HEDGING_GENERATION, "medium_generation")
        assert after.accept, (
            f"generation gate must ignore table order for strictness -- got {after.reason!r}"
        )

    def test_appending_a_strict_marker_makes_it_strict(self) -> None:
        """The inverse: a genuine disclaimer must hard-reject wherever it sits.

        A fix that simply DELETED the strict check would pass the two tests above
        while destroying the gate. This pins the other direction, so the pair
        discriminates a real fix from a neutered one.
        """
        verdict = qe.evaluate("I don't know what that value is.", "short_answer")
        assert not verdict.accept, (
            "an explicit knowledge disclaimer must still hard-reject a short answer"
        )


class TestStrictAndHedgingGroupsArePartitioned:
    """The two groups must partition the full table -- no drift, no overlap."""

    def test_groups_are_disjoint(self) -> None:
        strict = set(qe._STRONG_UNCERTAINTY_MARKERS)
        hedging = set(qe._WEAK_UNCERTAINTY_MARKERS)
        assert not (strict & hedging), f"marker in both groups: {strict & hedging}"

    def test_union_is_the_full_table(self) -> None:
        """`_UNCERTAINTY_MARKERS` must be DERIVED, so the loose gate can never
        drift out of sync with the two groups it is built from."""
        assert set(qe._UNCERTAINTY_MARKERS) == set(qe._STRONG_UNCERTAINTY_MARKERS) | set(
            qe._WEAK_UNCERTAINTY_MARKERS
        )

    def test_strict_set_is_unchanged_by_this_refactor(self) -> None:
        """Behaviour-preserving: the four markers that were strict stay strict.

        The prior revision is the oracle here (verification-depth.md: for a change
        claimed to be behaviour-preserving, the pre-existing implementation is a
        free unbiased oracle). These are exactly `_UNCERTAINTY_MARKERS[:4]` as it
        stood before the refactor.
        """
        assert set(qe._STRONG_UNCERTAINTY_MARKERS) == {
            "i'm not sure",
            "i am not sure",
            "i don't know",
            "i do not know",
        }
