"""Cloud Teleport Protocol — file-based task delegation between Claude instances."""

import contextlib
import logging
import uuid
from datetime import UTC, datetime

import yaml

from .vault_ops import VaultOps


logger = logging.getLogger(__name__)


class CloudTeleportProtocol:
    """File-based task queue for delegating work between local and cloud Claude."""

    def __init__(self, vault: VaultOps):
        self._vault = vault
        # Ensure directories exist
        self._vault.write("teleport/tasks/.gitkeep", "")
        self._vault.write("teleport/results/.gitkeep", "")

    def create_task(
        self,
        title: str,
        description: str,
        context: str = "",
        expected_output: str = "",
        priority: str = "medium",
    ) -> dict:
        """Create a new teleport task."""
        task_id = uuid.uuid4().hex[:12]
        now = datetime.now(UTC).isoformat()

        metadata = {
            "id": task_id,
            "title": title,
            "status": "pending",
            "priority": priority,
            "created_at": now,
            "updated_at": now,
            "assigned_to": "",
            "expected_output": expected_output,
        }

        body = f"# {title}\n\n"
        if context:
            body += f"## Context\n\n{context}\n\n"
        body += f"## Description\n\n{description}\n"

        self._write_task(task_id, metadata, body)
        logger.info("Created teleport task: %s — %s", task_id, title)
        return metadata

    def list_tasks(self, status: str | None = None) -> list[dict]:
        """List all teleport tasks, optionally filtered by status."""
        tasks = []
        try:
            files = self._vault.list_dir("teleport/tasks", recursive=False)
        except FileNotFoundError:
            return tasks

        for filename in files:
            if not filename.endswith(".md") or filename.endswith(".gitkeep"):
                continue
            task_id = filename.replace("teleport/tasks/", "").replace(".md", "")
            try:
                task = self._read_task(task_id)
                if status is None or task.get("status") == status:
                    tasks.append(task)
            except (FileNotFoundError, ValueError):
                continue

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks

    def claim_task(self, task_id: str, assigned_to: str) -> dict:
        """Claim a pending task for processing."""
        task = self._read_task(task_id)

        if task["status"] != "pending":
            raise ValueError(
                f"Task {task_id} is not pending (status: {task['status']})"
            )

        task["status"] = "in_progress"
        task["assigned_to"] = assigned_to
        task["updated_at"] = datetime.now(UTC).isoformat()

        self._write_task(task_id, task, task.pop("_body", ""))
        logger.info("Task %s claimed by %s", task_id, assigned_to)
        return task

    def complete_task(self, task_id: str, result: str) -> dict:
        """Complete a task and write the result."""
        task = self._read_task(task_id)

        if task["status"] != "in_progress":
            raise ValueError(
                f"Task {task_id} is not in_progress (status: {task['status']})"
            )

        task["status"] = "completed"
        task["updated_at"] = datetime.now(UTC).isoformat()

        # Write result
        result_content = f"""---
task_id: {task_id}
title: {task.get("title", "")}
completed_at: {task["updated_at"]}
assigned_to: {task.get("assigned_to", "")}
---
# Result: {task.get("title", "")}

{result}
"""
        self._vault.write(f"teleport/results/{task_id}.md", result_content)

        # Update task status
        self._write_task(task_id, task, task.pop("_body", ""))
        logger.info("Task %s completed", task_id)
        return task

    def fail_task(self, task_id: str, error: str) -> dict:
        """Mark a task as failed."""
        task = self._read_task(task_id)

        task["status"] = "failed"
        task["updated_at"] = datetime.now(UTC).isoformat()
        task["error"] = error

        self._write_task(task_id, task, task.pop("_body", ""))
        logger.info("Task %s failed: %s", task_id, error)
        return task

    def get_result(self, task_id: str) -> dict:
        """Get the result of a completed task."""
        result_path = f"teleport/results/{task_id}.md"
        try:
            content = self._vault.read(result_path)
        except FileNotFoundError as err:
            raise FileNotFoundError(f"No result found for task {task_id}") from err

        # Parse frontmatter
        metadata = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                with contextlib.suppress(yaml.YAMLError):
                    metadata = yaml.safe_load(content[3:end]) or {}
                body = content[end + 3 :].strip()

        return {
            "task_id": task_id,
            "metadata": metadata,
            "result": body,
        }

    def _read_task(self, task_id: str) -> dict:
        """Read and parse a task file."""
        path = f"teleport/tasks/{task_id}.md"
        content = self._vault.read(path)  # Raises FileNotFoundError if missing

        metadata = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                with contextlib.suppress(yaml.YAMLError):
                    metadata = yaml.safe_load(content[3:end]) or {}
                body = content[end + 3 :].strip()

        metadata["_body"] = body
        return metadata

    def _write_task(self, task_id: str, metadata: dict, body: str) -> None:
        """Write a task file with YAML frontmatter."""
        # Remove internal fields
        clean_meta = {k: v for k, v in metadata.items() if not k.startswith("_")}

        frontmatter = yaml.dump(clean_meta, default_flow_style=False, sort_keys=False)
        content = f"---\n{frontmatter}---\n{body}"

        self._vault.write(f"teleport/tasks/{task_id}.md", content)
