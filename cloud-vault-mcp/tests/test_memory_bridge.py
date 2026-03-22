"""Tests for VaultMemoryBridge."""

import pytest

from mcp_server.memory_bridge import VaultMemoryBridge
from mcp_server.vault_ops import VaultOps


@pytest.fixture
def vault(tmp_path):
    """Create a temporary vault with subdirectories."""
    (tmp_path / "daily").mkdir()
    (tmp_path / "patterns").mkdir()
    (tmp_path / "projects").mkdir()
    return VaultOps(str(tmp_path))


@pytest.fixture
def bridge(vault):
    return VaultMemoryBridge(vault)


class TestPushSessionState:
    def test_push_session_state(self, bridge, vault):
        path = bridge.push_session_state(
            branch="main", test_status="24/24", phase="Phase 6"
        )
        assert path.startswith("daily/")
        assert path.endswith(".md")
        content = vault.read(path)
        assert "main" in content
        assert "24/24" in content
        assert "Phase 6" in content

    def test_push_session_state_with_tasks(self, bridge, vault):
        path = bridge.push_session_state(
            branch="dev",
            test_status="10/10",
            phase="Phase 1",
            active_tasks=["Fix tests", "Update docs"],
        )
        content = vault.read(path)
        assert "- Fix tests" in content
        assert "- Update docs" in content

    def test_push_session_state_no_tasks(self, bridge, vault):
        path = bridge.push_session_state(branch="dev", test_status="ok", phase="test")
        content = vault.read(path)
        assert "No active tasks recorded" in content


class TestPushMemory:
    SAMPLE_MEMORY = """# Project Memory

## Current State
- **Branch**: `feature/phase-6`
- **Test suite**: 24/24 passing
- **Last commit**: `abc1234` some commit

## Lessons
- **CRITICAL**: Always extract knowledge first
- **SURREALDB**: SDK returns flat list

## TODO
- Fix the tests
- Update documentation
"""

    def test_push_memory_full(self, bridge, vault):
        result = bridge.push_memory(self.SAMPLE_MEMORY)
        assert result["session_notes"].startswith("daily/")
        assert result["lessons_synced"] == 2
        assert result["todos_updated"] is True

    def test_push_memory_lessons_only(self, bridge):
        content = """## Lessons
- **HOOK FILE REVERT**: PostToolUse ruff hook can revert files
- **BATCH CACHE**: Two-phase approach works best
"""
        result = bridge.push_memory(content)
        assert result["lessons_synced"] == 2
        assert result["session_notes"] == ""
        assert result["todos_updated"] is False

    def test_push_memory_todos(self, bridge, vault):
        content = """## TODO
- **VLIW FIX**: Revert N_CORES
- **COMPOUND LIVE CYCLE**: Fix SurrealDB auth
"""
        result = bridge.push_memory(content)
        assert result["todos_updated"] is True
        todos = vault.read("projects/cohezion-todos.md")
        assert "VLIW FIX" in todos
        assert "COMPOUND LIVE CYCLE" in todos


class TestPullSessionContext:
    def test_pull_session_context_empty(self, bridge):
        context = bridge.pull_session_context()
        assert context["sessions"] == []
        assert context["latest_branch"] == ""

    def test_pull_session_context(self, bridge, vault):
        # Push two sessions
        bridge.push_session_state(
            branch="old-branch", test_status="10/10", phase="Phase 1"
        )
        bridge.push_session_state(
            branch="new-branch", test_status="24/24", phase="Phase 6"
        )

        context = bridge.pull_session_context()
        assert len(context["sessions"]) == 2
        # Latest session should be first (reverse sorted)
        assert context["latest_branch"] in ("old-branch", "new-branch")
        assert context["latest_test_status"] in ("10/10", "24/24")


class TestLessonDeduplication:
    def test_lesson_deduplication(self, bridge):
        content = """## Lessons
- **CRITICAL**: Always extract knowledge first
- **SURREALDB**: SDK returns flat list
"""
        result1 = bridge.push_memory(content)
        assert result1["lessons_synced"] == 2

        # Push same content again — should not create duplicates
        result2 = bridge.push_memory(content)
        assert result2["lessons_synced"] == 0


class TestInternalMethods:
    def test_parse_memory_sections(self, bridge):
        content = """## Section A
Content A line 1
Content A line 2

## Section B
Content B
"""
        sections = bridge._parse_memory_sections(content)
        assert "Section A" in sections
        assert "Section B" in sections
        assert "Content A line 1" in sections["Section A"]
        assert "Content B" in sections["Section B"]

    def test_extract_field(self, bridge):
        text = "- **Branch**: `feature/test`\n- **Tests**: 24/24 passing"
        assert bridge._extract_field(text, "Branch") == "feature/test"
        assert bridge._extract_field(text, "Tests") == "24/24 passing"

    def test_extract_field_missing(self, bridge):
        assert bridge._extract_field("no fields here", "Missing") == ""

    def test_slugify(self, bridge):
        assert bridge._slugify("HOOK FILE REVERT") == "hook-file-revert"
        assert bridge._slugify("CI SCOPE DISCIPLINE") == "ci-scope-discipline"
        assert bridge._slugify("a/b/c") == "abc"
