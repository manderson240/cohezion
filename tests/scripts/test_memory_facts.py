"""The gate decides what an extracted triple MEANS; the LLM only proposes spans."""

import importlib.util
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "memory_facts", Path(__file__).resolve().parents[2] / "scripts/ops/memory_facts.py"
)
mf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mf)

S = "The KV estimator in kv_budget.py is consumed by hotswap.ensure_resident during every load."


def test_mf1_ordered_cue_maps_to_a_lexicon_predicate():
    assert mf.verify("KV estimator", "consumed by", "hotswap.ensure_resident", S) == "consumed_by"


def test_mf2_the_live_probe_hallucination_is_rejected():
    # Real model output: verbatim subject/object, invented relation. No cue in the sentence.
    assert (
        mf.verify("the KV estimator in kv_budget.py", "contradicts", "hotswap.ensure_resident", S)
        is None
    )


def test_mf3_wrong_order_or_missing_span_is_rejected():
    assert mf.verify("hotswap.ensure_resident", "consumed by", "KV estimator", S) is None
    assert mf.verify("KV estimator", "consumed by", "not in the sentence", S) is None
    assert mf.verify("KV estimator", "consumed by", "KV estimator", S) is None  # s == o


def test_mf4_a_verbatim_cue_outside_the_lexicon_is_rejected():
    # The cue IS in the sentence, in order — only the lexicon can reject it. An LLM-invented
    # relation word must never become a predicate.
    sent = "The alpha module resembles the beta cache in almost every observable way."
    assert mf.verify("alpha module", "resembles", "beta cache", sent) is None


def test_mf5_markdown_and_case_are_ignored_but_words_are_not():
    s = "**Qwen3-Coder-Next** `depends on` the GDN recurrent-state buffer."
    assert (
        mf.verify("qwen3-coder-next", "Depends On", "GDN recurrent-state buffer", s) == "depends_on"
    )


def test_mf6_placebo_control_rejects_cross_sentence_pairings():
    a = {"subject": "alpha module", "predicate": "uses", "object": "beta cache",
         "sentence": "The alpha module uses the beta cache for lookups in every request."}  # fmt: skip
    b = {"subject": "gamma job", "predicate": "depends_on", "object": "delta queue",
         "sentence": "The gamma job depends on the delta queue being drained first."}  # fmt: skip
    assert mf.verify(a["subject"], "uses", a["object"], a["sentence"]) == "uses"
    assert mf.placebo_pass_rate([a, b]) == 0.0


def test_mf7_sentence_splitter_drops_fragments():
    assert mf.sentences("Too short.\nThis sentence is long enough to keep. Another one that also qualifies.") == [
        "This sentence is long enough to keep.", "Another one that also qualifies."]  # fmt: skip


def test_mf8_prefilter_keeps_only_sentences_a_fact_could_come_from():
    assert mf.has_cue("The estimator is consumed by hotswap during loads.")
    assert not mf.has_cue("Measured on 2026-09-29 the box had 105 GB in use overall.")
    assert not mf.has_cue(
        "The misused reference stays unmatched here."
    )  # word-boundary, not substring
