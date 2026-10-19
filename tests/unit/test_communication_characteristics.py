"""Unit tests for AA-PersonalityBench 21 Communication Characteristics Analyzer."""

from __future__ import annotations

import pytest

from cohezion.text.communication_characteristics import (
    CommunicationCharacteristics,
    analyze_communication_characteristics,
    count_emojis,
    split_sentences,
)


def test_empty_string_returns_zeroed_metrics():
    """Verify empty input returns clean zeroed characteristics."""
    chars = analyze_communication_characteristics("")
    assert chars.characters == 0
    assert chars.words == 0
    assert chars.sentences == 0
    assert chars.paragraphs == 0
    assert chars.avg_sentence_length == 0.0
    assert not chars.ends_with_question


def test_21_metrics_populated():
    """Verify all 21 communication characteristics are present in the dataclass."""
    sample = """# System Architecture Report

Here is our first finding on the AMD Ryzen AI Max 300 series.
We don't recommend loading large models into UMA aperture.

- First point: Use FastFlowLM on NPU
- Second point: Offload heavy tasks to Ollama Cloud

| Component | Status | Port |
|---|---|---|
| NPU | Active | 13305 |
| Ollama | Active | 11434 |

Isn't this clean? Let's check: it's **deterministic**, *fast*, and robust—truly SOTA! 🚀
"""
    chars = analyze_communication_characteristics(sample)
    d = chars.to_dict()

    # 1. Length (5)
    assert d["characters"] > 0
    assert d["words"] > 0
    assert d["sentences"] >= 3
    assert d["paragraphs"] >= 1
    assert d["avg_sentence_length"] > 0.0

    # 2. Structure (3)
    assert d["headings"] >= 1  # '# System Architecture Report'
    assert d["lists"] == 2  # Two bullet points
    assert d["tables"] >= 3  # Table header + separator + rows

    # 3. Punctuation (8)
    assert d["em_dashes"] == 1  # 'robust—truly'
    assert d["contractions"] >= 3  # "don't", "isn't", "let's", "it's"
    assert d["exclamations"] >= 1  # '!'
    assert d["questions"] >= 1  # '?'
    assert d["colons"] >= 3  # ':'
    assert d["quotes"] >= 0

    # 4. Emphasis & Surface (5)
    assert d["bold"] >= 1  # **deterministic**
    assert d["italics"] >= 1  # *fast*
    assert d["emojis"] >= 1  # 🚀
    assert d["acronyms"] >= 2  # AMD, UMA, NPU, SOTA
    assert not d["ends_with_question"]


def test_ends_with_question_detection():
    """Verify ends_with_question boolean flag."""
    text_with_q = "Would you like us to proceed with the next experiment?"
    text_without_q = "The experiment has successfully concluded."

    chars_q = analyze_communication_characteristics(text_with_q)
    chars_no_q = analyze_communication_characteristics(text_without_q)

    assert chars_q.ends_with_question
    assert not chars_no_q.ends_with_question


def test_sentence_splitting_handles_abbreviations():
    """Verify sentence splitting does not falsely split on Dr., e.g., i.e."""
    text = "Dr. Smith presented the results, e.g. the 12D state vectors. The verification passed."
    sentences = split_sentences(text)
    assert len(sentences) == 2
