"""Discriminating tests: learned refinements written by SkillRefiner are CONSUMED.

Proves the SkillRefiner._append_refinement → next-execution channel is live:
a "## Learned Refinement" section in a skill's PRIME file must appear in the
guidance dict returned by fetch_experience_guidance. The neutralizing test
severs the reader (monkeypatched to return []) and asserts the refinement
disappears — so this suite goes RED if the consumption wiring is removed.
"""

from __future__ import annotations

import sys
import urllib.request
from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor_helpers import refinement_reader
from cohezion.compound.executor_helpers.refinement_reader import load_refined_guidance
from cohezion.compound.executor_helpers.vault_integration import fetch_experience_guidance


KNOWN_INSIGHT = "REFINEMENT-CANARY: always batch NPU classification calls"

PRIME_CONTENT = f"""# TEST_REFINED PRIME

## Purpose

Test skill for refinement-consumption wiring.

## Learned Refinement (2026-07-01T10:00:00)

**Insight**: older refinement, superseded

## Learned Refinement (2026-07-02T10:00:00)

**Insight**: {KNOWN_INSIGHT}

## Version: 1.0.2

## Keywords: test, refinement
"""


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    """Point the reader at a temp skills dir holding a known PRIME file."""
    (tmp_path / "TEST_REFINED_PRIME.md").write_text(PRIME_CONTENT, encoding="utf-8")
    monkeypatch.setattr(refinement_reader, "_SKILLS_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def vault_logger():
    """Mock vault logger returning a stable base guidance dict."""
    logger = MagicMock()
    logger.get_experience_guidance.return_value = {
        "relevant_context": {"decisions": [], "experiments": [], "patterns": []},
    }
    return logger


@pytest.fixture(autouse=True)
def _isolated_enrichment(monkeypatch):
    """Neutralize network-touching enrichment steps for hermetic tests.

    Trajectory search falls into its ImportError branch; the SurrealDB
    retrospection query falls into its OSError branch. Both are the
    documented non-blocking fallbacks — base guidance is still returned.
    """
    monkeypatch.setitem(sys.modules, "cohezion.compound.guidance_enhancer", None)

    def _refuse(*args, **kwargs):
        raise OSError("test: SurrealDB disabled")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)


class TestRefinementReader:
    """Unit behavior of load_refined_guidance."""

    def test_reads_known_refinement(self, skills_dir):
        sections = load_refined_guidance("TEST_REFINED", skills_dir=skills_dir)
        assert any(KNOWN_INSIGHT in s for s in sections)

    def test_most_recent_first(self, skills_dir):
        sections = load_refined_guidance("TEST_REFINED", skills_dir=skills_dir)
        assert len(sections) == 2
        # SkillRefiner appends new sections after older ones — newest is last
        # in the file, so the reader must return it FIRST.
        assert KNOWN_INSIGHT in sections[0]
        assert "older refinement" in sections[1]

    def test_sections_exclude_following_headings(self, skills_dir):
        sections = load_refined_guidance("TEST_REFINED", skills_dir=skills_dir)
        assert all("## Version" not in s for s in sections)
        assert all("## Keywords" not in s for s in sections)

    def test_cap_at_max_sections(self, skills_dir):
        sections = load_refined_guidance("TEST_REFINED", skills_dir=skills_dir, max_sections=1)
        assert len(sections) == 1
        assert KNOWN_INSIGHT in sections[0]  # cap keeps the most recent

    def test_fuzzy_match_like_skill_refiner(self, skills_dir):
        # SkillRefiner._find_prime_file falls back to substring glob match
        sections = load_refined_guidance("test_refined", skills_dir=skills_dir)
        assert any(KNOWN_INSIGHT in s for s in sections)

    def test_missing_skill_fails_open(self, skills_dir):
        assert load_refined_guidance("NO_SUCH_SKILL", skills_dir=skills_dir) == []

    def test_missing_skills_dir_fails_open(self, tmp_path):
        assert load_refined_guidance("TEST_REFINED", skills_dir=tmp_path / "absent") == []


class TestGuidanceConsumption:
    """The channel: PRIME refinement → fetch_experience_guidance output."""

    def test_refinement_reaches_guidance_dict(self, skills_dir, vault_logger):
        guidance = fetch_experience_guidance(vault_logger, "some task", skill_name="TEST_REFINED")
        assert "learned_refinements" in guidance
        assert any(KNOWN_INSIGHT in s for s in guidance["learned_refinements"])

    def test_existing_keys_preserved(self, skills_dir, vault_logger):
        guidance = fetch_experience_guidance(vault_logger, "some task", skill_name="TEST_REFINED")
        assert "relevant_context" in guidance  # base guidance contract intact

    def test_no_skill_name_skips_refinement_read(self, skills_dir, vault_logger):
        guidance = fetch_experience_guidance(vault_logger, "some task")
        assert "learned_refinements" not in guidance

    def test_neutralized_reader_severs_channel(self, skills_dir, vault_logger, monkeypatch):
        """DISCRIMINATING: sever the reader — the refinement must vanish.

        This test fails if fetch_experience_guidance stops consuming
        load_refined_guidance (e.g. the wiring is removed and the section
        text leaks in via some other path — or never arrived at all,
        making test_refinement_reaches_guidance_dict the red one).
        """
        monkeypatch.setattr(refinement_reader, "load_refined_guidance", lambda *a, **k: [])
        guidance = fetch_experience_guidance(vault_logger, "some task", skill_name="TEST_REFINED")
        assert not any(KNOWN_INSIGHT in s for s in guidance.get("learned_refinements", []))
        assert KNOWN_INSIGHT not in str(guidance)

    def test_reader_exception_returns_base_guidance_unchanged(
        self, skills_dir, vault_logger, monkeypatch
    ):
        def _boom(*args, **kwargs):
            raise ValueError("test: reader exploded")

        monkeypatch.setattr(refinement_reader, "load_refined_guidance", _boom)
        guidance = fetch_experience_guidance(vault_logger, "some task", skill_name="TEST_REFINED")
        assert "learned_refinements" not in guidance
        assert "relevant_context" in guidance
