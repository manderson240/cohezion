"""
Race Condition Prevention Tests

Verifies that file locking prevents Lost Update anomalies when
multiple concurrent agents modify the same file.

Tests:
- Basic file locking (acquire/release)
- Concurrent writes (multiple readers/writers)
- Atomic operations (read-modify-write)
- Timeout handling (deadlock prevention)
- Backoff and retry logic
"""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from cohezion.security.file_lock_context import (
    FileLock,
    FileLockError,
    atomic_file_modify,
    atomic_file_read,
    atomic_file_write,
    locked_file_operation,
)
import contextlib


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("Initial content")
        temp_path = f.name

    yield temp_path

    # Cleanup
    with contextlib.suppress(FileNotFoundError):
        Path(temp_path).unlink()


class TestFileLock:
    """Test basic file locking functionality."""

    def test_acquire_and_release(self, temp_file):
        """Test acquiring and releasing a lock."""
        lock = FileLock(temp_file, timeout=1.0)

        lock.acquire()
        assert lock._acquired is True

        lock.release()
        assert lock._acquired is False

    def test_context_manager(self, temp_file):
        """Test lock as context manager."""
        with FileLock(temp_file) as lock:
            assert lock._acquired is True

        assert lock._acquired is False

    def test_lock_timeout(self, temp_file):
        """Test lock timeout when already locked."""
        lock1 = FileLock(temp_file, timeout=0.5)
        lock2 = FileLock(temp_file, timeout=0.5)

        lock1.acquire()

        # Second lock should timeout
        with pytest.raises(FileLockError):
            lock2.acquire()

        lock1.release()

    def test_lock_retry(self, temp_file):
        """Test lock retry logic."""
        lock1 = FileLock(temp_file, timeout=2.0, max_retries=2)
        lock2 = FileLock(temp_file, timeout=2.0, max_retries=2)

        lock1.acquire()

        # Release in another thread after delay
        def release_delayed():
            time.sleep(0.3)
            lock1.release()

        thread = threading.Thread(target=release_delayed)
        thread.start()

        # Lock2 should eventually acquire
        lock2.acquire()
        assert lock2._acquired is True

        lock2.release()
        thread.join()


class TestLockedFileOperation:
    """Test locked_file_operation context manager."""

    def test_read_with_lock(self, temp_file):
        """Test reading file with lock."""
        Path(temp_file).write_text("Test content")

        with locked_file_operation(temp_file) as lock:
            content = Path(lock.filepath).read_text()
            assert content == "Test content"

    def test_write_with_lock(self, temp_file):
        """Test writing file with lock."""
        with locked_file_operation(temp_file) as lock:
            Path(lock.filepath).write_text("New content")

        assert Path(temp_file).read_text() == "New content"

    def test_atomic_modification(self, temp_file):
        """Test atomic read-modify-write with lock."""
        Path(temp_file).write_text("Initial")

        with locked_file_operation(temp_file) as lock:
            content = Path(lock.filepath).read_text()
            new_content = content + " modified"
            Path(lock.filepath).write_text(new_content)

        assert Path(temp_file).read_text() == "Initial modified"


class TestAtomicOperations:
    """Test atomic file operations."""

    def test_atomic_write(self, temp_file):
        """Test atomic file write."""
        atomic_file_write(temp_file, "Atomic content")
        assert Path(temp_file).read_text() == "Atomic content"

    def test_atomic_read(self, temp_file):
        """Test atomic file read."""
        Path(temp_file).write_text("Read content")
        content = atomic_file_read(temp_file)
        assert content == "Read content"

    def test_atomic_modify(self, temp_file):
        """Test atomic file modification."""
        Path(temp_file).write_text("Original")

        def append_text(content):
            return content + "\nModified"

        atomic_file_modify(temp_file, append_text)
        assert Path(temp_file).read_text() == "Original\nModified"

    def test_atomic_write_nonexistent_file(self):
        """Test atomic write to nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "new_file.md"

            atomic_file_write(str(filepath), "New file content")

            assert filepath.read_text() == "New file content"


class TestConcurrencyPrevention:
    """Test prevention of Lost Update anomaly."""

    def test_serialized_modifications(self, temp_file):
        """Test that locks serialize modifications."""
        Path(temp_file).write_text("Counter: 0")

        def increment():
            for _ in range(5):
                with locked_file_operation(temp_file) as lock:
                    content = Path(lock.filepath).read_text()
                    count = int(content.split(": ")[1])
                    new_content = f"Counter: {count + 1}"
                    Path(lock.filepath).write_text(new_content)
                    time.sleep(0.01)  # Simulate work

        # Run multiple threads
        threads = [threading.Thread(target=increment) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final count should be 15 (3 threads × 5 increments)
        final = Path(temp_file).read_text()
        assert final == "Counter: 15"

    def test_concurrent_readers_exclusive_writers(self, temp_file):
        """Test exclusive write access prevents data corruption."""
        Path(temp_file).write_text("0")

        results = []

        def writer(value):
            time.sleep(0.01)  # Stagger starts
            with locked_file_operation(temp_file):
                # Read
                content = Path(temp_file).read_text()
                old_val = int(content)

                # Simulate work
                time.sleep(0.05)

                # Write
                Path(temp_file).write_text(str(value))
                results.append((old_val, value))

        # Start two writers
        t1 = threading.Thread(target=writer, args=(1,))
        t2 = threading.Thread(target=writer, args=(2,))

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Final value should be one of the writers (not corrupted)
        final = int(Path(temp_file).read_text())
        assert final in [1, 2]

    def test_lost_update_scenario_prevented(self, temp_file):
        """
        Test prevention of classic Lost Update scenario:
        Agent A: read (value=5)
        Agent B: read (value=5)
        Agent A: write (value=6)
        Agent B: write (value=7)  <- B's write lost A's!

        With locking, this cannot happen.
        """
        Path(temp_file).write_text("5")

        results = {"a": None, "b": None}

        def agent_a():
            with locked_file_operation(temp_file):
                # Lock held - B cannot start
                val = int(Path(temp_file).read_text())
                time.sleep(0.1)  # Simulate processing
                Path(temp_file).write_text(str(val + 1))
                results["a"] = val + 1

        def agent_b():
            time.sleep(0.02)  # Ensure A locks first
            with locked_file_operation(temp_file):
                val = int(Path(temp_file).read_text())
                time.sleep(0.1)  # Simulate processing
                Path(temp_file).write_text(str(val + 2))
                results["b"] = val + 2

        ta = threading.Thread(target=agent_a)
        tb = threading.Thread(target=agent_b)

        ta.start()
        tb.start()

        ta.join()
        tb.join()

        # Both writes should be preserved due to serialization
        final = int(Path(temp_file).read_text())

        # Expected: A writes 6, then B reads 6 and writes 8
        assert final == 8
        assert results["a"] == 6
        assert results["b"] == 8


class TestErrorHandling:
    """Test error handling in file operations."""

    def test_lock_on_nonexistent_file(self):
        """Test locking nonexistent file (should create it)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "new.md"

            with locked_file_operation(str(filepath)):
                filepath.write_text("Content")

            assert filepath.exists()

    def test_atomic_read_nonexistent(self):
        """Test atomic read on nonexistent file."""
        with pytest.raises((FileNotFoundError, FileLockError)):
            atomic_file_read("/nonexistent/path/file.md")

    def test_atomic_modify_nonexistent(self):
        """Test atomic modify on nonexistent file."""
        with pytest.raises((FileNotFoundError, FileLockError)):
            atomic_file_modify("/nonexistent/path/file.md", lambda x: x)

    def test_lock_cleanup_on_exception(self, temp_file):
        """Test that lock is released even if operation fails."""
        lock1 = FileLock(temp_file)

        try:
            with locked_file_operation(temp_file):
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Lock should be released, so this should work
        lock1.acquire()
        lock1.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
