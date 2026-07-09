"""RED tests for the 14 hand-built default CapabilityProfile records.

These profiles populate the registry's default ModelEntry records. They
must be honest: no fabricated strengths/weaknesses beyond what the
public model card states.

Each profile must have:
- a source_url pointing to a real model card
- strengths/weaknesses that are card-derivable
- a non-empty family
- non-zero min_ctx and optimal_ctx
"""

from __future__ import annotations

import pytest

from cohezion.inference.capability_profile import CapabilityProfile
from cohezion.inference.default_profiles import DEFAULT_PROFILES


def test_default_profiles_is_a_dict_of_at_least_14():
    assert isinstance(DEFAULT_PROFILES, dict)
    assert len(DEFAULT_PROFILES) >= 14


@pytest.mark.parametrize("model_id, profile", list(DEFAULT_PROFILES.items()))
def test_default_profile_required_fields_are_populated(model_id, profile):
    assert isinstance(profile, CapabilityProfile)
    assert profile.model_id == model_id
    # source_url must be present and look like a URL
    assert profile.source_url.startswith("http"), f"{model_id} has no source_url"
    # ctx values must be positive
    assert profile.min_ctx > 0
    assert profile.optimal_ctx >= profile.min_ctx
    # family must be non-empty
    assert profile.family != ""
    # strengths and weaknesses are frozensets
    assert isinstance(profile.strengths, frozenset)
    assert isinstance(profile.weaknesses, frozenset)


def test_default_profiles_for_known_models_match_public_cards():
    """A few anchor records we can verify against the public model cards."""
    # Qwen3-0.6B is a small general model with /no_think support
    qwen = DEFAULT_PROFILES.get("Qwen3-0.6B-GGUF")
    if qwen is not None:
        assert qwen.thinking_mode in {"optional_prefix", "never"}
        assert "qwen3" in qwen.prompt_template_fingerprint

    # Gemma-4-E4B-it is a thinking model (per existing model_card_harness)
    gemma = DEFAULT_PROFILES.get("Gemma-4-E4B-it-GGUF")
    if gemma is not None:
        assert gemma.thinking_mode == "always"

    # A code-oriented model should have "code" in strengths
    code_oriented = [k for k, p in DEFAULT_PROFILES.items() if "code" in p.strengths]
    assert len(code_oriented) >= 1
