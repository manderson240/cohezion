"""Unit tests for Harness^2 Engine (arXiv:2610.14224).

Verifies:
1. Canonical K=8 component representation and deterministic hashing.
2. Orthogonal Invariant (INV) vs Domain (DOM) candidate proposal.
3. Behavioral contrast extraction without ground-truth labels.
4. Selective composition of helped edits and rejection of regressions.
5. Strict Confounding Doctrine enforcement in reflection.
6. Continual improvement library persistence and retrieval.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.harness2_engine import (
    BehavioralProber,
    ComponentEdit,
    ContrastiveComposer,
    ContrastiveProposer,
    ExecutionRecord,
    Harness2Engine,
    HarnessComponentType,
    HarnessDefinition,
    HarnessExperience,
    HarnessingReflector,
    HarnessLibraryStore,
    HarnessVerdict,
)


@pytest.mark.unit
class TestHarnessDefinition:
    """Tests for HarnessDefinition and K=8 component types."""

    def test_canonical_k8_components(self) -> None:
        """Ensure all 8 canonical components are present."""
        expected_values = {
            "prompt.txt",
            "guardrails.md",
            "memory.md",
            "skills",
            "tools",
            "scripts",
            "subagents",
            "plugin.py",
        }
        actual_values = {c.value for c in HarnessComponentType}
        assert actual_values == expected_values
        assert len(HarnessComponentType) == 8

    def test_hash_calculation_deterministic_and_sensitive(self) -> None:
        """Hash must be invariant to order and sensitive to content changes."""
        h1 = HarnessDefinition(
            harness_id="h1",
            components={
                HarnessComponentType.PROMPT: "System prompt A",
                HarnessComponentType.GUARDRAILS: "Stop on error",
            },
        )
        h2 = HarnessDefinition(
            harness_id="h2",
            components={
                HarnessComponentType.GUARDRAILS: "Stop on error",
                HarnessComponentType.PROMPT: "System prompt A",
            },
        )
        # Invariant to insertion order
        assert h1.calculate_hash() == h2.calculate_hash()

        # Sensitive to component mutation
        h3 = HarnessDefinition(
            harness_id="h3",
            components={
                HarnessComponentType.PROMPT: "System prompt B",
                HarnessComponentType.GUARDRAILS: "Stop on error",
            },
        )
        assert h1.calculate_hash() != h3.calculate_hash()

    def test_to_and_from_dict(self) -> None:
        h = HarnessDefinition(
            harness_id="h-test",
            components={
                HarnessComponentType.PROMPT: "You are an agent",
                HarnessComponentType.SCRIPTS: "# helper",
            },
            metadata={"tier": "local"},
        )
        d = h.to_dict()
        assert d["harness_id"] == "h-test"
        assert d["components"]["prompt.txt"] == "You are an agent"
        assert "hash" in d

        recovered = HarnessDefinition.from_dict(d)
        assert recovered.harness_id == h.harness_id
        assert recovered.get_content(HarnessComponentType.PROMPT) == "You are an agent"
        assert recovered.get_content(HarnessComponentType.SCRIPTS) == "# helper"


@pytest.mark.unit
class TestContrastiveProposer:
    """Tests for orthogonal INV and DOM candidate generation."""

    def test_propose_candidates_with_reference_errors(self) -> None:
        base = HarnessDefinition(
            harness_id="base_1",
            components={HarnessComponentType.PROMPT: "Base prompt"},
        )
        ref_exec = ExecutionRecord(
            harness_id="base_1",
            trajectory=[{"step": 1, "action": "run_cmd"}, {"step": 2, "action": "fail"}],
            deliverable="partial output",
            errors_encountered=["TimeoutError: process exceeded budget"],
        )

        inv_cand, dom_cand, edits = ContrastiveProposer.propose_candidates(
            base_harness=base,
            reference_exec=ref_exec,
            task_query="Process ARC-AGI-3 grid",
        )

        # Invariant candidate should inject guardrail and script offload
        assert inv_cand.harness_id == "base_1_inv"
        assert "Error Trajectory & Loop Suppression" in inv_cand.get_content(
            HarnessComponentType.GUARDRAILS
        )
        assert "output_validator" in inv_cand.get_content(HarnessComponentType.SCRIPTS)

        # Domain candidate should inject domain skill contract
        assert dom_cand.harness_id == "base_1_dom"
        assert "Domain Contract for Task" in dom_cand.get_content(HarnessComponentType.SKILLS)

        # Proposed edits list contains both INV and DOM
        scopes = {e.candidate_scope for e in edits}
        assert "INV" in scopes
        assert "DOM" in scopes

    def test_propose_candidates_applies_library_experiences(self) -> None:
        base = HarnessDefinition(
            harness_id="base_exp",
            components={HarnessComponentType.PROMPT: "Initial prompt"},
        )
        ref_exec = ExecutionRecord(
            harness_id="base_exp",
            trajectory=[],
            deliverable="",
        )
        exp = HarnessExperience(
            experience_id="exp_prior_1",
            cue="Multi-step tool failure",
            lesson="Always verify file existence before opening",
            evidence="Mitigated FileNotFoundError",
            confidence="high",
            task_id="prior_task",
            component=HarnessComponentType.PROMPT,
        )

        inv_cand, _, edits = ContrastiveProposer.propose_candidates(
            base_harness=base,
            reference_exec=ref_exec,
            task_query="Test query",
            applicable_experiences=[exp],
        )

        assert "Lesson from exp_prior_1" in inv_cand.get_content(HarnessComponentType.PROMPT)
        assert any(e.change_summary.startswith("Adapted library lesson") for e in edits)


@pytest.mark.unit
class TestBehavioralProber:
    """Tests for BehavioralProber contrast extraction without ground truth."""

    def test_error_mitigation_detection(self) -> None:
        ref_exec = ExecutionRecord(
            harness_id="ref",
            trajectory=[{"step": 1, "action": "act_a"}],
            deliverable="some result",
            errors_encountered=["Error 1", "Error 2"],
        )
        cand_exec = ExecutionRecord(
            harness_id="cand",
            trajectory=[{"step": 1, "action": "act_a"}, {"step": 2, "action": "act_b"}],
            deliverable="improved result",
            errors_encountered=[],
        )

        contrasts = BehavioralProber.extract_contrasts(ref_exec, cand_exec)
        assert contrasts["error_mitigated"] is True
        assert contrasts["new_errors"] is False
        assert contrasts["improved"] is True
        assert contrasts["regressed"] is False

    def test_regression_detection_on_new_errors_or_empty_deliverable(self) -> None:
        ref_exec = ExecutionRecord(
            harness_id="ref",
            trajectory=[{"step": 1, "action": "a"}],
            deliverable="full deliverable",
            errors_encountered=[],
        )
        cand_exec = ExecutionRecord(
            harness_id="cand_regressed",
            trajectory=[{"step": 1, "action": "a"}],
            deliverable="",  # Emptied output
            errors_encountered=["Critical crash"],
        )

        contrasts = BehavioralProber.extract_contrasts(ref_exec, cand_exec)
        assert contrasts["new_errors"] is True
        assert contrasts["regressed"] is True
        assert contrasts["improved"] is False

    def test_trajectory_divergence_step(self) -> None:
        ref_exec = ExecutionRecord(
            harness_id="ref",
            trajectory=[
                {"step": 0, "action": "load_data"},
                {"step": 1, "action": "run_eval"},
                {"step": 2, "action": "retry"},
            ],
            deliverable="done",
        )
        cand_exec = ExecutionRecord(
            harness_id="cand",
            trajectory=[
                {"step": 0, "action": "load_data"},
                {"step": 1, "action": "deterministic_check"},
                {"step": 2, "action": "emit"},
            ],
            deliverable="done",
        )

        contrasts = BehavioralProber.extract_contrasts(ref_exec, cand_exec)
        assert contrasts["divergence_step"] == 1


@pytest.mark.unit
class TestContrastiveComposer:
    """Tests for selective composition based on contrast evidence."""

    def test_compose_adopts_supported_edits(self) -> None:
        base = HarnessDefinition(
            harness_id="base",
            components={HarnessComponentType.PROMPT: "Base"},
        )
        inv_cand = HarnessDefinition(
            harness_id="inv",
            components={
                HarnessComponentType.PROMPT: "Base",
                HarnessComponentType.GUARDRAILS: "Guardrail X",
            },
        )
        dom_cand = HarnessDefinition(
            harness_id="dom",
            components={
                HarnessComponentType.PROMPT: "Base",
                HarnessComponentType.SKILLS: "Skill Y",
            },
        )
        edits = [
            ComponentEdit(
                component=HarnessComponentType.GUARDRAILS,
                candidate_scope="INV",
                change_summary="Add guard",
                diff_content="Guardrail X",
            ),
            ComponentEdit(
                component=HarnessComponentType.SKILLS,
                candidate_scope="DOM",
                change_summary="Add skill",
                diff_content="Skill Y",
            ),
        ]

        inv_contrast = {"improved": True, "regressed": False, "divergence_step": 1}
        dom_contrast = {"improved": True, "regressed": False, "divergence_step": 2}

        succ, final_edits = ContrastiveComposer.compose(
            base_harness=base,
            inv_candidate=inv_cand,
            dom_candidate=dom_cand,
            inv_contrast=inv_contrast,
            dom_contrast=dom_contrast,
            proposed_edits=edits,
        )

        assert succ.get_content(HarnessComponentType.GUARDRAILS) == "Guardrail X"
        assert succ.get_content(HarnessComponentType.SKILLS) == "Skill Y"
        assert len(final_edits) == 2
        assert all(e.verdict == HarnessVerdict.HELPED for e in final_edits)

    def test_compose_rejects_regressions(self) -> None:
        base = HarnessDefinition(
            harness_id="base",
            components={HarnessComponentType.PROMPT: "Base"},
        )
        inv_cand = HarnessDefinition(
            harness_id="inv",
            components={HarnessComponentType.GUARDRAILS: "Bad guard"},
        )
        dom_cand = HarnessDefinition(
            harness_id="dom",
            components={HarnessComponentType.SKILLS: "Good skill"},
        )
        edits = [
            ComponentEdit(
                component=HarnessComponentType.GUARDRAILS,
                candidate_scope="INV",
                change_summary="Add bad guard",
                diff_content="Bad guard",
            ),
            ComponentEdit(
                component=HarnessComponentType.SKILLS,
                candidate_scope="DOM",
                change_summary="Add good skill",
                diff_content="Good skill",
            ),
        ]

        inv_contrast = {"improved": False, "regressed": True}
        dom_contrast = {"improved": True, "regressed": False}

        succ, final_edits = ContrastiveComposer.compose(
            base_harness=base,
            inv_candidate=inv_cand,
            dom_candidate=dom_cand,
            inv_contrast=inv_contrast,
            dom_contrast=dom_contrast,
            proposed_edits=edits,
        )

        # Only DOM should be adopted
        assert succ.get_content(HarnessComponentType.SKILLS) == "Good skill"
        assert HarnessComponentType.GUARDRAILS not in succ.components
        assert len(final_edits) == 1
        assert edits[0].verdict == HarnessVerdict.HURT


@pytest.mark.unit
class TestHarnessingReflector:
    """Tests for Confounding Doctrine and transferable experience extraction."""

    def test_clean_unconfounded_reflection(self) -> None:
        base = HarnessDefinition(harness_id="b1")
        edits = [
            ComponentEdit(
                component=HarnessComponentType.GUARDRAILS,
                candidate_scope="INV",
                change_summary="Suppressed loop",
                diff_content="diff",
                observed_difference="Mitigated 2 infinite loops",
                verdict=HarnessVerdict.HELPED,
            )
        ]

        evaluated, exp = HarnessingReflector.reflect(
            task_id="task_001",
            base_harness=base,
            candidate_edits=edits,
            final_deliverable="Structured answer verified.",
        )

        assert len(evaluated) == 1
        assert evaluated[0].verdict == HarnessVerdict.HELPED
        assert exp is not None
        assert exp.component == HarnessComponentType.GUARDRAILS
        assert exp.task_id == "task_001"
        assert "Suppressed loop" in exp.lesson
        assert exp.confidence == "high"

    def test_confounding_doctrine_enforcement_on_multi_component_edits(self) -> None:
        """If >2 components changed simultaneously and were adopted together, mark CONFOUNDED."""
        base = HarnessDefinition(harness_id="b2")
        edits = [
            ComponentEdit(
                component=HarnessComponentType.PROMPT,
                candidate_scope="INV",
                change_summary="Edit prompt",
                diff_content="p",
                verdict=HarnessVerdict.HELPED,
            ),
            ComponentEdit(
                component=HarnessComponentType.GUARDRAILS,
                candidate_scope="INV",
                change_summary="Edit guardrails",
                diff_content="g",
                verdict=HarnessVerdict.HELPED,
            ),
            ComponentEdit(
                component=HarnessComponentType.SKILLS,
                candidate_scope="DOM",
                change_summary="Edit skills",
                diff_content="s",
                verdict=HarnessVerdict.HELPED,
            ),
        ]

        evaluated, _exp = HarnessingReflector.reflect(
            task_id="task_confounded",
            base_harness=base,
            candidate_edits=edits,
            final_deliverable="Deliverable output.",
        )

        # First edit remains HELPED, but subsequent edits in multi-bundle are marked CONFOUNDED
        assert evaluated[0].verdict == HarnessVerdict.HELPED
        assert evaluated[1].verdict == HarnessVerdict.CONFOUNDED
        assert evaluated[2].verdict == HarnessVerdict.CONFOUNDED
        assert "CONFOUNDED" in evaluated[1].observed_difference


@pytest.mark.unit
class TestHarnessLibraryStore:
    """Tests for file-based and SurrealDB experience store."""

    def test_save_and_list_experiences(self, tmp_path: pytest.TempPathFactory) -> None:
        store = HarnessLibraryStore(store_dir=tmp_path / "harness_lib")

        exp = HarnessExperience(
            experience_id="exp_test_01",
            cue="Repeated JSON parse failure",
            lesson="Validate JSON schema via scripts/validator.py",
            evidence="Eliminated 3 runtime SchemaErrors",
            confidence="high",
            task_id="task_test_123",
            component=HarnessComponentType.SCRIPTS,
        )

        # Mock out urllib request to avoid relying on live SurrealDB
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_url.return_value.__enter__.return_value = mock_resp

            saved_path = store.save_experience(exp)
            assert saved_path.exists()

        # Reload and filter
        all_exps = store.list_experiences()
        assert len(all_exps) == 1
        assert all_exps[0].experience_id == "exp_test_01"
        assert all_exps[0].component == HarnessComponentType.SCRIPTS

        filtered_prompt = store.list_experiences(component=HarnessComponentType.PROMPT)
        assert len(filtered_prompt) == 0

        filtered_scripts = store.list_experiences(component=HarnessComponentType.SCRIPTS)
        assert len(filtered_scripts) == 1


@pytest.mark.unit
class TestHarness2EngineIntegration:
    """Full integration test of the contrastive improvement cycle."""

    def test_full_contrastive_step(self, tmp_path: pytest.TempPathFactory) -> None:
        store = HarnessLibraryStore(store_dir=tmp_path / "integration_lib")
        engine = Harness2Engine(store=store)

        base_harness = HarnessDefinition(
            harness_id="arc_base",
            components={HarnessComponentType.PROMPT: "ARC Solver"},
        )
        ref_exec = ExecutionRecord(
            harness_id="arc_base",
            trajectory=[{"step": 0, "action": "inspect_task"}, {"step": 1, "action": "fail"}],
            deliverable="incomplete grid",
            errors_encountered=["IndexError: grid shape out of bounds"],
        )

        def mock_probe_runner(harness: HarnessDefinition) -> ExecutionRecord:
            if "_inv" in harness.harness_id:
                return ExecutionRecord(
                    harness_id=harness.harness_id,
                    trajectory=[
                        {"step": 0, "action": "inspect_task"},
                        {"step": 1, "action": "run_script_validator"},
                    ],
                    deliverable="valid 3x3 grid",
                    errors_encountered=[],  # Error mitigated
                )
            if "_dom" in harness.harness_id:
                return ExecutionRecord(
                    harness_id=harness.harness_id,
                    trajectory=[
                        {"step": 0, "action": "inspect_task"},
                        {"step": 1, "action": "contract_check"},
                    ],
                    deliverable="valid 3x3 grid with domain invariants",
                    errors_encountered=[],
                )
            # Successor run
            return ExecutionRecord(
                harness_id=harness.harness_id,
                trajectory=[
                    {"step": 0, "action": "inspect_task"},
                    {"step": 1, "action": "composed_success"},
                ],
                deliverable="final optimal solution",
                errors_encountered=[],
            )

        with patch("urllib.request.urlopen"):
            succ_harness, succ_exec, exp, edits = engine.run_contrastive_improvement_step(
                task_id="arc_task_42",
                task_query="Solve 3x3 symmetry grid",
                base_harness=base_harness,
                reference_exec=ref_exec,
                probe_runner_fn=mock_probe_runner,
            )

        assert succ_harness.harness_id == "arc_base_succ"
        assert succ_exec.deliverable == "final optimal solution"
        assert exp is not None
        assert exp.task_id == "arc_task_42"
        assert any(e.verdict == HarnessVerdict.HELPED for e in edits)
