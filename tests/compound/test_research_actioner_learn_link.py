"""LEARN link for the skill the compound daemon actually runs: ``research-actioner``.

Audit 2026-09-21: ``_find_prime_file("research-actioner")`` returned None, so ``refine()`` exited
before any gate and no refinement was ever written; ``golden_fixture`` had no rows for the skill,
so the FAPO R3 regression gate could not bite. No inference, no DB: run_fn is a fake and the
fixture loader reads the checked-in file.
"""

from __future__ import annotations

import json
import shutil
from unittest.mock import patch

import pytest

from cohezion.actioner.engine import triage
from cohezion.compound.prompt_version_registry import (
    GOLDEN_FIXTURE_DIR,
    PromptVersionRegistry,
    _validate,
    load_golden_fixture_file,
)
from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner
from cohezion.registry.skill_registry import load_registry


SKILL = "research-actioner"
REGISTRY_KEY = "RESEARCH_ACTIONER_PRIME"
GOOD_JSON = '{"proposal": "Wire X into the loop.", "falsifiable_step": "p95 latency drops 10%."}'


@pytest.fixture
def isolated_skills_dir(tmp_path, monkeypatch):
    """The real skill file in a scratch SKILLS_DIR, so refine() cannot append to the repo copy."""
    src = SkillRefiner.SKILLS_DIR / f"{REGISTRY_KEY}.md"
    shutil.copy(src, tmp_path / src.name)
    monkeypatch.setattr(SkillRefiner, "SKILLS_DIR", tmp_path)
    return tmp_path


def _registry_without_entry():
    reg = load_registry()
    reg.pop(REGISTRY_KEY, None)
    return reg


class TestSkillFileResolves:
    def test_find_prime_file_resolves_the_lane_label(self, isolated_skills_dir):
        path = SkillRefiner()._find_prime_file(SKILL)
        assert path == isolated_skills_dir / f"{REGISTRY_KEY}.md"

    def test_resolution_goes_through_the_registry(self, isolated_skills_dir):
        """Mutation: drop the registry entry and the lane label no longer resolves."""
        with patch(
            "cohezion.registry.skill_registry.load_registry", side_effect=_registry_without_entry
        ):
            assert SkillRefiner()._find_prime_file(SKILL) is None

    def test_unknown_lane_still_resolves_to_none(self, isolated_skills_dir):
        assert SkillRefiner()._find_prime_file("no-such-lane") is None


class TestCheckedInFixtures:
    def test_fixture_routes_match_the_real_triage(self):
        """Oracle is the engine itself: each triage fixture's route is what triage() does today."""
        doc = json.loads((GOLDEN_FIXTURE_DIR / f"{SKILL}.json").read_text())
        triage_fx = [f for f in doc["fixtures"] if f["kind"] == "triage"]
        assert len(triage_fx) >= 5
        for fx in triage_fx:
            assert (triage(fx["source_card"]) or "none") == fx["expected_route"], fx["why"]
            assert _validate(fx["expected_route"], fx["expected_output"], "regex")

    def test_loader_returns_only_db_fields_and_some_critical(self):
        fixtures = load_golden_fixture_file(SKILL)
        assert 5 <= len(fixtures) <= 10
        assert all(
            set(f) == {"input", "expected_output", "validator_type", "critical"} for f in fixtures
        )
        assert any(f["critical"] for f in fixtures)


def _fake_run(output_for_proposal: str):
    """Answers each fixture as a well-behaved skill would, except proposal prompts."""

    def run(_candidate, inp):
        if "Reply with STRICT JSON" in inp:
            return output_for_proposal
        for fx in json.loads((GOLDEN_FIXTURE_DIR / f"{SKILL}.json").read_text())["fixtures"]:
            if fx["input"] == inp:
                return fx["expected_route"]
        raise AssertionError("unknown fixture input")

    return run


class TestRegressionGate:
    @pytest.fixture(autouse=True)
    def _fixtures_from_file(self):
        with patch.object(
            PromptVersionRegistry,
            "_load_behavioral_fixtures",
            return_value=load_golden_fixture_file(SKILL),
        ):
            yield

    def test_noop_candidate_passes(self):
        assert PromptVersionRegistry().regression_check(SKILL, "prime", _fake_run(GOOD_JSON))

    def test_candidate_breaking_a_critical_fixture_blocks(self):
        broken = _fake_run("Here is my proposal in prose, no JSON.")
        assert not PromptVersionRegistry().regression_check(SKILL, "prime", broken)

    def test_refine_reaches_the_gate_and_is_blocked(self, isolated_skills_dir):
        """Before the fix refine() returned at 'No PRIME file' and never consulted the gate."""
        refiner = SkillRefiner()
        refiner._regression_run_fn = _fake_run("prose only")
        signal = LearningSignal(SKILL, "generate", "Reply in prose.", "q+0.1", "prose", 0.8)
        prime = isolated_skills_dir / f"{REGISTRY_KEY}.md"
        before = prime.read_text()
        with (
            patch.object(SkillRefiner, "_generate_learning_signal", return_value=signal),
            patch.object(PromptVersionRegistry, "check_drift", return_value=True),
            patch.object(SkillRefiner, "_record_blocked_promotion") as blocked,
        ):
            assert refiner.refine(SKILL, "generate", {"success": True}) is None
        blocked.assert_called_once()
        assert blocked.call_args.args[2] == "regression_gate"
        assert prime.read_text() == before
