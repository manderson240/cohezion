"""
File Locking Context Manager for Atomic File Operations

Provides safe concurrent access to files with exclusive locking,
preventing Lost Update anomalies when multiple agents edit the same file.

Implementation:
- fcntl-based file locking on Unix/Linux
- Timeout protection against deadlocks
- Automatic lock cleanup
- Retry logic with exponential backoff
"""

import fcntl
import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


logger = logging.getLogger(__name__)


class FileLockError(IOError):
    """Raised when file locking fails."""

    pass


class FileLock:
    """Exclusive file lock using fcntl."""

    def __init__(self, filepath: str, timeout: float = 5.0, max_retries: int = 3):
        """
        Initialize file lock.

        Args:
            filepath: Path to file to lock
            timeout: How long to wait for lock (seconds)
            max_retries: Number of times to retry if lock fails
        """
        self.filepath = Path(filepath)
        self.timeout = timeout
        self.max_retries = max_retries
        self._lockfile = None
        self._acquired = False

    def __enter__(self):
        """Acquire lock when entering context."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock when exiting context."""
        self.release()
        return False

    def acquire(self) -> None:
        """
        Acquire exclusive lock on file.

        Raises:
            FileLockError: If lock cannot be acquired after retries
        """
        for attempt in range(self.max_retries):
            try:
                # Open lockfile (create if needed)
                self._lockfile = open(self.filepath, "a+", encoding="utf-8")  # noqa: SIM115

                # Try to acquire exclusive lock with timeout
                start_time = time.time()
                while True:
                    try:
                        fcntl.flock(
                            self._lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                        )
                        self._acquired = True
                        logger.debug(
                            f"Acquired lock on {self.filepath} (attempt {attempt + 1})"
                        )
                        return
                    except BlockingIOError:
                        if time.time() - start_time > self.timeout:
                            raise
                        time.sleep(0.1)

            except OSError as e:
                if self._lockfile:
                    self._lockfile.close()
                    self._lockfile = None

                if attempt < self.max_retries - 1:
                    wait_time = 0.1 * (2**attempt)  # Exponential backoff
                    logger.warning(f"Failed to acquire lock on {self.filepath}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    raise FileLockError(
                        f"Cannot acquire lock on {self.filepath} after {self.max_retries} attempts"
                    ) from e

    def release(self) -> None:
        """Release lock and close file."""
        if self._lockfile and self._acquired:
            try:
                fcntl.flock(self._lockfile.fileno(), fcntl.LOCK_UN)
                self._lockfile.close()
                self._acquired = False
                logger.debug(f"Released lock on {self.filepath}")
            except OSError as e:
                logger.error(f"Error releasing lock on {self.filepath}: {e}")
            finally:
                self._lockfile = None


@contextmanager
def locked_file_operation(filepath: str, timeout: float = 5.0, max_retries: int = 3) -> Generator:
    """
    Context manager for atomic file operations with locking.

    Usage:
        with locked_file_operation("path/to/file.md") as lock:
            content = Path(lock.filepath).read_text()
            # Modify content
            Path(lock.filepath).write_text(new_content)

    Args:
        filepath: Path to file
        timeout: Lock acquisition timeout (seconds)
        max_retries: Retry attempts

    Raises:
        FileLockError: If lock cannot be acquired
    """
    lock = FileLock(filepath, timeout, max_retries)
    with lock:
        yield lock


def atomic_file_write(filepath: str, content: str, timeout: float = 5.0) -> None:
    """
    Write file contents atomically with locking.

    Acquires exclusive lock, writes to temporary file, then atomically renames.

    Args:
        filepath: Path to file
        content: Content to write
        timeout: Lock acquisition timeout

    Raises:
        FileLockError: If lock cannot be acquired
    """
    filepath = Path(filepath)

    with locked_file_operation(str(filepath), timeout):
        # Write to temporary file first
        temp_file = filepath.with_suffix(".tmp")

        try:
            temp_file.write_text(content, encoding="utf-8")
            # Atomic rename
            temp_file.replace(filepath)
            logger.debug(f"Atomically wrote {filepath}")
        except OSError as e:
            if temp_file.exists():
                temp_file.unlink()
            raise FileLockError(f"Cannot atomically write {filepath}") from e


def atomic_file_read(filepath: str, timeout: float = 5.0) -> str:
    """
    Read file contents atomically with locking.

    Args:
        filepath: Path to file
        timeout: Lock acquisition timeout

    Returns:
        File contents

    Raises:
        FileLockError: If lock cannot be acquired
        FileNotFoundError: If file doesn't exist
    """
    filepath = Path(filepath)

    with locked_file_operation(str(filepath), timeout):
        if not filepath.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")
        return filepath.read_text(encoding="utf-8")


def atomic_file_modify(filepath: str, modify_func, timeout: float = 5.0) -> None:
    """
    Modify file atomically with locking.

    Acquires lock, reads file, calls modify_func, writes result.

    Args:
        filepath: Path to file
        modify_func: Function to transform file contents
        timeout: Lock acquisition timeout

    Raises:
        FileLockError: If lock cannot be acquired
        FileNotFoundError: If file doesn't exist
    """
    filepath = Path(filepath)

    with locked_file_operation(str(filepath), timeout):
        if not filepath.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        content = filepath.read_text(encoding="utf-8")
        new_content = modify_func(content)

        # Write directly (already holding lock)
        temp_file = filepath.with_suffix(".tmp")
        try:
            temp_file.write_text(new_content, encoding="utf-8")
            temp_file.replace(filepath)
            logger.debug(f"Atomically modified {filepath}")
        except OSError as e:
            if temp_file.exists():
                temp_file.unlink()
            raise FileLockError(f"Cannot atomically modify {filepath}") from e
