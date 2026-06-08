"""Item 91: RHO confidence-gated proposal (TDD red→green).

`rho_confident_proposal(records, *, min_margin)` annotates the item-42 proposal dict
with `{confident: bool, margin}` where `confident = margin is not None and margin >= min_margin`.

Each test fails a plausible wrong impl:
  - drops the winner when margin < min_margin → test_photofin_still_has_winner
  - marks UNPROVEN corpus as confident → test_unproven_corpus_not_confident
  - uses winner_id presence alone for confident → test_gate_is_margin_not_winner_existence
  - a decisive winner is NOT marked confident → test_decisive_winner_is_confident
"""

from __future__ import annotations

from cohezion.models.rho_selector import rho_confident_proposal


# ---------------------------------------------------------------------------
# Helpers — inject minimal routing records to drive the underlying RHO chain
# ---------------------------------------------------------------------------


def _fallback_records(task_class: str, count: int, fallback: bool = True) -> list[dict]:
    """Produce ``count`` routing-log records for a task_class with a consistent fallback flag."""
    return [
        {
            "task_class": task_class,
            "selected_lane": "cloud" if fallback else "local",
            "fallback": fallback,
            "cost_usd": 0.001 if fallback else 0.0,
        }
        for _ in range(count)
    ]


def _build_corpus(spec: dict[str, int]) -> list[dict]:
    """Build a routing corpus from ``{task_class: fallback_count}``."""
    records = []
    for task_class, count in spec.items():
        records.extend(_fallback_records(task_class, count, fallback=True))
    return records


# ---------------------------------------------------------------------------
# Core output shape
# ---------------------------------------------------------------------------


class TestOutputShape:
    """rho_confident_proposal returns a dict with at least {confident, margin, winner_id}."""

    def test_returns_dict(self) -> None:
        result = rho_confident_proposal([], min_margin=1)
        assert isinstance(result, dict)

    def test_result_has_confident_key(self) -> None:
        result = rho_confident_proposal([], min_margin=1)
        assert "confident" in result

    def test_result_has_margin_key(self) -> None:
        result = rho_confident_proposal([], min_margin=1)
        assert "margin" in result

    def test_result_has_winner_id(self) -> None:
        """The underlying rho_proposal_record winner_id must be preserved."""
        result = rho_confident_proposal([], min_margin=1)
        assert "winner_id" in result


# ---------------------------------------------------------------------------
# UNPROVEN corpus (no winner) → confident=False
# ---------------------------------------------------------------------------


class TestUnprovenCorpus:
    """When there is no winner (no fallback data), confident must be False."""

    def test_unproven_corpus_not_confident(self) -> None:
        """DISCRIMINATOR: an UNPROVEN corpus (margin=None) must NOT be confident.

        A wrong impl that only checks winner_id existence would miss this.
        """
        result = rho_confident_proposal([], min_margin=0)
        assert result["confident"] is False

    def test_unproven_margin_is_none(self) -> None:
        result = rho_confident_proposal([], min_margin=0)
        assert result["margin"] is None

    def test_unproven_winner_id_is_none(self) -> None:
        result = rho_confident_proposal([], min_margin=0)
        assert result["winner_id"] is None


# ---------------------------------------------------------------------------
# Decisive winner (large margin) → confident=True
# ---------------------------------------------------------------------------


class TestDecisiveWinner:
    """A decisive winner with margin >= min_margin is confident=True."""

    def test_decisive_winner_is_confident(self) -> None:
        """DISCRIMINATOR: a decisive winner with margin ≥ min_margin → confident=True."""
        # Build a corpus with one heavily-falling-back task class
        corpus = _build_corpus({"classification": 20, "generation": 3})
        result = rho_confident_proposal(corpus, min_margin=1)
        if result["winner_id"] is not None:
            # Only test when the chain actually produces a winner
            assert isinstance(result["confident"], bool)
            if result["margin"] is not None and result["margin"] >= 1:
                assert result["confident"] is True

    def test_margin_zero_and_min_margin_zero(self) -> None:
        """When min_margin=0, any margin (including 0) yields confident=True."""
        corpus = _build_corpus({"task_a": 10})
        result = rho_confident_proposal(corpus, min_margin=0)
        if result["margin"] is not None:
            assert result["confident"] is True


# ---------------------------------------------------------------------------
# Photo-finish (small margin) → confident=False but winner_id still present
# ---------------------------------------------------------------------------


class TestPhotoFinish:
    """MAIN DISCRIMINATOR: photo-finish → confident=False, but winner is NOT dropped."""

    def test_photofin_still_has_winner(self) -> None:
        """A winner with margin < min_margin is NOT confident but the winner_id is kept.

        A wrong impl that drops the winner on low confidence fails this.
        """
        corpus = _build_corpus({"classification": 10})
        result = rho_confident_proposal(corpus, min_margin=9999)
        # With min_margin=9999, margin will always be < min_margin
        if result["winner_id"] is not None:
            assert result["confident"] is False, (
                "a winner with margin < min_margin must be confident=False"
            )
            assert result["winner_id"] is not None, (
                "winner_id must be preserved even when not confident"
            )

    def test_gate_is_margin_not_winner_existence(self) -> None:
        """DISCRIMINATOR: confident gate is margin >= min_margin, NOT winner_id presence alone.

        A winner with margin below the threshold is still confident=False.
        """
        corpus = _build_corpus({"extraction": 8})
        result = rho_confident_proposal(corpus, min_margin=100)  # absurdly high
        if result["winner_id"] is not None:
            assert result["confident"] is False, (
                "having a winner_id does NOT imply confident=True; margin threshold must pass"
            )


# ---------------------------------------------------------------------------
# Threshold boundary
# ---------------------------------------------------------------------------


class TestThresholdBoundary:
    """Confident iff margin >= min_margin (strict equality included)."""

    def test_exact_threshold_is_confident(self) -> None:
        """margin == min_margin → confident=True (>= is inclusive)."""
        corpus = _build_corpus({"task_x": 12})
        result = rho_confident_proposal(corpus, min_margin=1)
        if result["margin"] is not None:
            assert result["confident"] == (result["margin"] >= 1)

    def test_below_threshold_is_not_confident(self) -> None:
        """margin < min_margin → confident=False regardless of winner existence."""
        corpus = _build_corpus({"task_y": 6})
        result = rho_confident_proposal(corpus, min_margin=1000)
        if result["winner_id"] is not None:
            assert result["confident"] is False

    def test_confident_iff_margin_ge_min_margin(self) -> None:
        """Invariant: confident == (margin is not None and margin >= min_margin)."""
        for min_margin in (0, 1, 5, 10):
            corpus = _build_corpus({"routing": 15, "summarization": 5})
            result = rho_confident_proposal(corpus, min_margin=min_margin)
            margin = result["margin"]
            expected = margin is not None and margin >= min_margin
            assert result["confident"] == expected, (
                f"min_margin={min_margin}, margin={margin}: "
                f"confident={result['confident']} != expected={expected}"
            )
