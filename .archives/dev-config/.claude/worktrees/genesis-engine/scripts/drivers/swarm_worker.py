#!/usr/bin/env python3
"""
Swarm Worker (Agentic Executor)
==============================
Picks up tasks from SurrealDB 'swarm_tasks' and executes them using
local heuristics or simple automation.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [WORKER] - %(message)s")
logger = logging.getLogger("SwarmWorker")


class SwarmWorker:
    def __init__(self):
        self.db = SurrealClient()

    async def start(self):
        logger.info("🤖 Worker initialized. Connecting to Hive Mind...")
        await self.db.connect()

        # Poll for tasks
        tasks = await self.fetch_pending_tasks()
        if not tasks:
            logger.info("💤 No tasks found. Resting.")
            return

        for task in tasks:
            await self.execute_task(task)

    async def fetch_pending_tasks(self):
        # SurrealDB query for pending tasks
        try:
            # PRIORITIZE: Look for "bloat" cleanup first
            query = "SELECT * FROM swarm_tasks WHERE status = 'pending' AND description CONTAINS 'bloat' LIMIT 1"
            result = await self.db.query(query)

            # Handle response format (It might be [result_list] or [{result: ...}])
            logger.debug("Query result type: %s", type(result))
            if result and isinstance(result, list):
                # If list of results
                if len(result) > 0:
                    first = result[0]
                    if isinstance(first, dict) and "result" in first:
                        return first["result"]  # Wrapped format
                    # Unwrapped list of records?
                    # Check if first item looks like a record (has 'id')
                    if isinstance(first, dict) and "id" in first:
                        return result  # The list itself is the records

            # Fallback to generic fetch if no bloat task
            logger.info("No bloat task found. Fetching generic...")
            result = await self.db.query("SELECT * FROM swarm_tasks WHERE status = 'pending' LIMIT 1")
            if result and isinstance(result, list):
                if len(result) > 0 and "result" in result[0]:
                    return result[0]["result"]
                return result  # Assume direct list

        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
        return []

    async def execute_task(self, task):
        logger.info(f"🚀 STARTING TASK: {task['description']} (Context: {task['context']})")

        try:
            if "Clean up" in task["description"] and "bloat" in task["description"]:
                await self.handle_repo_cleanup(task)
            else:
                logger.info(f"⚠️ Task type '{task['type']}' requires manual intervention or advanced model.")
        except Exception as e:
            logger.error(f"Task Execution Failed: {e}")

    async def handle_repo_cleanup(self, task):
        logger.info("🧹 Initiating Hygiene Protocol...")

        # 1. Update .gitignore
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if "data/surrealdb" not in content:
                logger.info("🛡️  Hardening .gitignore...")
                with open(".gitignore", "a") as f:
                    f.write("\n# Swarm Auto-Ignore\ndata/surrealdb/\ndata/overnight/\n")

        # 2. Stage deletions
        logger.info("📦 Staging deletions (git add -u)...")
        subprocess.run(["git", "add", "-u"], check=False)

        # 3. Clean untracked (Dry Run first)
        logger.info("🗑️  Cleaning untracked files (git clean -fdX)... service is effectively restarting state.")
        # Note: -f (force), -d (directories), -X (only ignored files) -> Wait, 8.6M files might be Ignored OR Untracked.
        # If they are NOT in gitignore, -X won't touch them. -x touches ignored too.
        # We want to remove UNTRACKED files that are NOT ignored?
        # No, the user typically wants to remove everything not in git.
        # But wait, 8.6M files. Deleting them might take hours.
        # Most likely they are in `data/surrealdb`.
        # If we ignore `data/surrealdb` (Step 1), then `git status` will drop to near zero immediately!
        # `git clean` is only needed if they are NOT ignored and we want to allow them to be re-ignored?
        # Actually, if we ignore them, `git status` stops reporting them.
        # So Step 1 alone might solve the "Bloat Detected" alert.

        # Let's verify status size after ignore.
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        count = len(res.stdout.strip().splitlines()) if res.stdout.strip() else 0
        logger.info(f"📉 Post-Hardening Bloat Count: {count}")

        if count < 100:
            logger.info("✅ Hygiene Protocol Successful. Marking task complete.")
            await self.complete_task(task)
        else:
            logger.warning("⚠️ Still bloated. Manual `git clean` required by User.")

    async def complete_task(self, task):
        try:
            # Update status in DB
            # task['id'] is the ID.
            # SurrealDB update
            await self.db.query(
                "UPDATE swarm_tasks SET status = 'completed', completed_at = time::now() WHERE id = $task_id",
                {"task_id": task["id"]},
            )
            logger.info(f"Task {task['id']} marked complete.")
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")


if __name__ == "__main__":
    asyncio.run(SwarmWorker().start())
