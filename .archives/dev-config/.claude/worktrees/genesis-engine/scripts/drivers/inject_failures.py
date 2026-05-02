from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar


logger = logging.getLogger("FailureInjector")


class FailureInjector:
    """Injects synthetic 'Red Wall' failures for validation."""

    # Security: Whitelist of allowed targets for failure injection
    # Only these files can be modified by the failure injector
    ALLOWED_TARGETS: ClassVar[set[str]] = {
        "src/cohezion/healing/drift_analyzer.py",
        "src/cohezion/reliability/substrate_governor.py",
        "tests/healing/test_drift_analyzer.py",
        "tests/reliability/test_dilation_controller.py",
    }

    def __init__(self):
        # Validate targets exist relative to project root
        self.project_root = Path(__file__).parent.parent.parent
        self._backups: dict[str, str] = {}  # Store original content for rollback

    def _validate_path(self, file_path: str) -> Path:
        """
        Validate that the file path is in the allowed list.
        Security: Prevents arbitrary file modification.
        """
        abs_path = (self.project_root / file_path).resolve()

        # Check path traversal
        try:
            abs_path.relative_to(self.project_root)
        except ValueError as err:
            raise ValueError(f"Path traversal attempt blocked: {file_path}") from err

        # Check against whitelist
        normalized = str(abs_path.relative_to(self.project_root))
        if normalized not in self.ALLOWED_TARGETS:
            raise ValueError(
                f"Target not in allowed list: {file_path}. Allowed targets: {', '.join(sorted(self.ALLOWED_TARGETS))}"
            )

        if not abs_path.exists():
            raise FileNotFoundError(f"Target file does not exist: {file_path}")

        return abs_path

    def inject_broken_import(self, file_path: str) -> bool:
        """Injects a non-existent import to trigger a failure.

        Returns:
            True if injection succeeded, False otherwise.
        """
        logger.info(f"Injecting broken import into {file_path}")
        try:
            path = self._validate_path(file_path)

            # Security: Create backup before modification
            content = path.read_text()
            self._backups[str(path)] = content

            # Inject failure
            with open(path, "w") as f:
                f.write("import non_existent_module_xyz\n" + content)

            logger.info(f"✅ Successfully injected broken import into {file_path}")
            return True

        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Failed to inject: {e}")
            return False

    def inject_logic_bug(self, file_path: str) -> bool:
        """Injects a zero division error.

        Returns:
            True if injection succeeded, False otherwise.
        """
        logger.info(f"Injecting logic bug into {file_path}")
        try:
            path = self._validate_path(file_path)

            # Security: Create backup before modification
            content = path.read_text()
            self._backups[str(path)] = content

            # Inject failure
            with open(path, "w") as f:
                f.write("x = 1 / 0\n" + content)

            logger.info(f"✅ Successfully injected logic bug into {file_path}")
            return True

        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Failed to inject: {e}")
            return False

    def restore(self, file_path: str) -> bool:
        """Restores file from backup.

        Returns:
            True if restore succeeded, False otherwise.
        """
        try:
            path = self._validate_path(file_path)
            path_str = str(path)

            if path_str not in self._backups:
                # Fallback: Remove injected lines if no backup
                lines = path.read_text().splitlines()
                new_lines = [
                    line for line in lines if "non_existent_module_xyz" not in line and "x = 1 / 0" not in line
                ]
                path.write_text("\n".join(new_lines) + "\n")
                logger.info(f"✅ Restored {file_path} by removing injected lines")
            else:
                # Restore from backup
                path.write_text(self._backups[path_str])
                del self._backups[path_str]
                logger.info(f"✅ Restored {file_path} from backup")

            return True

        except Exception as e:
            logger.error(f"Failed to restore {file_path}: {e}")
            return False

    def restore_all(self) -> dict[str, bool]:
        """Restore all files that have been modified.

        Returns:
            Dict mapping file paths to restore success status.
        """
        results = {}
        for file_path in list(self._backups.keys()):
            try:
                rel_path = str(Path(file_path).relative_to(self.project_root))
                results[rel_path] = self.restore(rel_path)
            except Exception as e:
                logger.error(f"Failed to restore {file_path}: {e}")
                results[file_path] = False
        return results


if __name__ == "__main__":
    injector = FailureInjector()
    print("Failure Injector initialized.")
    print(f"Allowed targets: {len(injector.ALLOWED_TARGETS)} files")
    print(f"Project root: {injector.project_root}")
