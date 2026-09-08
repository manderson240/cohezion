"""V-model tests for cross-model semantic agreement (invariants AG1-AG4).

Structural tests prove the symbols exist. Discriminating tests prove the CONSUMER acts on
them -- each one FAILS if the mechanism is neutralised, which is the standard a
consumption invariant has to meet.
"""

from __future__ import annotations

import inspect

from cohezion.compound.autodqa import AutoDQA
from cohezion.inference.agreement import (
    AGREEMENT_THRESHOLD,
    MAX_PENALTY,
    agreement_penalty,
    semantic_agreement,
)


# Deterministic stand-in for the embedder: orthogonal unit vectors == total disagreement,
# identical vectors == perfect agreement. Keeps the tests offline and exact.
_AGREE = {"a": [1.0, 0.0], "b": [1.0, 0.0]}
_DISAGREE = {"a": [1.0, 0.0], "b": [0.0, 1.0]}


def _fake_embed(mapping):
    def fn(texts):
        return [mapping.get(t, [1.0, 0.0]) for t in texts]

    return fn


class TestAG1Structural:
    """AG1: the symbols exist and the consumer accepts the signal."""

    def test_semantic_agreement_signature(self):
        assert "embed_fn" in inspect.signature(semantic_agreement).parameters

    def test_autodqa_accepts_peer_outputs(self):
        assert "peer_outputs" in inspect.signature(AutoDQA.evaluate).parameters

    def test_threshold_traces_to_measured_run(self):
        # Youden-optimal split on the n=140 calibrated run. Changing this constant is a
        # claim about NEW data, so it is pinned here deliberately.
        assert AGREEMENT_THRESHOLD == 0.40


class TestAG2AgreementSemantics:
    """AG2: agreement is undefined (None), never silently 0.0, when unmeasurable."""

    def test_fewer_than_two_texts_is_none(self):
        assert semantic_agreement(["only one"]) is None
        assert semantic_agreement([]) is None

    def test_blank_peers_do_not_count_as_a_second_opinion(self):
        assert semantic_agreement(["real answer", "   ", ""]) is None

    def test_embedder_unavailable_is_none_not_zero(self):
        # None ("could not measure") must be distinguishable from 0.0 ("they disagreed"),
        # or a transport fault becomes a confident quality judgement.
        assert semantic_agreement(["a", "b"], embed_fn=lambda _t: None) is None

    def test_identical_answers_score_high(self):
        score = semantic_agreement(["a", "b"], embed_fn=_fake_embed(_AGREE))
        assert score is not None and score > 0.99

    def test_orthogonal_answers_score_low(self):
        score = semantic_agreement(["a", "b"], embed_fn=_fake_embed(_DISAGREE))
        assert score is not None and score < 0.01


class TestAG3PenaltyIsBounded:
    """AG3: the penalty is bounded and only fires below the measured threshold."""

    def test_no_penalty_at_or_above_threshold(self):
        assert agreement_penalty(AGREEMENT_THRESHOLD) == 0.0
        assert agreement_penalty(1.0) == 0.0

    def test_unmeasurable_agreement_never_penalises(self):
        assert agreement_penalty(None) == 0.0

    def test_penalty_grows_as_agreement_falls(self):
        assert agreement_penalty(0.0) > agreement_penalty(0.2) > agreement_penalty(0.39)

    def test_penalty_capped(self):
        assert agreement_penalty(0.0) <= MAX_PENALTY


class TestAG4ConsumerActsOnIt:
    """AG4 (CONSUMPTION): AutoDQA's verdict must CHANGE because of peer disagreement.

    These fail if the wiring is removed -- proving the signal is consumed, not merely
    accepted as an argument.
    """

    def _dqa(self):
        return AutoDQA(persist=False, notify_on_reject=False)

    def test_disagreeing_peers_lower_the_score(self, monkeypatch):
        monkeypatch.setattr(
            "cohezion.compound.autodqa.semantic_agreement",
            lambda texts: 0.0,  # total disagreement
        )
        dqa = self._dqa()
        task = "What is the capital of France?"
        base = dqa.evaluate("Paris is the capital of France.", task)
        peered = dqa.evaluate("Paris is the capital of France.", task, peer_outputs=["Lyon"])
        # A no-op implementation returns the same score for both -> this fails.
        assert peered.verdict.score < base.verdict.score

    def test_agreeing_peers_leave_the_score_untouched(self, monkeypatch):
        monkeypatch.setattr(
            "cohezion.compound.autodqa.semantic_agreement",
            lambda texts: 1.0,  # perfect agreement
        )
        dqa = self._dqa()
        task = "What is the capital of France?"
        base = dqa.evaluate("Paris is the capital of France.", task)
        peered = dqa.evaluate("Paris is the capital of France.", task, peer_outputs=["Paris"])
        assert peered.verdict.score == base.verdict.score

    def test_no_peers_means_no_agreement_call(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "cohezion.compound.autodqa.semantic_agreement",
            lambda texts: calls.append(texts) or 0.0,
        )
        self._dqa().evaluate("Paris.", "What is the capital of France?")
        assert calls == []  # no peers -> no embedder traffic at all

    def test_unmeasurable_agreement_does_not_change_verdict(self, monkeypatch):
        # The fail-open path needs its own discriminating test: when the embedder is down
        # the verdict must be IDENTICAL, not merely "not rejected".
        monkeypatch.setattr("cohezion.compound.autodqa.semantic_agreement", lambda texts: None)
        dqa = self._dqa()
        task = "What is the capital of France?"
        base = dqa.evaluate("Paris is the capital of France.", task)
        peered = dqa.evaluate("Paris is the capital of France.", task, peer_outputs=["Lyon"])
        assert peered.verdict.score == base.verdict.score
        assert peered.verdict.reason == base.verdict.reason
