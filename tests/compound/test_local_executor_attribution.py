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

    def test_status_failed_variant1_does_not_retry_again(self, tmp_path: Path) -> None:
        """STATUS:FAILED on variant=1 is a final failure — no third attempt."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

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
        assert call_count == 2  # variant 0 + variant 1, no more

    def test_verification_failure_does_not_trigger_variant_retry(self, tmp_path: Path) -> None:
        """Variant retry only fires on STATUS:FAILED — not on verification failure."""
        exec_ = _make_executor(tmp_path)
        task = _make_task()

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
        assert call_count == 1  # no retry on verification failure


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
