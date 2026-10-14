"""Test headless Claude Code model aliases (fable, opus, sonnet, haiku, claude-haiku-5-5)."""

import pytest
from cohezion.inference.registry import get_registry, Lane
from cohezion.inference.default_profiles import get_profile


def test_claude_model_aliases_registered_in_fleet():
    reg = get_registry()

    expected_models = [
        "fable",
        "opus",
        "sonnet",
        "haiku",
        "claude-haiku-5-5",
        "claude-sonnet-5-5",
        "claude-opus-5-5",
        "claude-fable-5",
    ]
    for m in expected_models:
        assert m in reg.models, f"Model {m} not found in fleet registry"
        entry = reg.models[m]
        assert entry.lane == Lane.CLOUD_CLAUDE
        assert entry.endpoint == "cli:claude"

    # Confirm old non-5.5 versions are purged
    for old in ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7", "claude-opus-4-8"]:
        assert old not in reg.models, f"Old model {old} unexpectedly in fleet registry"


def test_claude_capability_profiles_registered():
    for alias in [
        "fable",
        "opus",
        "sonnet",
        "haiku",
        "claude-haiku-5-5",
        "claude-sonnet-5-5",
        "claude-opus-5-5",
        "claude-fable-5",
    ]:
        prof = get_profile(alias)
        assert prof is not None, f"Profile for {alias} is missing"
        assert prof.family == "claude"
        assert prof.optimal_ctx == 200000
