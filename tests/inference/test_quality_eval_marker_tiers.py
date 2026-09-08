"""The strong-uncertainty window must be NAMED, not a positional slice.

`quality_eval` distinguishes two tiers of uncertainty marker:

  * STRONG -- an explicit admission of ignorance ("I don't know"). In a short
    answer or as a generation's opening sentence this means escalate.
  * WEAK   -- a hedge ("possibly", "might be"). Fine mid-paragraph; only the
    categorical gate treats these as disqualifying.

That distinction was expressed as `_UNCERTAINTY_MARKERS[:4]` at three call
sites -- selection by INDEX. Inserting or reordering a marker silently changes
which markers are strong, with no test failing.

This is the SAME defect class the sibling module already fixed and documented:
`task_classifier.py` carries the note "Selected by CONFIDENCE, not position.
This was `_CATEGORICAL_PATTERNS[:6]`", with a regression test to match. It was
fixed in one file and left standing in the other.

The discriminating test below prepends a marker to the weak list and asserts
that strong-marker behavior is unchanged. Under the `[:4]` implementation the
prepend pushes "i do not know" out of the window, so an answer that admits
ignorance is ACCEPTED -- exactly the regression.
"""

from __future__ import annotations

import pytest

from cohezion.inference import quality_eval
from cohezion.inference.quality_eval import evaluate


class TestStrongMarkerWindowIsNamed:
    def test_strong_window_is_an_explicit_named_tuple(self):
        """T1 structural: the window must exist as its own symbol."""
        assert hasattr(quality_eval, "_STRONG_UNCERTAINTY_MARKERS"), (
            "strong-marker window must be a named tuple, not a positional slice"
        )

    def test_strong_window_is_a_subset_of_all_markers(self):
        strong = set(quality_eval._STRONG_UNCERTAINTY_MARKERS)
        every = set(quality_eval._UNCERTAINTY_MARKERS)
        assert strong, "strong window must not be empty"
        assert strong <= every, f"strong markers not in the full set: {strong - every}"

    @pytest.mark.parametrize(
        "admission",
        ["I don't know the answer.", "I do not know the answer.", "I'm not sure about that."],
    )
    def test_explicit_ignorance_is_rejected_in_a_short_answer(self, admission):
        assert not evaluate(admission, "short_answer").accept

    def test_weak_hedge_is_not_treated_as_strong_in_a_short_answer(self):
        """A hedge is not an admission of ignorance -- it must not escalate."""
        verdict = evaluate("The result is possibly around 42 for this input.", "short_answer")
        assert verdict.accept, f"weak hedge wrongly rejected: {verdict.reason}"

    def test_DISCRIMINATING_prepending_a_marker_does_not_shrink_the_strong_window(
        self, monkeypatch
    ):
        """Order-independence: growing the marker list must not silently
        demote an existing strong marker.

        Under `_UNCERTAINTY_MARKERS[:4]` the prepend shifts "i do not know" to
        index 4, out of the window, and this answer is accepted.
        """
        monkeypatch.setattr(
            quality_eval,
            "_UNCERTAINTY_MARKERS",
            ("perhaps", *quality_eval._UNCERTAINTY_MARKERS),
        )
        verdict = evaluate("I do not know the answer.", "short_answer")
        assert not verdict.accept, (
            "an explicit ignorance admission was accepted after an unrelated "
            "marker was prepended -- the strong window is position-dependent"
        )
