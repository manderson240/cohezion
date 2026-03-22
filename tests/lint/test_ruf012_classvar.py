"""Regression test: no RUF012 mutable class defaults in src/cohezion/.

Fails if any class attribute uses a mutable default (list/dict/set) without
a ClassVar annotation. This prevents the 'shared mutable class state' footgun.
"""

import shutil
import subprocess
from pathlib import Path

SRC = Path(__file__).parents[2] / "src" / "cohezion"


def test_no_ruf012_violations():
    """RUF012: all mutable class defaults must be annotated with ClassVar."""
    ruff = shutil.which("ruff") or "ruff"
    result = subprocess.run(
        [ruff, "check", str(SRC), "--select", "RUF012"],
        capture_output=True,
        text=True,
    )
    violations = [
        line for line in result.stdout.splitlines() if "RUF012" in line
    ]
    assert result.returncode == 0, (
        f"Found {len(violations)} RUF012 violations:\n"
        + "\n".join(violations[:20])
    )
