"""Tests for Language Self-Play (LSP, arXiv:2509.07414) in autonomous_loop."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cohezion.compound.autonomous_loop.rzero_challenger import (
    ChallengerAgent,
    EpisodeResult,
    GroupTaskAttempt,
    RZeroChallengerExecutor,
    SolverAgent,
    TaskAttempt,
    compute_rq,
    evaluate_code_ast,
)


class TestLspAstAndQualityEvaluation:
    def test_evaluate_code_ast_valid_fenced(self) -> None:
        snippet = "```python\ndef solve() -> int:\n    return 42\n```"
        valid, msg = evaluate_code_ast(snippet)
        assert valid
        assert "cleanly" in msg

    def test_evaluate_code_ast_syntax_error(self) -> None:
        snippet = "```python\ndef bad(\n```"
        valid, msg = evaluate_code_ast(snippet)
        assert not valid
        assert "syntax error" in msg.lower()

    def test_evaluate_code_ast_valid_inline(self) -> None:
        code = "import os\ndef test(): pass"
        valid, msg = evaluate_code_ast(code)
        assert valid
        assert "valid Python AST" in msg

    def test_evaluate_code_ast_empty_and_prose(self) -> None:
        assert not evaluate_code_ast("")[0]
        assert not evaluate_code_ast("Hello world just text here")[0]

    def test_compute_rq_evasive_or_empty(self) -> None:
        score, ast_ok = compute_rq("Task 1", "")
        assert score == 0.0
        assert not ast_ok

        score, ast_ok = compute_rq("Task 1", "No concrete change found in repository.")
        assert score == 0.0
        assert not ast_ok

    def test_compute_rq_concrete_and_adherent(self) -> None:
        response = (
            "1. File: src/cohezion/compound/executor.py\n"
            "2. Change: add return type and fix logic at line 40\n"
            "```python\ndef get_status() -> str:\n    return 'ready'\n```\n"
            "3. This improves robustness and resolves typing."
        )
        score, ast_ok = compute_rq("Improve typing in executor.py", response)
        assert score >= 0.8
        assert ast_ok


class TestChallengerAgent:
    def test_difficulty_hint(self) -> None:
        agent = ChallengerAgent()
        assert "mix of easy and hard" in agent._difficulty_hint(None)
        assert "HARDER" in agent._difficulty_hint(0.8)
        assert "EASIER" in agent._difficulty_hint(0.2)
        assert "well-calibrated" in agent._difficulty_hint(0.5)

    def test_parse_numbered_list(self) -> None:
        agent = ChallengerAgent()
        text = "1. Refactor executor\n2. Add test for cache\n3. Fix typing"
        tasks = agent._parse_numbered_list(text, 3)
        assert len(tasks) == 3
        assert tasks[0] == "Refactor executor"
        assert tasks[1] == "Add test for cache"
        assert tasks[2] == "Fix typing"

    def test_parse_numbered_list_fallback_on_empty(self) -> None:
        agent = ChallengerAgent()
        tasks = agent._parse_numbered_list("", 2)
        assert len(tasks) == 2
        assert "Review src/cohezion" in tasks[0]


class TestSolverAgentLsp:
    @patch("cohezion.compound.autonomous_loop.rzero_challenger._chat")
    def test_attempt_task_group(self, mock_chat: MagicMock) -> None:
        mock_chat.side_effect = [
            (
                "src/cohezion/compound/executor.py line 12: add type annotation",
                {},
            ),
            (
                "No concrete change found.",
                {},
            ),
        ]
        solver = SolverAgent()
        group = solver.attempt_task_group("Task", "task-01", group_size=2)

        assert isinstance(group, GroupTaskAttempt)
        assert len(group.candidates) == 2
        # Candidate 0 succeeded (R=1.0), Candidate 1 failed (R=0.0)
        assert group.candidates[0].reward_r == 1.0
        assert group.candidates[1].reward_r == 0.0
        # Group baseline V(q_i) = (1.0 + 0.0) / 2 = 0.5
        assert group.group_baseline_v == 0.5
        # Solver advantages: R - V
        assert group.candidates[0].solver_advantage == 0.5
        assert group.candidates[1].solver_advantage == -0.5
        assert group.best_candidate_idx == 0

    @patch("cohezion.compound.autonomous_loop.rzero_challenger._chat")
    def test_attempt_task_backward_compatible(self, mock_chat: MagicMock) -> None:
        mock_chat.return_value = (
            "src/cohezion/compound/executor.py line 12: def run(): pass",
            {},
        )
        solver = SolverAgent()
        attempt = solver.attempt_task("Task", "task-01")

        assert isinstance(attempt, TaskAttempt)
        assert attempt.quality_score == 1.0
        assert attempt.task_id == "task-01"
        assert attempt.solver_advantage == 0.0


class TestRZeroChallengerExecutorLsp:
    @patch("cohezion.compound.autonomous_loop.rzero_challenger._push_episode_to_vault")
    @patch("cohezion.compound.autonomous_loop.rzero_challenger._vault_quality_context")
    @patch("cohezion.compound.autonomous_loop.rzero_challenger._web_search_enrich")
    @patch("cohezion.compound.autonomous_loop.rzero_challenger._chat")
    def test_run_episode_lsp(
        self,
        mock_chat: MagicMock,
        mock_search: MagicMock,
        mock_vault: MagicMock,
        mock_push: MagicMock,
    ) -> None:
        mock_search.return_value = ""
        mock_vault.return_value = ""

        # Mock sequence:
        # 1. Challenger generates 2 tasks
        # 2. Solver attempts Task 1 candidate 1
        # 3. Solver attempts Task 1 candidate 2
        # 4. Solver attempts Task 2 candidate 1
        # 5. Solver attempts Task 2 candidate 2
        mock_chat.side_effect = [
            # Challenger output
            ("1. Task A\n2. Task B", {}),
            # Task 1 Candidate 1 (Success)
            ("src/cohezion/a.py line 5: fix typing because it improves code", {}),
            # Task 1 Candidate 2 (Evasion)
            ("No concrete change found", {}),
            # Task 2 Candidate 1 (Success)
            ("src/cohezion/b.py line 10: add function because it improves test", {}),
            # Task 2 Candidate 2 (Success)
            ("src/cohezion/b.py line 12: replace loop", {}),
        ]

        executor = RZeroChallengerExecutor(group_size=2)
        res = executor.run_episode(n_tasks=2, group_size=2)

        assert isinstance(res, EpisodeResult)
        assert len(res.tasks) == 2
        assert len(res.group_tasks) == 2

        # Task 1 group: V = (1.0 + 0.0)/2 = 0.5
        assert res.group_tasks[0].group_baseline_v == 0.5
        # Task 2 group: V = (1.0 + 1.0)/2 = 1.0
        assert res.group_tasks[1].group_baseline_v == 1.0

        # Global baseline V = (0.5 + 1.0)/2 = 0.75
        assert res.global_baseline_v == 0.75
        assert res.mean_success == 0.75

        # Challenger advantages A_Ch = V - V(q_i) + gamma * V_Q(q_i)
        # For task 1: V - V(q_1) = 0.75 - 0.5 = +0.25 (Challenger found a harder problem!)
        assert res.group_tasks[0].challenger_advantage > 0.25

        # Check vault push was invoked
        mock_push.assert_called_once_with(res)
