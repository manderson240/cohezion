"""Unit tests for LLM-as-Jev decision model (arXiv:2610.02076)."""

import math

import pytest

from cohezion.decision.llm_as_jev import (
    JevCandidate,
    JevPromptFormatter,
    JevTrieScorer,
    LLMAsJevRouter,
    TreeFactorizedListwiseLoss,
    compute_brier_score,
    compute_expected_calibration_error,
)


@pytest.fixture
def sample_candidates():
    return [
        JevCandidate(index=1, label="Alpha", description="Alpha model route"),
        JevCandidate(index=2, label="Beta", description="Beta model route"),
        JevCandidate(index=3, label="Gamma", description="Gamma model route"),
    ]


def test_jev_candidate_suffix_and_prefix_free():
    c1 = JevCandidate(index=1, label="C1")
    c2 = JevCandidate(index=12, label="C12")
    c3 = JevCandidate(index=123, label="C123")

    assert c1.suffix() == "1]"
    assert c2.suffix() == "12]"
    assert c3.suffix() == "123]"

    candidates = [c1, c2, c3]
    # Suffixes "1]", "12]", "123]" are prefix-free because ']' prevents one from being a prefix of another
    assert JevPromptFormatter.is_prefix_free(candidates)


def test_jev_prompt_formatter(sample_candidates):
    context = "System task: classify query latency requirements."
    prompt = JevPromptFormatter.format_prompt(context, sample_candidates)

    assert context in prompt
    assert "[1] Alpha: Alpha model route" in prompt
    assert "[2] Beta: Beta model route" in prompt
    assert "[3] Gamma: Gamma model route" in prompt
    assert prompt.endswith("Best answer: [")


def test_jev_trie_construction(sample_candidates):
    trie = JevPromptFormatter.build_trie(sample_candidates)
    assert not trie.is_terminal

    # Candidate 1: "1]"
    node_1 = trie.find_node("1")
    assert node_1 is not None
    assert not node_1.is_terminal

    node_1_term = trie.find_node("1]")
    assert node_1_term is not None
    assert node_1_term.is_terminal
    assert node_1_term.candidate_index == 1

    # Candidate 2: "2]"
    node_2_term = trie.find_node("2]")
    assert node_2_term is not None
    assert node_2_term.is_terminal
    assert node_2_term.candidate_index == 2


def test_jev_trie_scorer_from_branch_logits(sample_candidates):
    scorer = JevTrieScorer(sample_candidates)

    # Mock logits: "2" has highest logit at root
    def mock_branch_logits(prefix: str, legal_tokens: list[str]) -> dict[str, float]:
        if prefix == "":
            return {"1": 1.0, "2": 3.0, "3": 0.5}
        if prefix in ("1", "2", "3"):
            return {"]": 2.0}
        return {}

    decision = scorer.score_from_branch_logits(mock_branch_logits)

    assert decision.selected_candidate.index == 2
    assert decision.selected_candidate.label == "Beta"
    assert decision.confidence > 0.7
    assert decision.margin > 0.5
    assert math.isclose(sum(decision.probabilities.values()), 1.0, rel_tol=1e-5)


def test_jev_trie_scorer_from_completion(sample_candidates):
    scorer = JevTrieScorer(sample_candidates)

    # Exact bracketed suffix completion
    dec1 = scorer.score_from_completion("2]")
    assert dec1.candidate_index == 2
    assert dec1.confidence > 0.9

    # Raw digit completion
    dec2 = scorer.score_from_completion("3")
    assert dec2.candidate_index == 3
    assert dec2.confidence > 0.9

    # Bracket enclosed completion
    dec3 = scorer.score_from_completion("[1]")
    assert dec3.candidate_index == 1

    # Whitespace padded completion
    dec4 = scorer.score_from_completion("   2] \nExplanation: Because Beta is faster.")
    assert dec4.candidate_index == 2

    # Malformed / unparseable completion falls back to uniform
    dec_fallback = scorer.score_from_completion("I don't know")
    assert math.isclose(dec_fallback.probabilities[1], 1.0 / 3.0, rel_tol=1e-5)


def test_tree_factorized_loss_computation():
    loss_fn = TreeFactorizedListwiseLoss(reg_lambda=1.0, top_k_tail_approx=64)

    # Gold path: "1", "]"
    gold_tokens = ["1", "]"]
    legal_token_sets = [["1", "2", "3"], ["]"]]

    # Model logits along gold trajectory
    gold_logits = [
        {"1": 2.5, "2": 0.5, "3": 0.1, "<unk>": -1.0},
        {"]": 3.0, "<unk>": -2.0},
    ]

    # Reference logits (p0)
    ref_logits = [
        {"1": 1.0, "2": 1.0, "3": 1.0, "<unk>": 0.0},
        {"]": 2.0, "<unk>": 0.0},
    ]

    metrics = loss_fn.compute_loss(gold_logits, ref_logits, gold_tokens, legal_token_sets)

    assert "loss" in metrics
    assert "l_tree" in metrics
    assert "l_legal" in metrics
    assert "l_out" in metrics
    assert metrics["l_tree"] > 0.0
    assert metrics["loss"] >= metrics["l_tree"]


def test_calibration_metrics():
    confidences = [0.9, 0.8, 0.6, 0.4]
    accuracies = [True, True, False, False]

    ece = compute_expected_calibration_error(confidences, accuracies, num_bins=5)
    assert 0.0 <= ece <= 1.0

    probs = [
        {1: 0.9, 2: 0.1},
        {1: 0.8, 2: 0.2},
        {1: 0.4, 2: 0.6},
    ]
    ground_truths = [1, 1, 2]
    brier = compute_brier_score(probs, ground_truths)
    assert brier >= 0.0


@pytest.mark.asyncio
async def test_llm_as_jev_router_sync_and_async(sample_candidates):
    def mock_sync_caller(prompt: str) -> str:
        return "2]"

    router = LLMAsJevRouter(caller=mock_sync_caller)
    dec = router.decide("Route request", sample_candidates)
    assert dec.candidate_index == 2

    async def mock_async_caller(prompt: str) -> str:
        return "3]"

    async_router = LLMAsJevRouter(caller=mock_async_caller)
    async_dec = await async_router.decide_async("Route request", sample_candidates)
    assert async_dec.candidate_index == 3
