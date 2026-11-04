"""The README promises `uv run python examples/quickstart.py` works offline. Hold it to that."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_quickstart_runs_offline_and_passes() -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    proc = subprocess.run(
        [sys.executable, str(REPO / "examples" / "quickstart.py")],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Quickstart complete." in proc.stdout
    # Each section ran and reported, not just the banner.
    for marker in ("NPU(", "SELF-TEST OK", "value=42", "SafeExecImportRefusedError"):
        assert marker in proc.stdout, f"missing {marker!r}:\n{proc.stdout}"
