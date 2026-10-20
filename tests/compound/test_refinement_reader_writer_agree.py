"""Refinement writer and reader must resolve the same file, and tracked PRIMEs need R3.

Review 2026-09-22: (C8) SkillRefiner resolved "research-actioner" through the registry to
RESEARCH_ACTIONER_PRIME.md, but refinement_reader._find_prime_file returned None for it --
refinements written, never read. (ops #4) With no promotion gate, SkillRefiner rewrote
git-tracked PRIME files in the service's dirty checkout whenever the FAPO R3 regression gate
fail-opened. Tracked files now need a VERIFIED regression pass; otherwise the refinement goes
to an out-of-repo overlay that the reader also reads. No inference, no DB.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from cohezion.compound.executor_helpers import refinement_reader as rr
from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner


SKILL = "research-actioner"
PRIME = "RESEARCH_ACTIONER_PRIME.md"


def _signal() -> LearningSignal:
    return LearningSignal(
        skill_name=SKILL,
        operation_type="research",
        key_insight="KEY-INSIGHT-MARKER",
        metric_change="q 0.9",
        recommendation="keep it",
        confidence=0.9,
    )


@pytest.fixture
def overlay_dir(tmp_path, monkeypatch):
    d = tmp_path / "overlay"
    monkeypatch.setenv("COHEZION_REFINEMENT_OVERLAY_DIR", str(d))
    return d


@pytest.fixture
def tracked_skills(tmp_path, monkeypatch):
    """The real skill file, git-TRACKED in a scratch repo (the service checkout's situation)."""
    repo = tmp_path / "repo"
    skills = repo / "skills"
    skills.mkdir(parents=True)
    shutil.copy(SkillRefiner.SKILLS_DIR / PRIME, skills / PRIME)
    for c in (["init", "-q"], ["add", "."]):
        subprocess.run(["git", *c], cwd=repo, check=True, capture_output=True)
    monkeypatch.setattr(SkillRefiner, "SKILLS_DIR", skills)
    monkeypatch.setattr(rr, "_SKILLS_DIR", skills)
    return skills


def test_reader_resolves_what_the_writer_resolves(tracked_skills):
    assert SkillRefiner()._find_prime_file(SKILL) == tracked_skills / PRIME
    assert rr._find_prime_file(SKILL, tracked_skills) == tracked_skills / PRIME


def test_unverified_refinement_of_a_tracked_prime_goes_to_the_overlay(tracked_skills, overlay_dir):
    before = (tracked_skills / PRIME).read_text()
    out = SkillRefiner()._append_refinement(tracked_skills / PRIME, _signal())
    assert (tracked_skills / PRIME).read_text() == before  # tracked file untouched
    assert out == rr.overlay_path(tracked_skills / PRIME) and out.parent == overlay_dir
    # ...and the reader still delivers it to the next run
    assert any("KEY-INSIGHT-MARKER" in s for s in rr.load_refined_guidance(SKILL))


def test_verified_refinement_may_rewrite_the_tracked_prime(tracked_skills, overlay_dir):
    out = SkillRefiner()._append_refinement(
        tracked_skills / PRIME, _signal(), regression_verified=True
    )
    assert out == tracked_skills / PRIME
    assert "KEY-INSIGHT-MARKER" in (tracked_skills / PRIME).read_text()
    assert not overlay_dir.exists()


def test_untracked_prime_is_written_in_place(tmp_path, overlay_dir):
    """Discriminating pair: the gate is about TRACKED files, not every write."""
    prime = tmp_path / "X_PRIME.md"
    shutil.copy(SkillRefiner.SKILLS_DIR / PRIME, prime)
    assert rr.is_git_tracked(prime) is False
    assert SkillRefiner()._append_refinement(prime, _signal()) == prime
    assert not overlay_dir.exists()


def test_refine_passes_unverified_when_fixtures_are_absent(
    tracked_skills, overlay_dir, monkeypatch
):
    """R3 fail-open (run_fn wired, zero fixtures) must not count as verification."""
    from cohezion.compound import prompt_version_registry as pvr

    monkeypatch.setattr(
        pvr.PromptVersionRegistry, "_load_behavioral_fixtures", lambda self, name: []
    )
    seen: dict[str, bool] = {}
    sr = SkillRefiner()
    sr._regression_run_fn = lambda cand, inp: ""
    real = sr._append_refinement

    def spy(prime, signal, *, regression_verified=False):
        seen["v"] = regression_verified
        return real(prime, signal, regression_verified=regression_verified)

    monkeypatch.setattr(sr, "_append_refinement", spy)
    monkeypatch.setattr(sr, "_ensure_golden_fixtures", lambda *a: None)
    monkeypatch.setattr(pvr.PromptVersionRegistry, "check_drift", lambda *a: True)
    monkeypatch.setattr(sr, "_adversarial_review_gate", lambda *a: True)
    monkeypatch.setattr(sr, "_should_run_refinement_chain", lambda: True)
    monkeypatch.setattr(sr, "_generate_learning_signal", lambda *a: _signal())
    sr.refine(SKILL, "research", {"success": True, "duration_seconds": 1.0, "tokens_used": 1})
    assert seen == {"v": False}
    assert "KEY-INSIGHT-MARKER" not in (tracked_skills / PRIME).read_text()


def test_untracked_file_inside_a_repo_is_not_tracked(tracked_skills):
    """In-repo is not tracked: a new, un-added PRIME file may be written in place."""
    new = tracked_skills / "NEW_PRIME.md"
    new.write_text("x\n")
    assert rr.is_git_tracked(new) is False
    assert rr.is_git_tracked(tracked_skills / PRIME) is True
