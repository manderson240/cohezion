"""
Google Keep Task Queue Integration.

Enables async communication:
1. You add tasks to a Google Keep note titled "Cohezion Tasks"
2. I check the note at session start
3. Execute tasks autonomously
4. Send email notification when complete

Uses keep-mcp or gkeepapi for Keep access.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """A task from Keep."""
    task_id: str
    title: str
    status: str  # pending, in_progress, complete
    priority: str  # low, medium, high, critical
    created_at: str
    details: str = ""


@dataclass
class TaskQueue:
    """Queue of tasks from Keep."""
    source: str
    fetched_at: str
    tasks: list[Task]
    
    def pending(self) -> list[Task]:
        return [t for t in self.tasks if t.status == "pending"]
    
    def to_dict(self) -> dict:
        return asdict(self)


class GoogleKeepIntegration:
    """
    Integration with Google Keep for task management.
    
    Setup:
    1. pip install gkeepapi
    2. Create app password at https://myaccount.google.com/apppasswords
    3. Set GOOGLE_EMAIL and GOOGLE_KEEP_TOKEN environment variables
    """
    
    TASK_NOTE_TITLE = "Cohezion Tasks"
    
    def __init__(self):
        self.email = os.getenv("GOOGLE_EMAIL", "")
        self.token = os.getenv("GOOGLE_KEEP_TOKEN", "")
        self._keep = None
        self._available = False
    
    async def initialize(self) -> bool:
        """Initialize Keep connection."""
        if not self.email or not self.token:
            logger.warning(
                "Google Keep not configured. Set GOOGLE_EMAIL and GOOGLE_KEEP_TOKEN. "
                "See: https://github.com/kiwiz/gkeepapi for setup."
            )
            return False
        
        try:
            import gkeepapi
            
            self._keep = gkeepapi.Keep()
            await asyncio.to_thread(
                self._keep.authenticate, self.email, self.token
            )
            self._available = True
            logger.info("Google Keep connected successfully")
            return True
            
        except ImportError:
            logger.warning("gkeepapi not installed. Run: pip install gkeepapi")
        except Exception as e:
            logger.error(f"Keep authentication failed: {e}")
        
        return False
    
    def _find_task_note(self):
        """Find the Cohezion Tasks note."""
        if not self._keep:
            return None
        
        notes = self._keep.find(query=self.TASK_NOTE_TITLE)
        for note in notes:
            if note.title == self.TASK_NOTE_TITLE:
                return note
        return None
    
    def _parse_tasks(self, note) -> list[Task]:
        """Parse tasks from a Keep note."""
        tasks = []
        
        # Handle list notes
        if hasattr(note, 'items'):
            for i, item in enumerate(note.items):
                status = "complete" if item.checked else "pending"
                priority = "high" if "!" in item.text else "medium"
                
                tasks.append(Task(
                    task_id=f"keep_{i}",
                    title=item.text.strip(),
                    status=status,
                    priority=priority,
                    created_at=str(note.timestamps.created),
                ))
        else:
            # Handle text notes - parse checkbox markdown
            lines = note.text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Parse markdown checkboxes
                if line.startswith('- [ ]'):
                    status = "pending"
                    title = line[5:].strip()
                elif line.startswith('- [x]') or line.startswith('- [X]'):
                    status = "complete"
                    title = line[5:].strip()
                else:
                    continue
                
                priority = "high" if "!" in title else "medium"
                
                tasks.append(Task(
                    task_id=f"keep_{i}",
                    title=title,
                    status=status,
                    priority=priority,
                    created_at=datetime.now(UTC).isoformat(),
                ))
        
        return tasks
    
    async def fetch_tasks(self) -> TaskQueue:
        """Fetch tasks from Keep."""
        if not self._available:
            return TaskQueue(
                source="google_keep",
                fetched_at=datetime.now(UTC).isoformat(),
                tasks=[],
            )
        
        try:
            await asyncio.to_thread(self._keep.sync)
            note = self._find_task_note()
            
            if note:
                tasks = self._parse_tasks(note)
                logger.info(f"Fetched {len(tasks)} tasks from Keep")
            else:
                tasks = []
                logger.info("No Cohezion Tasks note found in Keep")
            
            return TaskQueue(
                source="google_keep",
                fetched_at=datetime.now(UTC).isoformat(),
                tasks=tasks,
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {e}")
            return TaskQueue(
                source="google_keep",
                fetched_at=datetime.now(UTC).isoformat(),
                tasks=[],
            )
    
    async def mark_complete(self, task: Task):
        """Mark a task as complete in Keep."""
        if not self._available:
            return
        
        try:
            note = self._find_task_note()
            if note and hasattr(note, 'items'):
                for item in note.items:
                    if item.text.strip() == task.title:
                        item.checked = True
                        break
                await asyncio.to_thread(self._keep.sync)
                logger.info(f"Marked complete: {task.title}")
        except Exception as e:
            logger.error(f"Failed to mark complete: {e}")
    
    async def add_result(self, task: Task, result: str):
        """Add completion result to the note."""
        if not self._available:
            return
        
        try:
            note = self._find_task_note()
            if note:
                # Add result as a comment
                note.text += f"\n\n✅ {task.title}\nCompleted: {datetime.now(UTC).isoformat()}\n{result[:200]}"
                await asyncio.to_thread(self._keep.sync)
        except Exception as e:
            logger.error(f"Failed to add result: {e}")
    
    @property
    def is_available(self) -> bool:
        return self._available


class LocalTaskQueue:
    """
    Fallback: Local file-based task queue.
    
    Use when Google Keep is not configured.
    Tasks are stored in .cohezion/tasks.md
    """
    
    def __init__(self, path: Path | None = None):
        self.path = path or Path(".cohezion/tasks.md")
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def _ensure_file(self):
        """Create task file if it doesn't exist."""
        if not self.path.exists():
            self.path.write_text("""# Cohezion Task Queue

Add tasks here in checkbox format:
- [ ] Example task
- [ ] Another task !high priority

Completed tasks:
- [x] Previously done task
""")
    
    def fetch_tasks(self) -> TaskQueue:
        """Fetch tasks from local file."""
        self._ensure_file()
        
        content = self.path.read_text()
        tasks = []
        
        for i, line in enumerate(content.split('\n')):
            line = line.strip()
            if line.startswith('- [ ]'):
                title = line[5:].strip()
                priority = "high" if "!" in title else "medium"
                tasks.append(Task(
                    task_id=f"local_{i}",
                    title=title,
                    status="pending",
                    priority=priority,
                    created_at=datetime.now(UTC).isoformat(),
                ))
            elif line.startswith('- [x]') or line.startswith('- [X]'):
                title = line[5:].strip()
                tasks.append(Task(
                    task_id=f"local_{i}",
                    title=title,
                    status="complete",
                    priority="medium",
                    created_at=datetime.now(UTC).isoformat(),
                ))
        
        return TaskQueue(
            source="local_file",
            fetched_at=datetime.now(UTC).isoformat(),
            tasks=tasks,
        )
    
    def mark_complete(self, task: Task):
        """Mark task as complete in local file."""
        content = self.path.read_text()
        updated = content.replace(
            f"- [ ] {task.title}",
            f"- [x] {task.title} ✅"
        )
        self.path.write_text(updated)


async def get_task_queue() -> tuple[TaskQueue, Any]:
    """Get task queue from Keep or local file."""
    # Try Google Keep first
    keep = GoogleKeepIntegration()
    if await keep.initialize():
        queue = await keep.fetch_tasks()
        return queue, keep
    
    # Fallback to local
    local = LocalTaskQueue()
    queue = local.fetch_tasks()
    return queue, local


async def check_and_report():
    """Check task queue and report status."""
    queue, source = await get_task_queue()
    
    print(f"\n=== Task Queue ({queue.source}) ===")
    print(f"Fetched: {queue.fetched_at}")
    print(f"Total tasks: {len(queue.tasks)}")
    print(f"Pending: {len(queue.pending())}")
    
    for task in queue.pending():
        print(f"  [{task.priority}] {task.title}")
    
    return queue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_and_report())
