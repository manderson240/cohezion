"""Vault Memory Bridge — sync session state between Claude instances via vault."""

import contextlib
import logging
import re
import uuid
from datetime import UTC, datetime

import yaml

from .vault_ops import VaultOps


logger = logging.getLogger(__name__)


class VaultMemoryBridge:
    """Bridge between Claude Code memory and Obsidian vault."""

    def __init__(self, vault: VaultOps):
        self._vault = vault

    def push_session_state(
        self,
        branch: str,
        test_status: str,
        phase: str,
        active_tasks: list[str] | None = None,
        last_commit: str = "",
    ) -> str:
        """Push current session state to a daily session note."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        session_id = uuid.uuid4().hex[:8]
        path = f"daily/{date}-session-{session_id}.md"

        content = f"""---
date: {date}
type: session
branch: {branch}
test_status: {test_status}
phase: {phase}
last_commit: {last_commit}
tags: [session, auto-generated]
---
# Session {session_id} — {date}

## Status
- **Branch**: {branch}
- **Tests**: {test_status}
- **Phase**: {phase}
- **Last Commit**: {last_commit or "N/A"}

## Active Tasks
{self._format_task_list(active_tasks)}

## Notes
(Auto-generated session snapshot)
"""
        self._vault.write(path, content)
        logger.info("Pushed session state: %s", path)
        return path

    def push_memory(self, memory_content: str) -> dict:
        """Parse MEMORY.md content and distribute to vault sections."""
        sections = self._parse_memory_sections(memory_content)
        result = {"session_notes": "", "lessons_synced": 0, "todos_updated": False}

        # Sync current state as session note
        if "Current State" in sections:
            path = self.push_session_state(
                branch=self._extract_field(sections["Current State"], "Branch"),
                test_status=self._extract_field(
                    sections["Current State"], "Test suite"
                ),
                phase=self._extract_field(sections["Current State"], "Phase")
                or "unknown",
                last_commit=self._extract_field(
                    sections["Current State"], "Last commit"
                ),
            )
            result["session_notes"] = path

        # Sync lessons to patterns
        if "Lessons" in sections:
            count = self._sync_lessons(sections["Lessons"])
            result["lessons_synced"] = count

        # Sync TODOs
        if "TODO" in sections:
            self._sync_todos(sections["TODO"])
            result["todos_updated"] = True

        return result

    def pull_session_context(self) -> dict:
        """Read latest session notes to build cross-instance context."""
        context = {
            "sessions": [],
            "latest_branch": "",
            "latest_phase": "",
            "latest_test_status": "",
        }

        try:
            files = self._vault.list_dir("daily", recursive=False)
        except FileNotFoundError:
            return context

        # Find session files, sorted by name (date-based)
        session_files = sorted(
            [f for f in files if "session" in f and f.endswith(".md")],
            reverse=True,
        )

        for path in session_files[:5]:  # Last 5 sessions
            try:
                content = self._vault.read(path)
                session = self._parse_session_note(content)
                session["path"] = path
                context["sessions"].append(session)
            except (FileNotFoundError, ValueError):
                continue

        if context["sessions"]:
            latest = context["sessions"][0]
            context["latest_branch"] = latest.get("branch", "")
            context["latest_phase"] = latest.get("phase", "")
            context["latest_test_status"] = latest.get("test_status", "")

        return context

    def _parse_memory_sections(self, content: str) -> dict[str, str]:
        """Split MEMORY.md by ## headings into sections."""
        sections = {}
        current_heading = None
        current_lines = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_heading is not None:
                    sections[current_heading] = "\n".join(current_lines).strip()
                current_heading = line[3:].strip()
                current_lines = []
            elif current_heading is not None:
                current_lines.append(line)

        if current_heading is not None:
            sections[current_heading] = "\n".join(current_lines).strip()

        return sections

    def _sync_lessons(self, lessons_text: str) -> int:
        """Parse lesson bullets and create pattern files for new ones."""
        count = 0
        # Extract bullet points (- **NAME**: description)
        pattern = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.+)", re.MULTILINE)

        existing_patterns = set()
        try:
            files = self._vault.list_dir("patterns", recursive=False)
            existing_patterns = {f.lower() for f in files if f.endswith(".md")}
        except FileNotFoundError:
            pass

        for match in pattern.finditer(lessons_text):
            name = match.group(1).strip()
            description = match.group(2).strip()
            slug = self._slugify(name)
            filename = f"patterns/lesson-{slug}.md"

            if filename.lower() in existing_patterns:
                continue  # Already exists — deduplicate

            date = datetime.now(UTC).strftime("%Y-%m-%d")
            content = f"""---
date: {date}
type: lesson
source: memory-bridge
tags: [lesson, auto-synced]
---
# {name}

{description}
"""
            self._vault.write(filename, content)
            existing_patterns.add(filename.lower())
            count += 1

        return count

    def _sync_todos(self, todos_text: str) -> str:
        """Write/update the project todos file."""
        date = datetime.now(UTC).strftime("%Y-%m-%d")
        content = f"""---
date: {date}
type: todos
source: memory-bridge
tags: [todos, auto-synced]
---
# Cohezion TODOs

_Last synced: {date}_

{todos_text}
"""
        path = "projects/cohezion-todos.md"
        self._vault.write(path, content)
        return path

    def _extract_field(self, text: str, field_name: str) -> str:
        """Extract a field value from markdown text."""
        pattern = re.compile(rf"\*\*{re.escape(field_name)}\*\*:\s*(.+?)(?:\n|$)")
        match = pattern.search(text)
        if match:
            return match.group(1).strip().strip("`")
        # Also try without bold
        pattern2 = re.compile(
            rf"{re.escape(field_name)}:\s*(.+?)(?:\n|$)", re.IGNORECASE
        )
        match2 = pattern2.search(text)
        if match2:
            return match2.group(1).strip().strip("`")
        return ""

    def _format_task_list(self, tasks: list[str] | None) -> str:
        """Format task list as markdown bullets."""
        if not tasks:
            return "- No active tasks recorded"
        return "\n".join(f"- {task}" for task in tasks)

    def _parse_session_note(self, content: str) -> dict:
        """Parse a session note to extract metadata."""
        result = {}
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                with contextlib.suppress(Exception):
                    result = yaml.safe_load(content[3:end]) or {}
        return result

    def _slugify(self, text: str) -> str:
        """Convert text to filename-safe slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text[:60].strip("-")
