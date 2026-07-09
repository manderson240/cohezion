"""RED tests for the card-aligned recipe guard.

The contract:
- RecipeGuard.assert_aligned(call_signature) raises RecipeMisalignment if
  a caller uses default params (i.e. an InferenceParams object was not
  supplied). This is the fail-closed runtime assertion.
- RecipeGuard.assert_aligned accepts InferenceParams and returns silently.
- A lint-style check (RecipeGuard.check_file_for_default_params) scans a
  .py file for `extend_claude(` calls that don't pass a `params=` kwarg
  and returns a list of line numbers with violations.
- A ModelEntry whose `profile` is None is considered cardless and cannot
  be dispatched to via route_by_capability — the guard rejects it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from cohezion.inference.capability_profile import CapabilityProfile
from cohezion.inference.model_card_harness import InferenceParams
from cohezion.inference.recipe_guard import (
    RecipeGuard,
    RecipeMisalignment,
)


def _good_profile(model_id: str = "test/model") -> CapabilityProfile:
    return CapabilityProfile(
        model_id=model_id,
        family="test",
        supported_modes=frozenset({"chat"}),
        optimal_ctx=8192,
        min_ctx=512,
        strengths=frozenset({"code"}),
        weaknesses=frozenset(),
        sampling_sweet_spot={"temperature": 0.6},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=(),
        source_url="https://example.com",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )


# ── Runtime assertion: default params are forbidden ──────────────────────────


def test_assert_aligned_accepts_aligned_params():
    params = InferenceParams(
        model_id="test/model",
        max_tokens=400,
        prompt_prefix="",
        extra_body={"temperature": 0.6},
    )
    # should not raise
    RecipeGuard.assert_aligned(params)


def test_assert_aligned_rejects_default_params():
    """If a caller constructs InferenceParams with default (zero) values, fail."""
    bad = InferenceParams(model_id="", max_tokens=0)
    with pytest.raises(RecipeMisalignment):
        RecipeGuard.assert_aligned(bad)


# ── Card-less ModelEntry cannot be dispatched ────────────────────────────────


def test_assert_card_present_rejects_none_profile():
    class FakeEntry:
        model_id = "no_card"
        profile = None

    with pytest.raises(RecipeMisalignment) as exc_info:
        RecipeGuard.assert_card_present(FakeEntry())
    assert "card" in str(exc_info.value).lower()


def test_assert_card_present_accepts_real_profile():
    class FakeEntry:
        model_id = "with_card"
        profile = _good_profile("with_card")

    # should not raise
    RecipeGuard.assert_card_present(FakeEntry())


# ── Lint: scan a file for `extend_claude(` calls without params= ─────────────


def test_lint_check_finds_unaligned_extend_claude(tmp_path: Path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text(
        """
from cohezion.inference.fleet import extend_claude
import asyncio

async def go():
    # BAD: no params= kwarg
    r = await extend_claude("hello", quality_threshold=0.8)
    return r
"""
    )
    violations = RecipeGuard.check_file_for_default_params(bad_file)
    assert len(violations) >= 1
    assert any("extend_claude" in v.message for v in violations)


def test_lint_check_passes_aligned_extend_claude(tmp_path: Path):
    good_file = tmp_path / "good.py"
    good_file.write_text(
        """
from cohezion.inference.fleet import extend_claude
from cohezion.inference.model_card_harness import InferenceParams
import asyncio

async def go():
    params = InferenceParams(model_id="x", max_tokens=400, sampling={"temperature": 0.6})
    r = await extend_claude("hello", params=params, quality_threshold=0.8)
    return r
"""
    )
    violations = RecipeGuard.check_file_for_default_params(good_file)
    assert violations == []


def test_lint_check_ignores_commented_out_calls(tmp_path: Path):
    f = tmp_path / "comments.py"
    f.write_text(
        """
# r = await extend_claude("hello")  # noqa
# await extend_claude("foo", params=other)  # ok
"""
    )
    violations = RecipeGuard.check_file_for_default_params(f)
    assert violations == []
