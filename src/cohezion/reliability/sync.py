"""
Reliability Synchronization Primitives.

Provides:
- FileLock: Advisory file locking using fcntl.
- SafeWriter: Atomic file writes via temporary staging and rename.
- AgentWorkspace: Shadow tree isolation for multi-file agent operations.
"""

import fcntl
import logging
import os
import shutil
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


logger = logging.getLogger(__name__)


class FileLock:
    """
    Advisory file locking context manager.
    Uses POSIX flock (exclusive) to coordinate access across processes.
    """

    def __init__(self, lock_file: str | Path, timeout: float = 10.0):
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self._fd = None

    @contextmanager
    def acquire(self) -> Generator[None]:
        """Block until lock is acquired or timeout is reached."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        # Touch the file to ensure it exists
        self.lock_file.touch()

        self._fd = open(self.lock_file)
        try:
            start_time = time.monotonic()
            while True:
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.debug(f"Lock acquired on {self.lock_file}")
                    break
                except OSError:
                    current_time = time.monotonic()
                    if current_time - start_time > self.timeout:
                        raise TimeoutError(f"Timed out waiting for lock on {self.lock_file}") from None
                    time.sleep(0.1)  # Fixed sleep instead of os.sched_yield for test stability
            yield
        finally:
            if self._fd:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                self._fd.close()
                self._fd = None
                logger.debug(f"Lock released on {self.lock_file}")


class SafeWriter:
    """
    Atomic file writer context manager.
    Writes to a temporary file and renames it to the target on success.
    """

    def __init__(self, target_path: str | Path, mode: str = "w"):
        self.target_path = Path(target_path)
        self.mode = mode
        self.temp_path = None

    @contextmanager
    def open(self) -> Generator[tempfile.NamedTemporaryFile]:
        """Provide a temporary file for writing."""
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        # Use a temporary file in the same directory to ensure rename is atomic (same mount point)
        with tempfile.NamedTemporaryFile(
            mode=self.mode,
            dir=self.target_path.parent,
            prefix=f".tmp_{self.target_path.name}_",
            delete=False,
        ) as tmp:
            self.temp_path = Path(tmp.name)
            try:
                yield tmp
                tmp.flush()
                os.fsync(tmp.fileno())  # Ensure data is on disk
                os.replace(self.temp_path, self.target_path)
                logger.debug(f"Atomic update completed for {self.target_path}")
            except Exception:
                if self.temp_path and self.temp_path.exists():
                    self.temp_path.unlink()
                raise


class AgentWorkspace:
    """
    Shadow tree isolation for multi-file operations.
    Creates a temporary workspace, clones relevant files, and merges on success.
    """

    def __init__(self, base_dir: Path, files: list[Path], workspace_root: Path | None = None):
        self.base_dir = base_dir
        self.files = files
        self.workspace_root = workspace_root or Path(".sandbox")
        self.staging_dir = None

    @contextmanager
    def session(self) -> Generator[Path]:
        """Sets up the staging environment."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.staging_dir = Path(tempfile.mkdtemp(dir=self.workspace_root, prefix="agent_ws_"))

        try:
            # 1. Clone relevant files into staging
            for f in self.files:
                rel_path = f.relative_to(self.base_dir)
                dest = self.staging_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                logger.debug(f"Cloned {f} to {dest}")

            # 2. Yield the staging directory for the agent to work in
            yield self.staging_dir

            # 3. Merge verified changes back (assuming verification happened inside the yield)
            # Higher level logic should decide whether to merge.
            # This primitive just provides the isolated space.
            # Merging logic is currently handled by the caller or specialized method.

        finally:
            if self.staging_dir and self.staging_dir.exists():
                shutil.rmtree(self.staging_dir)
                logger.debug(f"Cleaned up workspace {self.staging_dir}")

    def commit(self):
        """Merge staging changes back to base_dir."""
        if not self.staging_dir or not self.staging_dir.exists():
            raise RuntimeError("No active staging session to commit.")

        for f in self.files:
            rel_path = f.relative_to(self.base_dir)
            source = self.staging_dir / rel_path
            dest = f
            if source.exists():
                # Use SafeWriter for individual file updates during merge
                with SafeWriter(dest).open() as out:
                    out.write(source.read_text())
                logger.info(f"Committed changes for {dest}")
