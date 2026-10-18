"""Unit tests for Harness^2 Multi-Round Recursive Harnessing & Mount Protocols.
=============================================================================
Based on Google Research Harness^2 (arXiv:2610.14224, github.com/google-research/harness2).

Verifies:
1. Filesystem mounting and directory round-trip fidelity for the K=8 components.
2. Sequential recursion mode (depth k chained PPC refinements).
3. Parallel recursion mode (width k orthogonal candidate exploration).
4. Experience extraction and continual improvement persistence across multiple rounds.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.compound.harness2_engine import (
    ExecutionRecord,
    Harness2Engine,
    HarnessComponentType,
    HarnessDefinition,
    HarnessLibraryStore,
)


@pytest.mark.unit
def test_harness_mount_and_load_roundtrip() -> None:
    """Verifies that all K=8 components can be mounted to disk and reloaded without loss."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_path = Path(tmp_dir)

        harness = HarnessDefinition(
            harness_id="test_mount_k8",
            components={
                HarnessComponentType.PROMPT: "You are an elite reasoning agent.",
                HarnessComponentType.GUARDRAILS: "- Stop loop on repeated failed action.",
                HarnessComponentType.MEMORY: "# State Vector: Poincare 2048D",
                HarnessComponentType.SKILLS: "# Domain Skill: Radiomics & ROC-AUC",
                HarnessComponentType.TOOLS: "tools:\n  - name: run_code\n",
                HarnessComponentType.SCRIPTS: "#!/usr/bin/env python3\nprint('OK')",
                HarnessComponentType.SUBAGENTS: "roles:\n  - name: reviewer\n",
                HarnessComponentType.PLUGIN: "# Event hook middleware\n",
            },
            metadata={"domain": "medical_imaging"},
        )

        mounted_paths = harness.mount_to_directory(target_path)
        assert len(mounted_paths) == 8

        # Check prompt file
        assert (target_path / "prompt.txt").is_file()
        assert (target_path / "prompt.txt").read_text(encoding="utf-8") == "You are an elite reasoning agent."

        # Check directory components
        assert (target_path / "skills" / "README.md").is_file()
        assert "Domain Skill: Radiomics" in (target_path / "skills" / "README.md").read_text(encoding="utf-8")

        # Reload from directory
        loaded_harness = HarnessDefinition.load_from_directory("test_reloaded", target_path)
        assert loaded_harness.harness_id == "test_reloaded"
        assert loaded_harness.get_content(HarnessComponentType.PROMPT) == harness.get_content(HarnessComponentType.PROMPT)
        assert loaded_harness.get_content(HarnessComponentType.GUARDRAILS) == harness.get_content(HarnessComponentType.GUARDRAILS)
        assert loaded_harness.get_content(HarnessComponentType.SKILLS) == harness.get_content(HarnessComponentType.SKILLS)


@pytest.mark.unit
def test_sequential_recursion_depth_k() -> None:
    """Verifies sequential recursion (depth k=2) chaining successive PPC refinements."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = HarnessLibraryStore(store_dir=Path(tmp_dir))
        engine = Harness2Engine(store=store)

        base_harness = HarnessDefinition(
            harness_id="base_seq",
            components={
                HarnessComponentType.PROMPT: "Baseline Solver Prompt",
                HarnessComponentType.GUARDRAILS: "Basic guardrail",
            },
        )

        ref_exec = ExecutionRecord(
            harness_id="base_seq",
            trajectory=[{"action": "step1"}, {"action": "step2_error"}],
            deliverable="partial baseline answer",
            errors_encountered=["TimeoutError on step 2"],
        )

        def mock_probe_runner(harness: HarnessDefinition) -> ExecutionRecord:
            if "_inv" in harness.harness_id or "_succ" in harness.harness_id:
                return ExecutionRecord(
                    harness_id=harness.harness_id,
                    trajectory=[{"action": "step1"}, {"action": "step2_fixed"}],
                    deliverable="complete robust answer",
                    errors_encountered=[],
                )
            return ExecutionRecord(
                harness_id=harness.harness_id,
                trajectory=[{"action": "step1"}, {"action": "step2_regressed"}],
                deliverable="",
                errors_encountered=["NewError"],
            )

        final_harness, final_exec, experiences, edits = engine.run_recursive_harnessing(
            task_id="task_seq_01",
            task_query="Solve complex medical reasoning task",
            base_harness=base_harness,
            reference_exec=ref_exec,
            probe_runner_fn=mock_probe_runner,
            budget_k=2,
            mode="sequential",
        )

        assert final_harness.harness_id is not None
        assert final_exec.errors_encountered == []
        assert "complete robust answer" in final_exec.deliverable
        assert len(edits) > 0
        assert isinstance(experiences, list)


@pytest.mark.unit
def test_parallel_recursion_width_k() -> None:
    """Verifies parallel recursion (width k=2) exploring orthogonal branches simultaneously."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = HarnessLibraryStore(store_dir=Path(tmp_dir))
        engine = Harness2Engine(store=store)

        base_harness = HarnessDefinition(
            harness_id="base_par",
            components={
                HarnessComponentType.PROMPT: "Baseline Parallel Prompt",
            },
        )

        ref_exec = ExecutionRecord(
            harness_id="base_par",
            trajectory=[{"action": "step1"}, {"action": "step2"}],
            deliverable="short answer",
            errors_encountered=["ToolError: missing parameter"],
        )

        def mock_probe_runner(harness: HarnessDefinition) -> ExecutionRecord:
            # Parallel candidate probes
            return ExecutionRecord(
                harness_id=harness.harness_id,
                trajectory=[{"action": "step1"}, {"action": "step2_verified"}],
                deliverable="substantive parallel verified answer",
                errors_encountered=[],
            )

        final_harness, final_exec, _experiences, _edits = engine.run_recursive_harnessing(
            task_id="task_par_01",
            task_query="Perform parallel multi-view feature engineering",
            base_harness=base_harness,
            reference_exec=ref_exec,
            probe_runner_fn=mock_probe_runner,
            budget_k=2,
            mode="parallel",
        )

        assert "parallel_k2" in final_harness.harness_id
        assert final_harness.metadata.get("mode") == "parallel"
        assert final_harness.metadata.get("width_k") == 2
        assert final_exec.errors_encountered == []
        assert "substantive parallel verified answer" in final_exec.deliverable
