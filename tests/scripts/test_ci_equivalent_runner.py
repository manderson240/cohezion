"""Consumption and failure-mode tests for scripts/ci/ci_equivalent_netns.sh.

The runner answers "is the repo green" the way CI answers it (no local services). A runner
nothing invokes is dormant, and a runner that can report green on a pytest usage error is worse
than none (the first draft did both things wrong), so both properties are pinned here.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ci" / "ci_equivalent_netns.sh"


def _can_unshare() -> bool:
    return (
        shutil.which("unshare") is not None
        and subprocess.run(["unshare", "-rn", "true"], capture_output=True).returncode == 0
    )


# ── T1 structural ─────────────────────────────────────────────────────────────
def test_t1_script_parses():
    assert subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True).returncode == 0


@pytest.mark.parametrize("consumer", ["Makefile", "scripts/ci/automerge_guard.sh", "CLAUDE.md"])
def test_t3_runner_is_consumed(consumer):
    """A runner no gate or doc points at is dormant — the class it exists to catch."""
    assert "ci_equivalent_netns.sh" in (REPO / consumer).read_text(encoding="utf-8")


# ── T2 discriminating: the two defects the first draft had ────────────────────
def test_t2_unusable_explicit_interpreter_is_refused_not_replaced(tmp_path):
    """CI_EQUIV_PYTHON that cannot import pytest+xdist must exit 3, never fall back silently."""
    fake = tmp_path / "python"
    fake.write_text("#!/usr/bin/env bash\nexit 1\n")
    fake.chmod(0o755)
    env = {**os.environ, "CI_EQUIV_PYTHON": str(fake), "CI_EQUIV_LOG": str(tmp_path / "log")}
    proc = subprocess.run(["bash", str(SCRIPT), "unit"], capture_output=True, text=True, env=env)
    assert proc.returncode == 3, proc.stderr
    assert "cannot import pytest and xdist" in proc.stderr


@pytest.mark.skipif(
    not _can_unshare(), reason="user+network namespaces unavailable (agent sandbox)"
)
def test_t2_pytest_usage_error_is_not_green(tmp_path):
    """A fake interpreter that passes the import probe but exits 4 (pytest usage error) when run
    must make the script exit non-zero. The first draft grepped for FAILED lines and called this
    green."""
    fake = tmp_path / "python"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in *"import pytest, xdist"*) exit 0;; *"import cohezion"*) echo stub;; '
        "*) echo 'ERROR: usage: fake pytest' >&2; exit 4;; esac\n"
    )
    fake.chmod(0o755)
    env = {**os.environ, "CI_EQUIV_PYTHON": str(fake), "CI_EQUIV_LOG": str(tmp_path / "log")}
    proc = subprocess.run(["bash", str(SCRIPT), "unit"], capture_output=True, text=True, env=env)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "NOT GREEN" in proc.stdout
