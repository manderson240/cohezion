"""Unit tests for TokenEfficientCompoundExecutor dynamic rules pruning and token optimization."""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.prompt_optimizer import PromptOptimizer
from cohezion.compound.token_efficient_executor import TokenEfficientCompoundExecutor


def test_jaccard_deduplication():
    """Verify that PromptOptimizer successfully deduplicates rule blocks via overlap coefficient."""
    optimizer = PromptOptimizer()

    block_a = "Surgical commits rule: always check git diff --cached before committing to avoid committing extra files."
    # Semantic duplicate with >65% overlap coefficient
    block_b = "Surgical commits rule: check git diff --cached before you commit to make sure you do not commit extra files."
    # Unrelated block
    block_c = "SurrealDB persistence should use port 8001 and handle connection failures gracefully with falling back to local memory store."

    content = f"{block_a}\n\n{block_b}\n\n{block_c}"
    pruned, seen = optimizer.prune_rules(content)

    # block_b should be pruned since it is a semantic duplicate of block_a
    assert block_a in pruned
    assert block_c in pruned
    assert block_b not in pruned


def test_category_relevance_pruning():
    """Verify that PromptOptimizer prunes category-specific rules that are irrelevant to the task."""
    optimizer = PromptOptimizer()

    # Make blocks longer than 60 characters to ensure relevance checks are executed
    block_db = "SurrealDB database configuration: always signin and connect to ws://localhost:8001 database server. Ensure tables are versioned and query statements are fully qualified."
    block_git = "Surgical commits git rule: always run git diff --cached --name-only command and explicitly stage target files before committing."
    block_core = "MANDATORY constraint: never print or display passwords or secrets under any circumstances, including logs, console output, and temp files."

    content = f"{block_db}\n\n{block_git}\n\n{block_core}"

    # Task is database, git rules should be pruned
    pruned_db, _ = optimizer.prune_rules(
        content, task_description="Query SurrealDB to persist learnings to tables"
    )
    assert block_db in pruned_db
    assert block_core in pruned_db
    assert block_git not in pruned_db

    # Task is git commits, database rules should be pruned
    pruned_git, _ = optimizer.prune_rules(
        content, task_description="Create a surgical git commit for the feature"
    )
    assert block_git in pruned_git
    assert block_core in pruned_git
    assert block_db not in pruned_git


@pytest.mark.asyncio
async def test_token_efficient_executor_pruning_integration():
    """Verify that TokenEfficientCompoundExecutor integrates PromptOptimizer rules pruning."""
    mock_mcp = MagicMock()
    mock_token = MagicMock()

    with (
        patch("cohezion.compound.exp_persistence.vault.VaultLogger"),
        patch("cohezion.compound.context_integration.ContextManager") as mock_cm_class,
    ):
        mock_cm = MagicMock()
        mock_cm.loaded_files = ["/dummy/rules.md"]
        # Make rules long enough to trigger relevance checks
        raw_rules = (
            "Surgical commits git rule: always run git diff --cached --name-only to check staged branches.\n\n"
            "MANDATORY constraint: Never write secrets to temp files."
        )
        mock_cm._load_file.return_value = raw_rules
        mock_cm_class.return_value = mock_cm

        executor = TokenEfficientCompoundExecutor(mock_mcp, mock_token)

        # Mock executor base methods for execution
        executor.logger = MagicMock()
        executor.logger.log_execution_start.return_value = "exp_path"

        # Running a task that does NOT mention git/commits should prune the git rules block from static prefix
        async def execute_fn(prefix, suffix):
            assert "Surgical commits" not in prefix
            assert "MANDATORY" in prefix
            return "output", {}

        with patch.object(executor, "get_experience_guidance", return_value={}):
            result = await executor.execute_task_efficient(
                task_description="Verify local model availability and metrics database",
                skill_name="test_skill",
                operation_type="analyze",
                execute_fn=execute_fn,
            )
            assert result.success
