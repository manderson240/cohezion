"""
Batch Manager for Cohezion.
Consolidates multiple menial tasks into high-density local model prompts.
"""

from typing import Any


class BatchManager:
    def __init__(self, max_batch_size: int = 5):
        self.max_batch_size = max_batch_size
        self.queue: list[dict[str, Any]] = []

    def enqueue(self, task_id: str, query: str, context: str | None = None):
        """Add a task to the consolidation queue."""
        self.queue.append({"task_id": task_id, "query": query, "context": context})

    def get_batch(self) -> dict[str, Any] | None:
        """Return a consolidated batch if queue is ready."""
        if not self.queue:
            return None

        # Take up to max_batch_size
        batch_tasks = self.queue[: self.max_batch_size]
        self.queue = self.queue[self.max_batch_size :]

        return self._consolidate(batch_tasks)

    def _consolidate(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Consolidate multiple tasks into a single high-density prompt."""
        header = f"BATCH PROCESSING: {len(tasks)} Menial Tasks Found."
        instruction = (
            "You are a local processing unit. Respond to EACH task below in sequence. "
            "Use the following format for each response: [TASK_ID: <id>] RESPONSE: <text>\n"
        )

        body = ""
        for task in tasks:
            body += f"\n--- TASK_ID: {task['task_id']} ---\n"
            if task["context"]:
                body += f"CONTEXT: {task['context']}\n"
            body += f"QUERY: {task['query']}\n"

        final_prompt = f"{header}\n\n{instruction}\n{body}"

        return {
            "prompt": final_prompt,
            "task_ids": [t["task_id"] for t in tasks],
            "count": len(tasks),
        }

    def parse_batch_response(self, response: str) -> dict[str, str]:
        """Parse the consolidated response back into individual results."""
        results = {}
        # Simple regex-less parsing based on task markers
        import re

        pattern = r"\[TASK_ID: (.*?)\] RESPONSE: (.*?)(?=\[TASK_ID:|$)"
        matches = re.finditer(pattern, response, re.DOTALL)

        for match in matches:
            task_id = match.group(1).strip()
            results[task_id] = match.group(2).strip()

        return results


if __name__ == "__main__":
    manager = BatchManager()
    manager.enqueue("T1", "Add docstring to this function", "def hello(): pass")
    manager.enqueue("T2", "Summarize this log", "ERROR: Connection lost at 12:00")

    batch = manager.get_batch()
    print("--- CONSOLIDATED PROMPT ---")
    print(batch["prompt"])
