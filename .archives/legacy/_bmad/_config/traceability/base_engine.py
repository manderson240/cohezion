#!/usr/bin/env python3
"""
Base Engine - Shared functionality for traceability engines

Provides:
- Command execution with timeout handling
- File discovery utilities
- CSV writing utilities
- Error handling with logging
- Dependency injection support
"""

from __future__ import annotations

import csv
import logging
import subprocess
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EngineConfig:
    """Engine configuration with dependency injection support."""

    project_root: Path
    output_dir: Path
    timeout: int = 300
    verbose: bool = True
    dry_run: bool = False


class BaseEngine(ABC):
    """Abstract base class for all traceability engines."""

    def __init__(self, config: EngineConfig):
        self.config = config
        self.project_root = config.project_root
        self.output_dir = config.output_dir

        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if config.verbose else logging.INFO)

        # Ensure output directory exists
        if not config.dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_command(
        self, cmd: List[str], timeout: Optional[int] = None, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run shell command with error handling and timeout.

        Args:
            cmd: Command and arguments as list
            timeout: Timeout in seconds (default: 300)
            capture_output: Whether to capture stdout/stderr

        Returns:
            Tuple of (returncode, stdout, stderr)

        Raises:
            subprocess.TimeoutExpired: If command times out
        """
        timeout = timeout or self.config.timeout

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root,
                timeout=timeout,
            )
            self.logger.debug(f"Command completed: {' '.join(cmd[:3])}...")
            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout}s: {' '.join(cmd[:3])}")
            return -1, "", f"Timeout after {timeout}s"

        except FileNotFoundError as e:
            self.logger.error(f"Command not found: {cmd[0]}")
            return -1, "", str(e)

        except PermissionError as e:
            self.logger.error(f"Permission denied: {cmd[0]}")
            return -1, "", str(e)

        except Exception as e:
            self.logger.error(f"Unexpected error running command: {e}")
            self.logger.debug(traceback.format_exc())
            return -1, "", str(e)

    def discover_python_files(self, root_dir: Path, pattern: str = "**/*.py") -> List[Path]:
        """
        Discover Python files in directory.

        Args:
            root_dir: Root directory to search
            pattern: Glob pattern (default: **/*.py)

        Returns:
            List of Path objects
        """
        try:
            files = list(root_dir.glob(pattern))
            self.logger.debug(f"Discovered {len(files)} Python files")
            return files
        except Exception as e:
            self.logger.error(f"Error discovering files: {e}")
            self.logger.debug(traceback.format_exc())
            return []

    def write_csv(
        self,
        file_path: Path,
        fieldnames: List[str],
        rows: List[Dict[str, Any]],
        overwrite: bool = True,
    ) -> Path:
        """
        Write data to CSV file.

        Args:
            file_path: Output file path
            fieldnames: CSV column names
            rows: List of dicts (one per row)
            overwrite: Whether to overwrite existing file

        Returns:
            Path to written file
        """
        if self.config.dry_run:
            self.logger.info(f"[DRY RUN] Would write {len(rows)} rows to {file_path}")
            return file_path

        mode = "w" if overwrite else "a"
        with open(file_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if overwrite:
                writer.writeheader()
            writer.writerows(rows)

        self.logger.info(f"Wrote {len(rows)} rows to {file_path}")
        return file_path

    def read_file_safe(self, file_path: Path, encoding: str = "utf-8") -> Optional[str]:
        """
        Safely read file with error handling.

        Args:
            file_path: File to read
            encoding: File encoding

        Returns:
            File contents or None if error
        """
        try:
            return file_path.read_text(encoding=encoding)
        except FileNotFoundError as e:
            self.logger.warning(f"File not found: {file_path}")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied: {file_path}")
            return None
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error in {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            self.logger.debug(traceback.format_exc())
            return None

    def get_relative_path(self, file_path: Path, base_dir: Optional[Path] = None) -> str:
        """
        Get relative path from base directory.

        Args:
            file_path: Absolute file path
            base_dir: Base directory (default: project_root)

        Returns:
            Relative path as string
        """
        base_dir = base_dir or self.project_root
        try:
            return str(file_path.relative_to(base_dir))
        except ValueError:
            # file_path is not relative to base_dir
            return str(file_path)

    @abstractmethod
    def run_full_extraction(self) -> Any:
        """
        Run full extraction pipeline.

        Must be implemented by subclasses.

        Returns:
            Extraction results (type varies by engine)
        """
        pass

    @abstractmethod
    def write_results(self, results: Any) -> Dict[str, Path]:
        """
        Write results to output files.

        Must be implemented by subclasses.

        Args:
            results: Extraction results

        Returns:
            Dict of output file paths
        """
        pass
