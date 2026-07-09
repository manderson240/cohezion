"""RED tests for the CapabilityProfile dataclass + card parser.

The contract:
- CapabilityProfile is a frozen dataclass with the card-derived fields
  the plan specifies (strengths, weaknesses, optimal_ctx, sampling_sweet_spot,
  thinking_mode, prompt_template_fingerprint, known_failure_modes, source_url,
  read_at).
- CardParser.parse_huggingface() takes a raw model card markdown string
  and returns either a CapabilityProfile or raises CardParseError with a
  reason.
- A model card that doesn't have a recognizable "strengths" or "limitations"
  section raises CardParseError — we never build a profile from a card we
  haven't actually read.
- Latest card wins on conflict: re-parsing with a newer card overwrites the
  previous profile (the new profile is the truth; old warnings are
  intentionally lost per the plan decision).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cohezion.inference.capability_profile import (
    CapabilityProfile,
    CardParseError,
    CardParser,
)


# ── CapabilityProfile dataclass shape ────────────────────────────────────────


def test_capability_profile_required_fields_exist():
    profile = CapabilityProfile(
        model_id="Qwen/Qwen3-8B",
        family="qwen3",
        supported_modes=frozenset({"chat", "tool_use"}),
        optimal_ctx=32768,
        min_ctx=1024,
        strengths=frozenset({"code", "math"}),
        weaknesses=frozenset({"multimodal"}),
        sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
        prompt_template_fingerprint="chatml",
        thinking_mode="optional_prefix",
        known_failure_modes=("degrades below 1k ctx",),
        source_url="https://huggingface.co/Qwen/Qwen3-8B",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )
    assert profile.model_id == "Qwen/Qwen3-8B"
    assert "code" in profile.strengths
    assert profile.thinking_mode == "optional_prefix"


def test_capability_profile_is_frozen():
    profile = CapabilityProfile(
        model_id="x",
        family="x",
        supported_modes=frozenset(),
        optimal_ctx=1024,
        min_ctx=512,
        strengths=frozenset(),
        weaknesses=frozenset(),
        sampling_sweet_spot={},
        prompt_template_fingerprint="unknown",
        thinking_mode="never",
        known_failure_modes=(),
        source_url="https://example.com",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )
    with pytest.raises((AttributeError, TypeError)):
        profile.model_id = "mutated"  # type: ignore[misc]


# ── HuggingFace card parser ──────────────────────────────────────────────────


GOOD_CARD = """
# Model Card for Qwen3-8B

## Intended Uses
Code generation, math, general chat.

## Strengths
- Excellent at code completion
- Strong math reasoning
- Supports tool use

## Limitations
- Not multimodal
- English/Chinese only

## How to Use
Use temperature=0.6, top_p=0.95. Use /no_think prefix to disable thinking.

## Citation
@software{qwen3-8b, ...}
"""


def test_parse_huggingface_happy_path():
    profile = CardParser.parse_huggingface(GOOD_CARD, model_id="Qwen/Qwen3-8B")
    assert isinstance(profile, CapabilityProfile)
    # Strengths preserve the card's own wording — we don't substitute our
    # own taxonomy. The test asserts the card's claims are preserved, not
    # mapped.
    assert "excellent at code completion" in profile.strengths
    assert "strong math reasoning" in profile.strengths
    # Limitations likewise
    assert "not multimodal" in profile.weaknesses
    # sampling parsed from "How to Use" section
    assert profile.sampling_sweet_spot["temperature"] == 0.6
    assert profile.sampling_sweet_spot["top_p"] == 0.95
    # /no_think prefix detected
    assert profile.thinking_mode == "optional_prefix"
    assert profile.prompt_template_fingerprint == "chatml"


def test_parse_huggingface_rejects_card_without_strengths():
    bad = """
    # A Model
    This card has no strengths section.
    """
    with pytest.raises(CardParseError) as exc_info:
        CardParser.parse_huggingface(bad, model_id="unknown/model")
    assert "strengths" in str(exc_info.value).lower()


def test_parse_huggingface_rejects_card_without_limitations():
    bad = """
    # A Model
    ## Strengths
    - Code
    """
    with pytest.raises(CardParseError) as exc_info:
        CardParser.parse_huggingface(bad, model_id="unknown/model")
    assert "limitations" in str(exc_info.value).lower()


def test_parse_huggingface_records_source_url_and_read_at():
    fixed_time = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    profile = CardParser.parse_huggingface(
        GOOD_CARD,
        model_id="Qwen/Qwen3-8B",
        source_url="https://huggingface.co/Qwen/Qwen3-8B/blob/main/README.md",
        read_at=fixed_time,
    )
    assert profile.source_url == "https://huggingface.co/Qwen/Qwen3-8B/blob/main/README.md"
    assert profile.read_at == fixed_time


# ── Latest card wins (the chosen policy) ─────────────────────────────────────


def test_latest_card_wins_on_conflict():
    """If the same model has a newer card, the new profile replaces the old.

    The new profile is the truth until a future revision supersedes it.
    Old warnings are intentionally lost.
    """
    old = CapabilityProfile(
        model_id="x",
        family="x",
        supported_modes=frozenset(),
        optimal_ctx=4096,
        min_ctx=512,
        strengths=frozenset({"code"}),
        weaknesses=frozenset({"math"}),  # OLD claim
        sampling_sweet_spot={},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=("old warning",),
        source_url="https://example.com/v1",
        read_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    new = CapabilityProfile(
        model_id="x",
        family="x",
        supported_modes=frozenset(),
        optimal_ctx=32768,  # updated
        min_ctx=1024,
        strengths=frozenset({"code", "math"}),  # math no longer a weakness
        weaknesses=frozenset(),  # cleared
        sampling_sweet_spot={"temperature": 0.6},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=(),
        source_url="https://example.com/v2",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )
    # Newer read_at ⇒ newer wins
    chosen = max([old, new], key=lambda p: p.read_at)
    assert chosen is new
    assert "math" in chosen.strengths
    assert "math" not in chosen.weaknesses
    assert "old warning" not in chosen.known_failure_modes


# ── arXiv abstract parser (lighter than HF; the plan says so) ────────────────


ABSTRACT_WITH_PARSED_FIELDS = """
We present a 7B parameter language model trained for code generation.
Strengths: code completion, bug fixing.
Weaknesses: long-context reasoning above 16k.
"""


def test_parse_arxiv_abstract_light():
    profile = CardParser.parse_arxiv_abstract(
        ABSTRACT_WITH_PARSED_FIELDS,
        model_id="arxiv:2402.00000",
        source_url="https://arxiv.org/abs/2402.00000",
    )
    assert isinstance(profile, CapabilityProfile)
    # The abstract explicitly lists these strengths; the parser preserves
    # them as the model claims them, not the test's preferred taxonomy.
    assert "code completion" in profile.strengths
    assert "bug fixing" in profile.strengths
    # source_url preserved
    assert profile.source_url.endswith("2402.00000")
    # arXiv cards have no sampling section ⇒ empty sweet-spot
    assert profile.sampling_sweet_spot == {}
    # no chat template fingerprint derivable from an abstract
    assert profile.prompt_template_fingerprint == "unknown"
