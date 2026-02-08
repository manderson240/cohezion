"""Thread-safe file locking for shared resource coordination.

Prevents race conditions when multiple agents/sessions access shared files:
- skill_registry.json (auto_sync from parallel agents)
- capability_usage.json (concurrent increment_usage)
- ~/.gitlab-runner/config.toml (multiple sessions editing)

Uses fcntl.flock() for Unix systems, with fallback timeout for deadlock prevention.
"""

import fcntl
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class FileLockError(Exception):
    """File lock acquisition failed."""


class FileLock:
    """Context manager for atomic file operations with locking.

    Ensures only one process/thread can access a file at a time.
    Uses fcntl.flock() on Unix systems.

    Example:
        ```python
        lock = FileLock('/path/to/skill_registry.json', timeout=10.0)
        with lock:
            data = json.load(open('/path/to/skill_registry.json'))
            data['skill1'] = {'version': 2}
            json.dump(data, open('/path/to/skill_registry.json', 'w'))
        ```
    """

    def __init__(self, filepath: str, timeout: float = 10.0):
        """Initialize file lock.

        Args:
            filepath: Path to file to lock
            timeout: Seconds to wait for lock acquisition
        """
        self.filepath = Path(filepath)
        self.timeout = timeout
        self._lock_file = None
        self._acquired_at = None

    def acquire(self) -> None:
        """Acquire lock on file.

        Raises:
            FileLockError: If lock cannot be acquired within timeout
        """
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        last_error = None

        while time.time() - start_time < self.timeout:
            try:
                self._lock_file = open(self.filepath, "a")
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._acquired_at = time.time()
                logger.debug(
                    "Acquired lock on %s after %.2f seconds",
                    self.filepath,
                    time.time() - start_time,
                )
                return
            except OSError as e:
                last_error = e
                time.sleep(0.1)  # Back off briefly

        raise FileLockError(
            f"Could not acquire lock on {self.filepath} within {self.timeout}s: {last_error}"
        )

    def release(self) -> None:
        """Release lock on file."""
        if self._lock_file:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                self._lock_file = None

                if self._acquired_at:
                    held_time = time.time() - self._acquired_at
                    logger.debug("Released lock on %s (held for %.3f seconds)",
                                self.filepath, held_time)
            except OSError as e:
                logger.warning("Error releasing lock on %s: %s", self.filepath, e)

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


class ConfigManager:
    """Atomic read-modify-write operations on JSON config files.

    Ensures multiple processes can safely update shared configs without
    corruption or lost updates.

    Example:
        ```python
        manager = ConfigManager('/path/to/skill_registry.json')
        def update_skill(data):
            data['skill1']['version'] += 1
            return data
        manager.atomic_update(update_skill)
        ```
    """

    def __init__(self, filepath: str, lock_timeout: float = 10.0):
        """Initialize config manager.

        Args:
            filepath: Path to config file
            lock_timeout: Seconds to wait for lock
        """
        self.filepath = Path(filepath)
        self.lock_timeout = lock_timeout

    @contextmanager
    def _read_with_lock(self) -> Generator[dict, None, None]:
        """Read config file with exclusive lock."""
        import json

        lock = FileLock(str(self.filepath), timeout=self.lock_timeout)
        with lock:
            if self.filepath.exists():
                with open(self.filepath, "r") as f:
                    content = f.read().strip()
                    data = json.loads(content) if content else {}
            else:
                data = {}
            yield data

    @contextmanager
    def _write_with_lock(self) -> Generator[dict, None, None]:
        """Prepare to write config file with exclusive lock."""
        import json

        lock = FileLock(str(self.filepath), timeout=self.lock_timeout)
        with lock:
            if self.filepath.exists():
                with open(self.filepath, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            yield data
            # Write happens after yield, so caller can modify data
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=2)

    def read(self) -> dict:
        """Read config file (non-blocking if already locked elsewhere).

        Returns:
            Dictionary with config contents

        Raises:
            FileLockError: If lock cannot be acquired
        """
        with self._read_with_lock() as data:
            return data

    def write(self, data: dict) -> None:
        """Write config file atomically.

        Args:
            data: Dictionary to write
        """
        import json

        lock = FileLock(str(self.filepath), timeout=self.lock_timeout)
        with lock:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=2)

    def atomic_update(self, update_func, max_retries: int = 3) -> dict:
        """Atomically read, modify, and write config.

        Ensures multiple processes updating the same file don't lose updates.

        Args:
            update_func: Function that takes dict, returns modified dict
            max_retries: Number of retries on lock timeout

        Returns:
            Final written data

        Raises:
            FileLockError: If lock cannot be acquired after retries
        """
        import json
        retries = 0
        last_error = None

        while retries < max_retries:
            try:
                lock = FileLock(str(self.filepath), timeout=self.lock_timeout)
                with lock:
                    # Read
                    if self.filepath.exists():
                        with open(self.filepath, "r") as f:
                            content = f.read().strip()
                            data = json.loads(content) if content else {}
                    else:
                        data = {}

                    # Modify
                    data = update_func(data)

                    # Write
                    self.filepath.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.filepath, "w") as f:
                        json.dump(data, f, indent=2)

                    logger.debug("Atomic update completed: %s", self.filepath)
                    return data
            except FileLockError as e:
                last_error = e
                retries += 1
                if retries < max_retries:
                    wait_time = 0.5 * (2 ** retries)  # Exponential backoff
                    logger.warning(
                        "Lock timeout on %s, retrying in %.1f seconds (%d/%d)",
                        self.filepath,
                        wait_time,
                        retries,
                        max_retries,
                    )
                    time.sleep(wait_time)

        raise FileLockError(
            f"Atomic update failed after {max_retries} retries: {last_error}"
        )


@contextmanager
def safe_file_access(filepath: str, timeout: float = 10.0) -> Generator[None, None, None]:
    """Simple context manager for safe file access.

    Args:
        filepath: Path to file
        timeout: Lock timeout in seconds

    Yields:
        Control when file is locked

    Example:
        ```python
        with safe_file_access('/path/to/file.json'):
            # File is locked, safe to read/write
            data = json.load(open('/path/to/file.json'))
        ```
    """
    lock = FileLock(filepath, timeout=timeout)
    with lock:
        yield
