"""Discriminating tests for overthinking_penalty (quantized-reasoning logit penalty, arXiv 2606.00206).

Each test fails for a naive impl that skips variant-expansion or the single-token guard.
"""

from cohezion.inference.overthinking_penalty import (
    DEFAULT_OVERTHINKING_MARKERS,
    marker_variants,
    overthinking_logit_bias,
)


def test_default_markers_include_the_papers_three():
    assert {"wait", "but", "alternatively"} <= set(DEFAULT_OVERTHINKING_MARKERS)


def test_variant_expansion_covers_space_and_capital_forms():
    v = set(marker_variants(["wait"]))
    # the discriminating cases: a naive impl returning just ["wait"] misses these BPE surface forms
    assert {"wait", " wait", "Wait", " Wait"} <= v


def test_bias_map_applies_penalty_to_marker_tokens():
    # fake tokenizer: each distinct string maps to a stable single id; penalize all of them
    ids = {}
    def token_ids_for(s):
        return [ids.setdefault(s, len(ids) + 1000)]
    bias = overthinking_logit_bias(token_ids_for, markers=["wait"], penalty=-5.0)
    assert bias, "expected non-empty bias map"
    assert all(v == -5.0 for v in bias.values())
    assert len(bias) == 4  # wait / " wait" / "Wait" / " Wait" → 4 single-token variants


def test_multi_token_markers_are_skipped():
    # a marker that tokenizes to >1 tokens must NOT be biased (would penalize unrelated continuations)
    def token_ids_for(s):
        return [1, 2, 3] if "alternatively" in s.lower() else [42]
    bias = overthinking_logit_bias(token_ids_for, markers=["alternatively"])
    assert bias == {}, bias  # all variants are multi-token → skipped
