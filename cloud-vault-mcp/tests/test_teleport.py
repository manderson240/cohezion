"""Tests for CloudTeleportProtocol — file-based task delegation."""

import pytest

from mcp_server.teleport import CloudTeleportProtocol
from mcp_server.vault_ops import VaultOps


@pytest.fixture
def vault(tmp_path):
    return VaultOps(str(tmp_path))


@pytest.fixture
def teleport(vault):
    return CloudTeleportProtocol(vault)


class TestCloudTeleportProtocol:
    def test_create_task(self, teleport, vault):
        result = teleport.create_task("Test task", "Do something")
        assert result["title"] == "Test task"
        assert result["status"] == "pending"
        assert result["priority"] == "medium"
        assert len(result["id"]) == 12
        assert result["assigned_to"] == ""
        # Verify file exists
        content = vault.read(f"teleport/tasks/{result['id']}.md")
        assert "Test task" in content
        assert "Do something" in content

    def test_create_task_all_params(self, teleport, vault):
        result = teleport.create_task(
            title="Full task",
            description="Detailed work",
            context="Some background info",
            expected_output="A report",
            priority="high",
        )
        assert result["priority"] == "high"
        assert result["expected_output"] == "A report"
        content = vault.read(f"teleport/tasks/{result['id']}.md")
        assert "Some background info" in content
        assert "Detailed work" in content
        assert "## Context" in content

    def test_list_tasks_empty(self, teleport):
        tasks = teleport.list_tasks()
        assert tasks == []

    def test_list_tasks(self, teleport):
        teleport.create_task("Task 1", "First")
        teleport.create_task("Task 2", "Second")
        teleport.create_task("Task 3", "Third")
        tasks = teleport.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_filter_status(self, teleport):
        t1 = teleport.create_task("Pending task", "Stay pending")
        t2 = teleport.create_task("Will claim", "To be claimed")
        teleport.claim_task(t2["id"], "worker-1")

        pending = teleport.list_tasks(status="pending")
        assert len(pending) == 1
        assert pending[0]["id"] == t1["id"]

        in_progress = teleport.list_tasks(status="in_progress")
        assert len(in_progress) == 1
        assert in_progress[0]["id"] == t2["id"]

    def test_claim_task(self, teleport):
        task = teleport.create_task("Claimable", "Grab it")
        claimed = teleport.claim_task(task["id"], "cloud-claude")
        assert claimed["status"] == "in_progress"
        assert claimed["assigned_to"] == "cloud-claude"

    def test_claim_already_claimed(self, teleport):
        task = teleport.create_task("Already taken", "Nope")
        teleport.claim_task(task["id"], "worker-1")
        with pytest.raises(ValueError, match="not pending"):
            teleport.claim_task(task["id"], "worker-2")

    def test_complete_task(self, teleport, vault):
        task = teleport.create_task("Completable", "Finish it")
        teleport.claim_task(task["id"], "worker")
        completed = teleport.complete_task(task["id"], "Here is the answer")
        assert completed["status"] == "completed"
        # Verify result file
        result_content = vault.read(f"teleport/results/{task['id']}.md")
        assert "Here is the answer" in result_content
        assert task["id"] in result_content

    def test_complete_unclaimed(self, teleport):
        task = teleport.create_task("Not claimed", "Cannot complete")
        with pytest.raises(ValueError, match="not in_progress"):
            teleport.complete_task(task["id"], "result")

    def test_fail_task(self, teleport):
        task = teleport.create_task("Will fail", "Doomed")
        teleport.claim_task(task["id"], "worker")
        failed = teleport.fail_task(task["id"], "Something broke")
        assert failed["status"] == "failed"
        assert failed["error"] == "Something broke"

    def test_get_result(self, teleport):
        task = teleport.create_task("Get result", "Need answer")
        teleport.claim_task(task["id"], "worker")
        teleport.complete_task(task["id"], "The final answer is 42")
        result = teleport.get_result(task["id"])
        assert result["task_id"] == task["id"]
        assert "The final answer is 42" in result["result"]
        assert result["metadata"]["task_id"] == task["id"]

    def test_get_result_missing(self, teleport):
        with pytest.raises(FileNotFoundError, match="No result found"):
            teleport.get_result("nonexistent123")

    def test_full_lifecycle(self, teleport):
        # Create
        task = teleport.create_task(
            "Lifecycle test",
            "Full round trip",
            context="Testing everything",
            expected_output="Success confirmation",
            priority="high",
        )
        assert task["status"] == "pending"

        # List
        tasks = teleport.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == task["id"]

        # Claim
        claimed = teleport.claim_task(task["id"], "integration-tester")
        assert claimed["status"] == "in_progress"
        assert claimed["assigned_to"] == "integration-tester"

        # Complete
        completed = teleport.complete_task(task["id"], "All checks passed")
        assert completed["status"] == "completed"

        # Get result
        result = teleport.get_result(task["id"])
        assert "All checks passed" in result["result"]

        # Verify listing reflects final state
        all_tasks = teleport.list_tasks()
        assert all_tasks[0]["status"] == "completed"
        completed_only = teleport.list_tasks(status="completed")
        assert len(completed_only) == 1
