"""Discriminating tests: learned refinements reach the PROMPT, not just the guidance dict.

``tests/compound/test_refinement_consumption.py`` proves ``fetch_experience_guidance``
puts "## Learned Refinement" sections under ``guidance["learned_refinements"]``. Until
2026-10-22 nothing read that key: ``make_local_execute_fn`` used ``guidance["guidance"]``,
which is never set, so the SkillRefiner loop was open at its consumption point.

These tests go RED if ``guidance_to_prompt_text`` stops including the sections, or if
``make_local_execute_fn`` stops calling it, or if the ``COHEZION_SKILLS_DIR`` override is
dropped on either the reader or the writer side.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.compound.executor_helpers import refinement_reader
from cohezion.compound.executor_helpers.refinement_reader import (
    SKILLS_DIR_ENV,
    guidance_to_prompt_text,
    load_refined_guidance,
    resolve_skills_dir,
)


CANARY = "PROMPT-CANARY: lead with the single canonical term"
SECTION = f"## Learned Refinement (2026-10-22T00:00:00)\n\n**Insight**: {CANARY}"


class TestGuidanceToPromptText:
    def test_learned_refinements_are_included(self) -> None:
        text = guidance_to_prompt_text({"learned_refinements": [SECTION]})
        assert CANARY in text

    def test_base_guidance_comes_first_when_present(self) -> None:
        text = guidance_to_prompt_text({"guidance": "BASE", "learned_refinements": [SECTION]})
        assert text.index("BASE") < text.index(CANARY)

    def test_dict_without_refinements_is_the_old_behaviour(self) -> None:
        assert guidance_to_prompt_text({"guidance": "BASE"}) == "BASE"
        assert guidance_to_prompt_text({"relevant_context": {}}) == ""

    def test_non_dict_and_none(self) -> None:
        assert guidance_to_prompt_text("plain") == "plain"
        assert guidance_to_prompt_text(None) == ""


def test_make_local_execute_fn_puts_refinements_in_the_prompt() -> None:
    """A refinement in the guidance dict must appear in the prompt handed to the cascade.

    The pre-fix execute_fn read ``guidance["guidance"]`` only; against this input it sent
    the bare task text and this assertion fails.
    """
    import cohezion.compound.local_inference as li
    from cohezion.inference.orchestrator import OrchestrationResult

    ok = OrchestrationResult(
        text="stack",
        primary_model="llama3.2-1b-FLM",
        final_model="llama3.2-1b-FLM",
        escalation_count=0,
        cost_usd=0.0,
    )
    orch = MagicMock()
    orch.run = AsyncMock(return_value=ok)
    with patch.object(li, "_get_orchestrator", return_value=orch):
        out, _metrics = li.make_local_execute_fn("What uses LIFO ordering?")(
            {"learned_refinements": [SECTION]}
        )
    assert out == "stack"
    prompt_sent = orch.run.call_args.args[0]
    assert CANARY in prompt_sent
    assert "What uses LIFO ordering?" in prompt_sent


class TestSkillsDirOverride:
    def test_reader_follows_env_override(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "OVERRIDE_TEST_PRIME.md").write_text(
            f"# OVERRIDE_TEST PRIME\n\n{SECTION}\n\n## Version: 1.0.1\n", encoding="utf-8"
        )
        monkeypatch.setenv(SKILLS_DIR_ENV, str(tmp_path))
        assert resolve_skills_dir() == tmp_path
        sections = load_refined_guidance("OVERRIDE_TEST")
        assert sections and CANARY in sections[0]

    def test_reader_defaults_to_repo_dir_without_env(self, monkeypatch) -> None:
        monkeypatch.delenv(SKILLS_DIR_ENV, raising=False)
        assert resolve_skills_dir() == refinement_reader._SKILLS_DIR

    def test_writer_follows_env_override(self, tmp_path: Path, monkeypatch) -> None:
        from cohezion.compound.skill_refiner import SkillRefiner

        monkeypatch.setenv(SKILLS_DIR_ENV, str(tmp_path))
        refiner = SkillRefiner()
        assert tmp_path == refiner.SKILLS_DIR
        (tmp_path / "OVERRIDE_TEST_PRIME.md").write_text("# x\n## Version: 1.0.0\n")
        assert refiner._find_prime_file("OVERRIDE_TEST") == tmp_path / "OVERRIDE_TEST_PRIME.md"

    def test_writer_defaults_to_repo_dir_without_env(self, monkeypatch) -> None:
        from cohezion.compound.skill_refiner import SkillRefiner

        monkeypatch.delenv(SKILLS_DIR_ENV, raising=False)
        assert SkillRefiner().SKILLS_DIR == SkillRefiner.SKILLS_DIR
