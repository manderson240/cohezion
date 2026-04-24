"""Tests for thread-safe file locking."""

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from cohezion.concurrency.file_lock import ConfigManager, FileLock, FileLockError


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("{}")
        filepath = f.name
    yield filepath
    Path(filepath).unlink(missing_ok=True)


def test_file_lock_acquire_release(temp_file):
    """Test lock acquire and release."""
    lock = FileLock(temp_file, timeout=5.0)

    lock.acquire()
    assert lock._lock_file is not None
    assert lock._acquired_at is not None

    lock.release()
    assert lock._lock_file is None


def test_file_lock_context_manager(temp_file):
    """Test lock as context manager."""
    lock = FileLock(temp_file, timeout=5.0)

    with lock:
        assert lock._lock_file is not None

    assert lock._lock_file is None


def test_file_lock_creates_parent_directories(temp_file):
    """Test that lock creates parent directories if needed."""
    nested_path = Path(temp_file).parent / "subdir" / "file.lock"

    lock = FileLock(str(nested_path), timeout=5.0)

    with lock:
        assert nested_path.parent.exists()

    nested_path.unlink(missing_ok=True)
    nested_path.parent.rmdir()


def test_file_lock_timeout(temp_file):
    """Test lock timeout behavior."""
    lock1 = FileLock(temp_file, timeout=0.5)
    lock1.acquire()

    # Try to acquire same lock with short timeout
    lock2 = FileLock(temp_file, timeout=0.1)

    with pytest.raises(FileLockError):
        lock2.acquire()

    lock1.release()


def test_config_manager_read(temp_file):
    """Test reading config file."""
    data = {"key1": "value1", "key2": {"nested": "value2"}}
    with open(temp_file, "w") as f:
        json.dump(data, f)

    manager = ConfigManager(temp_file)
    read_data = manager.read()

    assert read_data == data


def test_config_manager_write(temp_file):
    """Test writing config file."""
    data = {"key1": "new_value"}

    manager = ConfigManager(temp_file)
    manager.write(data)

    with open(temp_file) as f:
        written_data = json.load(f)

    assert written_data == data


def test_config_manager_atomic_update(temp_file):
    """Test atomic read-modify-write."""
    initial_data = {"counter": 0}
    with open(temp_file, "w") as f:
        json.dump(initial_data, f)

    manager = ConfigManager(temp_file)

    def increment_counter(data):
        data["counter"] += 1
        return data

    result = manager.atomic_update(increment_counter)

    assert result["counter"] == 1

    # Verify it was written
    with open(temp_file) as f:
        written_data = json.load(f)
    assert written_data["counter"] == 1


def test_config_manager_atomic_update_concurrent(temp_file):
    """Test concurrent atomic updates don't lose data."""
    initial_data = {"counter": 0}
    with open(temp_file, "w") as f:
        json.dump(initial_data, f)

    manager = ConfigManager(temp_file, lock_timeout=30.0)
    results = []

    def increment_counter():
        def update_fn(data):
            data["counter"] += 1
            # justify: real-thread contention test for atomic_update; sleep
            # widens the critical section so concurrent threads must serialize
            time.sleep(0.01)
            return data

        result = manager.atomic_update(update_fn)
        results.append(result["counter"])

    # Launch 5 concurrent increment threads
    threads = [threading.Thread(target=increment_counter) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Final value should be 5 (not 1 if race condition exists)
    with open(temp_file) as f:
        final_data = json.load(f)

    assert final_data["counter"] == 5
    # All increments should have happened in sequence
    assert sorted(results) == [1, 2, 3, 4, 5]


def test_config_manager_missing_file(temp_file):
    """Test operations on non-existent file."""
    non_existent = str(Path(temp_file).parent / "nonexistent.json")

    manager = ConfigManager(non_existent)

    # Read should return empty dict
    data = manager.read()
    assert data == {}

    # Write should create file
    manager.write({"key": "value"})
    assert Path(non_existent).exists()

    Path(non_existent).unlink()


def test_config_manager_atomic_update_empty_file(temp_file):
    """Test atomic update on empty/non-existent file."""
    non_existent = str(Path(temp_file).parent / "empty.json")

    manager = ConfigManager(non_existent)

    def create_data(data):
        data["created"] = True
        return data

    result = manager.atomic_update(create_data)
    assert result["created"] is True

    Path(non_existent).unlink()


def test_file_lock_serial_access(temp_file):
    """Test that locks enforce serial access."""
    access_order = []

    def access_with_lock(lock_id):
        lock = FileLock(temp_file, timeout=5.0)
        with lock:
            access_order.append(("enter", lock_id))
            # justify: real-thread serial-access test; sleep ensures other
            # threads attempt entry while this one holds the lock
            time.sleep(0.1)
            access_order.append(("exit", lock_id))

    threads = [threading.Thread(target=access_with_lock, args=(i,)) for i in range(3)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Verify no overlapping access (no two enters without an exit between)
    depth = 0
    for event, _lock_id in access_order:
        if event == "enter":
            depth += 1
            assert depth == 1, "Lock not exclusive!"
        else:
            depth -= 1


def test_file_lock_held_duration(temp_file):
    """Test lock held time tracking."""
    lock = FileLock(temp_file, timeout=5.0)

    lock.acquire()
    acquired_at = lock._acquired_at
    assert acquired_at is not None

    # justify: tests real wall-clock duration tracking on FileLock;
    # mocking time.time would invalidate the test's intent
    time.sleep(0.1)
    lock.release()

    # Verify lock was held for at least 100ms
    held_duration = time.time() - acquired_at
    assert held_duration >= 0.1


def test_config_manager_retry_logic(temp_file):
    """Test retry logic in atomic update."""
    data = {"counter": 0}
    with open(temp_file, "w") as f:
        json.dump(data, f)

    manager = ConfigManager(temp_file, lock_timeout=0.1)

    def update_fn(data):
        data["counter"] += 1
        return data

    # Hold lock in background thread
    lock = FileLock(temp_file, timeout=30.0)
    lock.acquire()

    # This should retry and eventually succeed
    try:
        manager.atomic_update(update_fn, max_retries=3)
        raise AssertionError("Should have failed due to held lock")
    except FileLockError:
        pass  # Expected
    finally:
        lock.release()


def test_safe_file_access_context_manager(temp_file):
    """Test safe_file_access context manager."""
    from cohezion.concurrency.file_lock import safe_file_access

    with safe_file_access(temp_file, timeout=5.0), open(temp_file) as f:
        # File should be locked and accessible
        data = json.load(f)
        assert isinstance(data, dict)
