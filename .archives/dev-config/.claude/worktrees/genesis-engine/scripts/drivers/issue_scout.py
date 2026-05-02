#!/usr/bin/env python3
"""
Issue Scout (Swarm Evolution Protocol)
=====================================
Background daemon that scans codebase for actionable tasks (TODOs, FIXMEs)
and populates the 'swarm_tasks' table in SurrealDB.
"""

import asyncio
import hashlib
import logging
import os
import re
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [SCOUT] - %(message)s")
logger = logging.getLogger("IssueScout")


class IssueScout:
    def __init__(self, root_dir: str = "."):
        self.root = Path(root_dir)
        self.db = SurrealClient()
        self.excludes = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "node_modules",
            ".agent",
            "brain",
        }

        self.patterns = {
            "TODO": re.compile(r"(TODO|FIXME|HACK|XXX):\s*(.*)", re.IGNORECASE),
            "NEXT_STEP": re.compile(
                r"(?:##|\*\*|[\-\*])\s*(?:Proposed )?Next Steps?:?\s*(.*)",
                re.IGNORECASE,
            ),
        }

    async def start(self):
        logger.info("🦅 Scout deployed. Scanning sector...")
        logger.info(f"DEBUG: DB Type: {type(self.db)}")

        await self.db.connect()

        while True:
            try:
                tasks = self.scan()
                git_task = await self.check_git_health()
                if git_task:
                    tasks.append(git_task)

                logger.info(f"🔍 Found {len(tasks)} potential tasks (including system health).")
                await self.sync_tasks(tasks)
            except Exception as e:
                logger.error(f"Scout encountered turbulence: {e}")

            await asyncio.sleep(600)  # Scan every 10 minutes

    async def check_git_health(self):
        """Check for repo bloat."""
        try:
            proc = await asyncio.create_subprocess_shell(
                "git status --porcelain | wc -l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            count = int(stdout.decode().strip())

            if count > 100:
                logger.warning(f"🚨 Repository Bloat Detected: {count} uncommitted changes.")
                return {
                    "id": "task_repo_cleanup",
                    "type": "maintenance",
                    "context": "repository",
                    "description": f"Clean up {count} uncommitted files (bloat detected).",
                    "status": "pending",
                    "source_file": "SYSTEM",
                    "line_number": 0,
                }
        except Exception as e:
            logger.error(f"Git check failed: {e}")
        return None

    def scan(self):
        found = []
        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.excludes]

            for file in files:
                if not file.endswith((".py", ".md", ".ts", ".tsx")):
                    continue

                path = Path(root) / file
                try:
                    content = path.read_text(errors="ignore")
                    for i, line in enumerate(content.splitlines()):
                        line = line.strip()
                        if not line:
                            continue

                        for _label, pattern in self.patterns.items():
                            match = pattern.search(line)
                            if match:
                                desc = match.group(2).strip()
                                if len(desc) < 3:
                                    continue

                                task_id = hashlib.sha256(f"{path}:{i}:{desc}".encode()).hexdigest()
                                found.append(
                                    {
                                        "id": task_id,
                                        "type": "refactor" if "FIXME" in line else "enhancement",
                                        "context": f"{path}:{i + 1}",
                                        "description": desc,
                                        "status": "pending",
                                        "source_file": str(path),
                                        "line_number": i + 1,
                                    }
                                )
                except Exception:
                    pass
        return found

    async def sync_tasks(self, tasks):
        count = 0
        for task in tasks:
            # Upsert into SurrealDB
            # We use a custom query to avoid overwriting completed tasks
            try:
                # Check if exists
                existing = await self.db.query(f"SELECT * FROM swarm_tasks WHERE id = '{task['id']}'")
                if not existing:
                    await self.db.create("swarm_tasks", task)
                    count += 1
            except Exception as e:
                logger.error(f"Failed to sync task {task['id']}: {e}")

        if count > 0:
            logger.info(f"✅ Registered {count} NEW tasks in the Swarm Marketplace.")


async def main():
    scout = IssueScout()
    await scout.start()


if __name__ == "__main__":
    asyncio.run(main())
