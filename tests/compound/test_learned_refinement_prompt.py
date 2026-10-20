"""Discriminating tests: learned refinements REACH THE MODEL PROMPT (LEARN -> next cycle).

``fetch_experience_guidance`` has put ``guidance["learned_refinements"]`` in the dict since
the refinement reader landed, and ``test_refinement_consumption.py`` proves the dict carries
it. But the only execute_fn in production, ``make_local_execute_fn``, built its prompt from
``guidance["guidance"]`` alone -- so the key was produced, passed, and never read. These
tests assert on the PROMPT the orchestrator receives, which is the consumer that matters.

Neutralising ``_format_learned_refinements`` (return "") turns the presence tests red.
"""

from __future__ import annotations

import sys
import urllib.request
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import cohezion.compound.local_inference as li
from cohezion.compound.executor_helpers import refinement_reader
from cohezion.inference.orchestrator import OrchestrationResult


CANARY = "REFINEMENT-CANARY-7731: batch NPU classification calls"
TASK = "Summarise the retrospection backlog"


def _capturing_orchestrator() -> tuple[MagicMock, list[str]]:
    prompts: list[str] = []

    async def _run(prompt, **kwargs):
        prompts.append(prompt)
        return OrchestrationResult(
            text="a sufficiently long answer " * 4,
            primary_model="Gemma-4-E4B-it-GGUF",
            final_model="Gemma-4-E4B-it-GGUF",
            escalation_count=0,
        )

    orch = MagicMock()
    orch.run = AsyncMock(side_effect=_run)
    return orch, prompts


def _run_execute_fn(guidance, context_prefix: str = "") -> str:
    orch, prompts = _capturing_orchestrator()
    with patch.object(li, "_get_orchestrator", return_value=orch):
        li.make_local_execute_fn(TASK, context_prefix=context_prefix)(guidance)
    assert len(prompts) == 1
    return prompts[0]


def _refinement(insight: str, pad: int = 0) -> str:
    return (
        "## Learned Refinement (2026-09-22T10:00:00)\n\n"
        f"**Insight**: {insight}\n\n**Recommendation**: keep it short" + ("x" * pad)
    )


class TestPromptConsumption:
    def test_refinement_appears_in_prompt(self):
        prompt = _run_execute_fn(
            {"guidance": "vault says hi", "learned_refinements": [_refinement(CANARY)]}
        )
        assert CANARY in prompt
        assert li._REFINEMENT_HEADER in prompt

    def test_absent_refinements_leave_prompt_unchanged(self):
        with_key = _run_execute_fn({"guidance": "vault says hi", "learned_refinements": []})
        without_key = _run_execute_fn({"guidance": "vault says hi"})
        assert li._REFINEMENT_HEADER not in with_key
        assert with_key == without_key == f"vault says hi\n\n{TASK}"

    def test_neutralised_consumer_drops_the_refinement(self, monkeypatch):
        """DISCRIMINATING: sever the consumer -- the canary must vanish from the prompt."""
        monkeypatch.setattr(li, "_format_learned_refinements", lambda _g: "")
        prompt = _run_execute_fn({"guidance": "g", "learned_refinements": [_refinement(CANARY)]})
        assert CANARY not in prompt

    def test_stable_first_ordering(self):
        prompt = _run_execute_fn(
            {"guidance": "VARIABLE-GUIDANCE", "learned_refinements": [_refinement(CANARY)]},
            context_prefix="FIXED-CONTEXT",
        )
        assert (
            prompt.index("FIXED-CONTEXT")
            < prompt.index(CANARY)
            < prompt.index("VARIABLE-GUIDANCE")
            < prompt.index(TASK)
        )

    def test_routing_classifies_prompt_without_refinements(self):
        orch, _ = _capturing_orchestrator()
        seen: list[str] = []

        def _classify(p, *a, **k):
            seen.append(p)
            raise RuntimeError("stop routing here")

        with (
            patch.object(li, "_get_orchestrator", return_value=orch),
            patch("cohezion.inference.task_classifier.classify", _classify),
        ):
            li.make_local_execute_fn(TASK)(
                {"guidance": "g", "learned_refinements": [_refinement(CANARY)]}
            )
        assert seen and CANARY not in seen[0]

    def test_string_guidance_is_unaffected(self):
        assert _run_execute_fn("plain guidance") == f"plain guidance\n\n{TASK}"


class TestBudget:
    def test_section_cap_keeps_most_recent(self):
        refs = [_refinement(f"insight-{i}") for i in range(5)]  # most recent first
        out = li._format_learned_refinements({"learned_refinements": refs})
        assert "insight-0" in out and "insight-2" in out
        assert "insight-3" not in out and "insight-4" not in out

    def test_char_cap_drops_older_whole_sections(self):
        refs = [_refinement("newest", pad=900), _refinement("older", pad=900)]
        out = li._format_learned_refinements({"learned_refinements": refs})
        assert "newest" in out and "older" not in out

    def test_oversized_newest_is_truncated_not_dropped(self):
        out = li._format_learned_refinements(
            {"learned_refinements": [_refinement("huge", pad=5000)]}
        )
        assert "huge" in out and "[truncated]" in out
        assert len(out) < li._MAX_REFINEMENT_CHARS + 200

    @pytest.mark.parametrize(
        "guidance",
        [None, "text", {}, {"learned_refinements": None}, {"learned_refinements": [1, "  "]}],
    )
    def test_nothing_to_add_returns_empty(self, guidance):
        assert li._format_learned_refinements(guidance) == ""


class TestThroughExecutor:
    """Skill PRIME file -> fetch_experience_guidance -> execute_task -> model prompt."""

    @pytest.fixture(autouse=True)
    def _hermetic(self, monkeypatch, tmp_path):
        monkeypatch.setitem(sys.modules, "cohezion.compound.guidance_enhancer", None)

        def _refuse(*a, **k):
            raise OSError("test: SurrealDB disabled")

        monkeypatch.setattr(urllib.request, "urlopen", _refuse)
        (tmp_path / "TEST_REFINED_PRIME.md").write_text(
            f"# TEST_REFINED PRIME\n\n{_refinement(CANARY)}\n\n## Version: 1.0.1\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(refinement_reader, "_SKILLS_DIR", tmp_path)

    def _execute(self, skill_name: str) -> str:
        from cohezion.compound.executor import CompoundExecutor

        client = MagicMock()
        client.vault_search.return_value = []
        client.vault_find_relevant_context.return_value = []
        client.vault_log_experiment.return_value = "experiments/t.md"
        executor = CompoundExecutor(client, enable_skill_refinement=False)
        orch, prompts = _capturing_orchestrator()
        with (
            patch.object(executor, "_try_template_match", return_value=None),
            patch.object(li, "_get_orchestrator", return_value=orch),
        ):
            executor.execute_task(
                TASK,
                skill_name=skill_name,
                operation_type="generate",
                execute_fn=li.make_local_execute_fn(TASK),
            )
        assert len(prompts) == 1
        return prompts[0]

    def test_skill_file_refinement_reaches_model_prompt(self):
        assert CANARY in self._execute("TEST_REFINED")

    def test_unrefined_skill_prompt_has_no_refinement_section(self):
        prompt = self._execute("NO_SUCH_SKILL")
        assert CANARY not in prompt and li._REFINEMENT_HEADER not in prompt
