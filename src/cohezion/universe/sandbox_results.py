"""File-based persistence for sandbox execution results.

Saves BackendResult output files, stdout/stderr, and metadata to
``data/simulations/{run_id}/``. No SurrealDB dependency — composable
and debuggable.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from cohezion.universe.sandbox_backends import BackendResult



logger = logging.getLogger(__name__)

DEFAULT_BASE_DIR = Path("data/simulations")


def persist_result(
    result: BackendResult,
    run_id: str,
    *,
    tier: str = "unknown",
    backend: str = "unknown",
    base_dir: Path = DEFAULT_BASE_DIR,
) -> Path:
    """Persist a BackendResult to disk.

    Parameters
    ----------
    result : BackendResult
        The execution result to persist.
    run_id : str
        Unique identifier for this run (used as directory name).
    tier : str
        The sandbox tier used (for metadata).
    backend : str
        The backend name used (for metadata).
    base_dir : Path
        Root directory for simulation results.

    Returns
    -------
    Path
        The directory where results were saved.
    """
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save stdout/stderr
    if result.stdout:
        (run_dir / "stdout.txt").write_text(result.stdout)
    if result.stderr:
        (run_dir / "stderr.txt").write_text(result.stderr)

    # Save output files
    if result.output_files:
        output_dir = run_dir / "output"
        output_dir.mkdir(exist_ok=True)
        for filename, content in result.output_files.items():
            (output_dir / filename).write_bytes(content)

    # Save metadata
    meta = {
        "run_id": run_id,
        "tier": tier,
        "backend": backend,
        "success": result.success,
        "exit_code": result.exit_code,
        "duration": result.duration,
        "output_file_count": len(result.output_files) if result.output_files else 0,
        "persisted_at": time.time(),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    logger.info(f"Persisted sandbox result to {run_dir}")
    return run_dir
