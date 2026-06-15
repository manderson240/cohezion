"""Tests for LocalImprovementExecutor attribution-graph-inspired features.

Verifies:
- _extract_status() parses STATUS: DONE/FAILED/UNKNOWN correctly
- _extract_plan() parses === PLAN === file list and approach
- _apply_suggestions() scope guard rejects out-of-plan patches
- execute_task() STATUS gate short-circuits before file writes on STATUS:FAILED
- execute_task() retries with variant=1 after STATUS:FAILED on variant=0
- variant=1 prompt contains DIAGNOSIS section; variant=0 does not
- _build_prompt() declares === PLAN === output format in both variants
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def _make_executor(tmp_path):
    from cohezion.compound.autonomous_loop.coordinator import LoopConfig
    from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

    config = LoopConfig(local_base_url="http://localhost:19999")
    with patch.object(LocalImprovementExecutor, "_check_server"):
        exec_ = LocalImprovementExecutor(config)
    exec_._available_models = ["Qwen3.6-35B-A3B-MTP-GGUF", "Gemma-4-E4B-it-GGUF"]
    exec_._started = True
    exec_._worktree_path = str(tmp_path)
    return exec_


def _make_task(task_id: str = "t1", category: str = "test_fix"):
    from cohezion.compound.autonomous_loop.coordinator import LoopTask

    return LoopTask(
        id=task_id,
        description="Fix something",
        priority=1,
        category=category,
        verification="echo ok",
        estimated_tokens=100,
    )


class TestExtractStatus:
    def test_done_with_em_dash(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status("STATUS: DONE — Added missing import")
        assert status == "DONE"
        assert reason == "Added missing import"

    def test_failed_with_em_dash(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status(
            "STATUS: FAILED — Cannot determine root cause safely"
        )
        assert status == "FAILED"
        assert reason == "Cannot determine root cause safely"

    def test_done_with_ascii_dash(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status("STATUS: DONE - patched coordinator.py")
        assert status == "DONE"
        assert "patched" in reason

    def test_unknown_when_no_status_line(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status("Here is my analysis.\nNo status line present.")
        assert status == "UNKNOWN"
        assert reason == ""

    def test_unknown_with_unrecognized_keyword(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status("STATUS: SKIPPED — not applicable")
        assert status == "UNKNOWN"

    def test_status_embedded_in_longer_response(self, tmp_path: Path) -> None:
        response = (
            "=== FILE: foo.py ===\nx = 1\n=== END FILE ===\n"
            "=== HARNESS: python -c 'import foo' ===\n"
            "STATUS: DONE — renamed variable x to y\n"
        )
        exec_ = _make_executor(tmp_path)
        status, reason = exec_._extract_status(response)
        assert status == "DONE"
        assert "renamed" in reason


class TestExtractPlan:
    def test_parses_files_and_approach(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        response = (
            "=== PLAN ===\n"
            "files: src/foo.py, src/bar.py\n"
            "approach: rename variable and update callers\n"
            "=== END PLAN ===\n"
        )
        plan = exec_._extract_plan(response)
        assert plan["files"] == ["src/foo.py", "src/bar.py"]
        assert "rename" in plan["approach"]

    def test_empty_when_no_plan_block(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        plan = exec_._extract_plan("No plan here, just some text.")
        assert plan["files"] == []
        assert plan["approach"] == ""

    def test_single_file_in_plan(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        response = "=== PLAN ===\nfiles: coordinator.py\napproach: fix import\n=== END PLAN ==="
        plan = exec_._extract_plan(response)
        assert plan["files"] == ["coordinator.py"]

    def test_files_list_strips_whitespace(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        response = "=== PLAN ===\nfiles:  a.py ,  b.py \napproach: x\n=== END PLAN ==="
        plan = exec_._extract_plan(response)
        assert plan["files"] == ["a.py", "b.py"]


class TestScopeGuard:
    def test_patch_within_plan_is_applied(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        content = "x = 1\n"
        response = f"=== FILE: allowed.py ===\n{content}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path), plan_files={"allowed.py"})
        assert ok is True
        assert (tmp_path / "allowed.py").read_text() == content

    def test_patch_outside_plan_is_rejected(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        response = "=== FILE: sneaky.py ===\nimport os; os.system('rm -rf /')\n=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path), plan_files={"allowed.py"})
        assert ok is False
        assert any("Scope drift" in e for e in errors)
        assert not (tmp_path / "sneaky.py").exists()

    def test_no_plan_files_allows_any_patch(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        content = "y = 2\n"
        response = f"=== FILE: anything.py ===\n{content}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path), plan_files=None)
        assert ok is True
        assert (tmp_path / "anything.py").exists()

    def test_scope_guard_before_syntax_check(self, tmp_path: Path) -> None:
        """Out-of-scope file with syntax error is caught by scope guard, not syntax check."""
        exec_ = _make_executor(tmp_path)
        bad = "def foo(\n"
        response = f"=== FILE: bad.py ===\n{bad}=== END FILE ==="
        ok, errors = exec_._apply_suggestions(response, str(tmp_path), plan_files={"allowed.py"})
        assert ok is False
        assert any("Scope drift" in e for e in errors)
        # The scope guard fires first — syntax error not mentioned
        assert not any("Syntax error" in e for e in errors)


class TestStatusGate:
    def test_status_failed_short_circuits_before_file_write(self, tmp_path: Path) -> None:
        """STATUS:FAILED response must not touch disk."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        failed_response = (
            "=== FILE: coordinator.py ===\nIMPORTANT CHANGES\n=== END FILE ===\n"
            "STATUS: FAILED — cannot safely determine the root cause\n"
        )

        with (
            patch.object(exec_, "_call_lemonade", return_value=(failed_response, 50)),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_._attempt(task, str(tmp_path), "model", "", "", variant=0)

        assert result["success"] is False
        assert "declined" in result["summary"]
        # File must NOT be written despite being in the response
        assert not (tmp_path / "coordinator.py").exists()

    def test_status_done_allows_file_writes(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")

        content = "x = 1\n"
        ok_response = (
            f"=== PLAN ===\nfiles: fixed.py\napproach: lint fix\n=== END PLAN ===\n"
            f"=== FILE: fixed.py ===\n{content}=== END FILE ===\n"
            "STATUS: DONE — removed unused import\n"
        )

        with (
            patch.object(exec_, "_call_lemonade", return_value=(ok_response, 40)),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch.object(exec_, "_run_verification", return_value=(True, "")),
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_._attempt(task, str(tmp_path), "model", "", "", variant=0)

        assert result["success"] is True
        assert (tmp_path / "fixed.py").exists()


class TestVariantRetry:
    def test_status_failed_variant0_triggers_variant1_retry(self, tmp_path: Path) -> None:
        """After STATUS:FAILED on variant 0, executor retries with variant=1."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        failed_response = "STATUS: FAILED — cannot determine root cause safely\n"
        success_response = (
            "=== PLAN ===\nfiles: target.py\napproach: root cause fix\n=== END PLAN ===\n"
            "=== FILE: target.py ===\nx = 1\n=== END FILE ===\n"
            "STATUS: DONE — fixed by root cause analysis\n"
        )

        call_responses = iter([(failed_response, 30), (success_response, 60)])

        with (
            patch.object(
                exec_, "_call_lemonade", side_effect=lambda *a, **kw: next(call_responses)
            ),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch.object(exec_, "_run_verification", return_value=(True, "")),
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_.execute_task(task, str(tmp_path))

        assert result["success"] is True
        assert (tmp_path / "target.py").exists()

    def test_status_failed_variant1_is_final_for_easy_tasks(self, tmp_path: Path) -> None:
        """For easy tasks (lint_fix), STATUS:FAILED on variant=1 is final — no v2 attempt.

        Hard tasks (test_fix/type_fix or estimated_tokens>500) DO get a variant=2
        attempt; that behaviour is tested in TestPoLarVariant2.
        """
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")  # easy — not in hard-task set

        failed_response = "STATUS: FAILED — task is unsafe at every framing\n"
        call_count = 0

        def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (failed_response, 30)

        with (
            patch.object(exec_, "_call_lemonade", side_effect=count_calls),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_.execute_task(task, str(tmp_path))

        assert result["success"] is False
        assert call_count == 2  # variant 0 + variant 1; no v2 for easy tasks

    def test_verification_failure_does_not_trigger_variant1_retry(self, tmp_path: Path) -> None:
        """Variant=1 retry only fires on STATUS:FAILED — not on verification failure.

        Note: hard tasks (test_fix) DO get a variant=2 beam attempt on any failure.
        This test scopes to lint_fix (easy) to isolate the v1-retry gate.
        """
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")  # easy — no v2

        # STATUS:DONE but tests fail — this is a real failure, not a model decline
        fail_verify_response = (
            "=== PLAN ===\nfiles: f.py\napproach: attempt\n=== END PLAN ===\n"
            "=== FILE: f.py ===\nx = 1\n=== END FILE ===\n"
            "STATUS: DONE — made the change\n"
        )
        call_count = 0

        def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (fail_verify_response, 30)

        with (
            patch.object(exec_, "_call_lemonade", side_effect=count_calls),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch.object(exec_, "_run_verification", return_value=(False, "tests failed")),
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_.execute_task(task, str(tmp_path))

        assert result["success"] is False
        assert call_count == 1  # no v1 retry on verification failure for easy task


class TestPromptVariants:
    def test_variant0_prompt_has_plan_output_format(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=0)
        assert "=== PLAN ===" in prompt
        assert "=== END PLAN ===" in prompt
        assert "files:" in prompt

    def test_variant1_prompt_has_diagnosis_section(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=1)
        assert "DIAGNOSIS" in prompt
        assert "root cause" in prompt.lower()

    def test_variant0_prompt_lacks_diagnosis_section(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=0)
        assert "DIAGNOSIS" not in prompt

    def test_variant1_role_differs_from_variant0(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        p0 = exec_._build_prompt(task, variant=0)
        p1 = exec_._build_prompt(task, variant=1)

        # Extract the ROLE section from each (first paragraph after ## ROLE)
        def role_text(p: str) -> str:
            lines = p.split("\n")
            capturing = False
            result = []
            for line in lines:
                if line.strip() == "## ROLE":
                    capturing = True
                    continue
                if capturing:
                    if line.startswith("## "):
                        break
                    result.append(line)
            return "\n".join(result)

        assert role_text(p0) != role_text(p1)


class TestPoLarVariant2:
    """PoLar (2606.06574): hard tasks get a 3rd variant with minimal-footprint beam."""

    def test_max_variants_constant_is_3(self, tmp_path: Path) -> None:
        from cohezion.compound.autonomous_loop.local_executor import LocalImprovementExecutor

        assert LocalImprovementExecutor._MAX_VARIANTS == 3

    def test_is_hard_task_true_for_test_fix(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="test_fix")
        assert exec_._is_hard_task(task) is True

    def test_is_hard_task_true_for_type_fix(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="type_fix")
        assert exec_._is_hard_task(task) is True

    def test_is_hard_task_true_for_large_token_budget(self, tmp_path: Path) -> None:
        from cohezion.compound.autonomous_loop.coordinator import LoopTask

        exec_ = _make_executor(tmp_path)
        task = LoopTask(
            id="big",
            description="big task",
            priority=1,
            category="refactor",
            verification="echo ok",
            estimated_tokens=501,
        )
        assert exec_._is_hard_task(task) is True

    def test_is_hard_task_false_for_lint_fix_small_budget(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")  # estimated_tokens=100
        assert exec_._is_hard_task(task) is False

    def test_hard_task_gets_variant2_after_both_prior_variants_fail(self, tmp_path: Path) -> None:
        """test_fix task: v0 STATUS:FAILED → v1 STATUS:FAILED → v2 fires."""
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="test_fix")

        success_response = (
            "=== PLAN ===\nfiles: target.py\napproach: beam fix\n=== END PLAN ===\n"
            "=== FILE: target.py ===\nx = 42\n=== END FILE ===\n"
            "STATUS: DONE — found minimal fix via beam enumeration\n"
        )
        failed_response = "STATUS: FAILED — cannot fix safely\n"

        call_responses = iter(
            [(failed_response, 20), (failed_response, 20), (success_response, 60)]
        )

        with (
            patch.object(
                exec_, "_call_lemonade", side_effect=lambda *a, **kw: next(call_responses)
            ),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch.object(exec_, "_run_verification", return_value=(True, "")),
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_.execute_task(task, str(tmp_path))

        assert result["success"] is True
        assert (tmp_path / "target.py").read_text() == "x = 42\n"

    def test_easy_task_does_not_get_variant2(self, tmp_path: Path) -> None:
        """lint_fix: all variants fail, but v2 is NOT triggered (easy task)."""
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")

        failed_response = "STATUS: FAILED — cannot fix\n"
        call_count = 0

        def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return (failed_response, 20)

        with (
            patch.object(exec_, "_call_lemonade", side_effect=count_calls),
            patch.object(exec_, "_sweeper") as mock_sweeper,
            patch(
                "cohezion.compound.autonomous_loop.coordinator.LoopCoordinator._check_ram_before_load",
                return_value=True,
            ),
        ):
            mock_sweeper.build_task_context.return_value = ""
            result = exec_.execute_task(task, str(tmp_path))

        assert result["success"] is False
        assert call_count == 2  # v0 + v1 only; no v2 for easy tasks

    def test_variant2_prompt_has_beam_candidates_section(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=2)
        assert "BEAM CANDIDATES" in prompt
        assert "Minimal" in prompt
        assert "Structural" in prompt
        assert "Conservative" in prompt

    def test_variant2_role_differs_from_v0_and_v1(self, tmp_path: Path) -> None:
        """Discriminating: v2 role must differ from both v0 and v1."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        def role_text(p: str) -> str:
            for line in p.split("\n"):
                if line.startswith("You are"):
                    return line
            return ""

        r0 = role_text(exec_._build_prompt(task, variant=0))
        r1 = role_text(exec_._build_prompt(task, variant=1))
        r2 = role_text(exec_._build_prompt(task, variant=2))
        assert r2 != r0
        assert r2 != r1
        assert r0 != r1  # sanity check

    def test_variant2_lacks_diagnosis_section(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=2)
        assert "DIAGNOSIS" not in prompt


class TestSeeRepoImportGraph:
    """SeeRepo (2606.14061): import-graph context at fault-localization stage only."""

    def test_variant0_with_worktree_injects_repo_structure(self, tmp_path: Path) -> None:
        """Discriminating: variant=0 with a worktree containing .py files gets the
        ## REPOSITORY STRUCTURE section; a wrong implementation would omit it."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        # Write a Python file with a cohezion import into the worktree
        src_dir = tmp_path / "src" / "cohezion"
        src_dir.mkdir(parents=True)
        (src_dir / "example.py").write_text(
            "from cohezion.compound.executor import CompoundExecutor\n"
        )

        prompt = exec_._build_prompt(task, variant=0, worktree_path=str(tmp_path))
        assert "## REPOSITORY STRUCTURE" in prompt
        assert "cohezion" in prompt

    def test_variant1_does_not_inject_repo_structure(self, tmp_path: Path) -> None:
        """SeeRepo: repair stage (v1) with structural context shows degraded performance."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        src_dir = tmp_path / "src" / "cohezion"
        src_dir.mkdir(parents=True)
        (src_dir / "example.py").write_text(
            "from cohezion.compound.executor import CompoundExecutor\n"
        )

        prompt = exec_._build_prompt(task, variant=1, worktree_path=str(tmp_path))
        assert "## REPOSITORY STRUCTURE" not in prompt

    def test_variant2_does_not_inject_repo_structure(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        task = _make_task()

        src_dir = tmp_path / "src" / "cohezion"
        src_dir.mkdir(parents=True)
        (src_dir / "example.py").write_text(
            "from cohezion.compound.executor import CompoundExecutor\n"
        )

        prompt = exec_._build_prompt(task, variant=2, worktree_path=str(tmp_path))
        assert "## REPOSITORY STRUCTURE" not in prompt

    def test_import_graph_includes_cohezion_internal_imports(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)

        src_dir = tmp_path / "src" / "cohezion"
        src_dir.mkdir(parents=True)
        (src_dir / "module.py").write_text(
            "import os\nfrom cohezion.flume.vae import FlumeVAE\nimport json\n"
        )

        graph = exec_._build_import_graph(str(tmp_path))
        # stdlib (os, json) must NOT appear; cohezion import must appear
        assert "cohezion" in graph
        assert "FlumeVAE" in graph or "cohezion.flume.vae" in graph

    def test_import_graph_empty_when_no_cohezion_imports(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)

        src_dir = tmp_path / "src" / "cohezion"
        src_dir.mkdir(parents=True)
        (src_dir / "pure_stdlib.py").write_text("import os\nimport json\n")

        graph = exec_._build_import_graph(str(tmp_path))
        assert graph == ""

    def test_import_graph_empty_when_no_src_dir(self, tmp_path: Path) -> None:
        exec_ = _make_executor(tmp_path)
        graph = exec_._build_import_graph(str(tmp_path))
        assert graph == ""

    def test_variant0_without_worktree_has_no_repo_structure(self, tmp_path: Path) -> None:
        """When worktree_path is empty string (default), no repo structure is injected."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()
        prompt = exec_._build_prompt(task, variant=0)
        assert "## REPOSITORY STRUCTURE" not in prompt


class TestMultiLabelRouting:
    """Multi-label task categories (scikit-llm multi-label pattern).

    LoopTask.categories is a tuple of task labels; __post_init__ derives it from
    category when not supplied. Model selection and hard-task detection are any-match.
    """

    def test_loop_task_derives_categories_from_category(self) -> None:
        """__post_init__ sets categories=(category,) when not supplied explicitly."""
        task = _make_task(category="test_fix")
        assert task.categories == ("test_fix",)

    def test_loop_task_explicit_multi_label(self) -> None:
        """Caller can supply explicit multi-label tuple."""
        from cohezion.compound.autonomous_loop.coordinator import LoopTask

        task = LoopTask(
            id="ml1",
            description="Fix test with type error",
            priority=1,
            category="test_fix",
            verification="pytest",
            estimated_tokens=300,
            categories=("test_fix", "type_fix"),
        )
        assert task.categories == ("test_fix", "type_fix")

    def test_categories_not_overridden_when_supplied(self) -> None:
        """__post_init__ must NOT overwrite an explicitly supplied categories tuple."""
        from cohezion.compound.autonomous_loop.coordinator import LoopTask

        task = LoopTask(
            id="ml2",
            description="desc",
            priority=0,
            category="lint_fix",
            verification="echo ok",
            estimated_tokens=50,
            categories=("lint_fix", "refactor"),
        )
        assert task.categories == ("lint_fix", "refactor")

    def test_is_hard_task_any_match_positive(self, tmp_path: Path) -> None:
        """Task with categories=("lint_fix", "test_fix") is hard (any-match)."""
        from cohezion.compound.autonomous_loop.coordinator import LoopTask

        exec_ = _make_executor(tmp_path)
        task = LoopTask(
            id="h1",
            description="desc",
            priority=0,
            category="lint_fix",
            verification="echo ok",
            estimated_tokens=50,
            categories=("lint_fix", "test_fix"),
        )
        assert exec_._is_hard_task(task) is True

    def test_is_hard_task_single_easy_label(self, tmp_path: Path) -> None:
        """Single easy label is still not hard."""
        exec_ = _make_executor(tmp_path)
        task = _make_task(category="lint_fix")
        assert exec_._is_hard_task(task) is False

    def test_prompt_shows_all_categories(self, tmp_path: Path) -> None:
        """Category field in prompt lists all labels for multi-label tasks."""
        from cohezion.compound.autonomous_loop.coordinator import LoopTask

        exec_ = _make_executor(tmp_path)
        task = LoopTask(
            id="p1",
            description="desc",
            priority=0,
            category="test_fix",
            verification="echo ok",
            estimated_tokens=100,
            categories=("test_fix", "type_fix"),
        )
        prompt = exec_._build_prompt(task, variant=0)
        assert "test_fix" in prompt
        assert "type_fix" in prompt
