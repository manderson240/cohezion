"""Unit tests for sheets research daemon components."""

import sqlite3
import tempfile
from pathlib import Path

from mcp_server.sheets_research_daemon import (
    AgentCoordinator,
    DeadLetterQueue,
    WorkQueue,
)


class TestWorkQueue:
    """Test WorkQueue SQLite operations."""

    def test_work_queue_initialization(self):
        """Test work queue creates schema correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            # Verify database exists
            assert Path(db_path).exists()

            # Verify schema
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='work_queue'"
            )
            assert cursor.fetchone() is not None
            conn.close()

    def test_add_rows(self):
        """Test adding rows to work queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            rows = [
                {"row": 100, "link": "https://example.com/1"},
                {"row": 101, "link": "https://example.com/2"},
            ]
            queue.add_rows(rows)

            # Verify rows were added
            pending = queue.get_pending_rows(10)
            assert len(pending) == 2
            assert pending[0]["row"] == 100
            assert pending[0]["link"] == "https://example.com/1"

    def test_mark_in_progress(self):
        """Test marking rows as in progress."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            rows = [{"row": 100, "link": "https://example.com/1"}]
            queue.add_rows(rows)

            queue.mark_in_progress([100])

            # Verify state changed
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT state FROM work_queue WHERE row_number = 100")
            state = cursor.fetchone()[0]
            conn.close()
            assert state == "IN_PROGRESS"

    def test_mark_completed(self):
        """Test marking rows as completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            rows = [{"row": 100, "link": "https://example.com/1"}]
            queue.add_rows(rows)

            queue.mark_in_progress([100])
            queue.mark_completed(100)

            # Verify state changed
            pending = queue.get_pending_rows(10)
            assert len(pending) == 0

    def test_mark_failed_retry_logic(self):
        """Test retry logic: 3 attempts before should_retry = False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            rows = [{"row": 100, "link": "https://example.com/1"}]
            queue.add_rows(rows)

            # First failure
            should_retry, retry_count = queue.mark_failed(100)
            assert should_retry is True
            assert retry_count == 1

            # Second failure
            should_retry, retry_count = queue.mark_failed(100)
            assert should_retry is True
            assert retry_count == 2

            # Third failure
            should_retry, retry_count = queue.mark_failed(100)
            assert should_retry is False
            assert retry_count == 3

    def test_get_stats(self):
        """Test getting work queue statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            queue = WorkQueue(db_path)

            rows = [
                {"row": 100, "link": "https://example.com/1"},
                {"row": 101, "link": "https://example.com/2"},
            ]
            queue.add_rows(rows)

            stats = queue.get_stats()
            assert stats.get("PENDING") == 2


class TestDeadLetterQueue:
    """Test DeadLetterQueue operations."""

    def test_dlq_initialization(self):
        """Test DLQ creates schema correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "dlq.db")
            dlq = DeadLetterQueue(db_path)

            # Verify database exists
            assert Path(db_path).exists()

            # Verify schema
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dead_letter_queue'"
            )
            assert cursor.fetchone() is not None
            conn.close()

    def test_add_to_dlq(self):
        """Test adding entries to DLQ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "dlq.db")
            dlq = DeadLetterQueue(db_path)

            dlq.add(100, "https://example.com/1", "Connection timeout")

            entries = dlq.get_all()
            assert len(entries) == 1
            assert entries[0]["row"] == 100
            assert entries[0]["reason"] == "Connection timeout"

    def test_dlq_increment_failure_count(self):
        """Test failure count increments on duplicate adds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "dlq.db")
            dlq = DeadLetterQueue(db_path)

            dlq.add(100, "https://example.com/1", "Error 1")
            dlq.add(100, "https://example.com/1", "Error 2")

            entries = dlq.get_all()
            assert len(entries) == 1
            assert entries[0]["failure_count"] == 2

    def test_remove_from_dlq(self):
        """Test removing entries from DLQ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "dlq.db")
            dlq = DeadLetterQueue(db_path)

            dlq.add(100, "https://example.com/1", "Timeout")
            dlq.remove(100)

            entries = dlq.get_all()
            assert len(entries) == 0

    def test_get_dlq_size(self):
        """Test getting DLQ size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "dlq.db")
            dlq = DeadLetterQueue(db_path)

            dlq.add(100, "https://example.com/1", "Error")
            dlq.add(101, "https://example.com/2", "Error")

            assert dlq.get_size() == 2


class TestAgentCoordinator:
    """Test agent coordination and JSON extraction."""

    def test_create_task_prompt(self):
        """Test task prompt generation."""
        coordinator = AgentCoordinator()

        rows = [
            {"row": 100, "link": "https://example.com/1"},
            {"row": 101, "link": "https://example.com/2"},
        ]

        prompt = coordinator._create_task_prompt(rows)

        assert "Row 100: https://example.com/1" in prompt
        assert "Row 101: https://example.com/2" in prompt
        assert "```json" in prompt
        assert "Researched" in prompt
        assert "Inaccessible" in prompt

    def test_extract_json_from_output_valid(self):
        """Test extracting JSON from agent output."""
        coordinator = AgentCoordinator()

        # Plain text with JSON code fence (what extract_json_from_output expects)
        output = '```json\n[{"row": 100, "status": "Researched", "abstractions": "Test", "domain": "AI", "integration_point": "Test point"}]\n```'

        results = coordinator.extract_json_from_output(output)

        assert len(results) > 0
        assert results[0]["row"] == 100
        assert results[0]["status"] == "Researched"

    def test_extract_json_invalid_schema(self):
        """Test extracting JSON with invalid schema."""
        coordinator = AgentCoordinator()

        # Missing required fields
        output = """{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "```json\\n[{\\"row\\": 100, \\"status\\": \\"Researched\\"}]\\n```"}}"""

        results = coordinator.extract_json_from_output(output)

        # Should filter out invalid entries
        assert len(results) == 0

    def test_extract_json_no_json_blocks(self):
        """Test extracting from output with no JSON blocks."""
        coordinator = AgentCoordinator()

        output = '{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "No JSON here"}}'

        results = coordinator.extract_json_from_output(output)

        assert len(results) == 0

    def test_extract_json_multiple_blocks(self):
        """Test extracting from multiple JSON blocks (takes largest)."""
        coordinator = AgentCoordinator()

        # Two JSON code fence blocks, larger one has more entries
        output = (
            '```json\n[{"row": 100, "status": "Researched", "abstractions": "Test", "domain": "AI", "integration_point": "Test"}]\n```\n'
            '```json\n[{"row": 101, "status": "Researched", "abstractions": "Test1", "domain": "AI", "integration_point": "Test1"}, '
            '{"row": 102, "status": "Researched", "abstractions": "Test2", "domain": "AI", "integration_point": "Test2"}]\n```'
        )

        results = coordinator.extract_json_from_output(output)

        # Should take the larger block (2 entries)
        assert len(results) == 2
