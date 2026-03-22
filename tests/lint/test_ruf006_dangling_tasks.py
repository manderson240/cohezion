"""Regression test: no RUF006 dangling asyncio tasks in src/cohezion/.

Fails if any asyncio.create_task() call discards its return value, which
allows the event loop to garbage-collect the task mid-execution.
"""

import shutil
import subprocess
from pathlib import Path

SRC = Path(__file__).parents[2] / "src" / "cohezion"


def test_no_ruf006_violations():
    """RUF006: all asyncio.create_task() results must be stored."""
    ruff = shutil.which("ruff") or "ruff"
    result = subprocess.run(
        [ruff, "check", str(SRC), "--select", "RUF006"],
        capture_output=True,
        text=True,
    )
    violations = [
        line for line in result.stdout.splitlines() if "RUF006" in line
    ]
    assert result.returncode == 0, (
        f"Found {len(violations)} RUF006 violations:\n"
        + "\n".join(violations[:20])
    )
