"""cohezion.compound.universal.init must never write to stdout.

The module runs ``initialize_cohezion_environment()`` at import time, and it is imported
by the compound stdio MCP server, where stdout IS the JSON-RPC channel. Its diagnostics
used to ``print()`` to stdout whenever the log file under ``<cwd>/.opencode/logs`` could
not be written. A banner there corrupts the protocol stream and the client rejects the
handshake, so the breakage depended on the service's cwd and looked intermittent.

The diagnostics must still be VISIBLE: they go to stderr. A fix that simply deleted the
prints would pass a stdout-only check, so each test also asserts the stderr message.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cohezion.compound.universal import init as uinit


REPO_SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory write permissions")
def test_import_from_unwritable_cwd_keeps_stdout_clean(tmp_path):
    """The real import path, as a stdio MCP server would run it."""
    cwd = tmp_path / "ro"
    cwd.mkdir()
    cwd.chmod(0o555)  # .opencode/logs cannot be created -> the fallback print fires
    env = {k: v for k, v in os.environ.items() if k != "COHEZION_NON_INTERACTIVE"}
    env["COHEZION_SESSION_ID"] = "stdout-silence-test"  # marks a cohezion environment
    env["PYTHONPATH"] = str(REPO_SRC)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", "import cohezion.compound.universal.init"],
            cwd=cwd,
            env=env,
            capture_output=True,
            timeout=120,
            check=False,
        )
    finally:
        cwd.chmod(0o755)

    assert proc.returncode == 0, proc.stderr.decode()[-2000:]
    assert b"[COHEZION_INIT" not in proc.stdout, proc.stdout.decode()[-2000:]
    assert b"[COHEZION_INIT" in proc.stderr  # still reported, just not on the RPC channel


def test_error_path_reports_on_stderr_only(monkeypatch, capsys):
    def boom() -> bool:
        raise RuntimeError("detector exploded")

    monkeypatch.delenv("COHEZION_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(uinit, "is_cohezion_environment", boom)
    monkeypatch.setattr(uinit.initialize_cohezion_environment, "_initialized", False, raising=False)

    assert uinit.initialize_cohezion_environment() is False

    out, err = capsys.readouterr()
    assert out == ""
    assert "[COHEZION_INIT_ERROR] detector exploded" in err


def test_missing_tdd_subsystem_reports_on_stderr_only(monkeypatch, capsys):
    monkeypatch.delenv("COHEZION_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(uinit, "is_cohezion_environment", lambda: True)
    monkeypatch.setattr(uinit.initialize_cohezion_environment, "_initialized", False, raising=False)
    # None in sys.modules makes the relative import raise ImportError.
    monkeypatch.setitem(sys.modules, "cohezion.compound.tdd_adversarial", None)

    assert uinit.initialize_cohezion_environment() is True

    out, err = capsys.readouterr()
    assert out == ""
    assert "[COHEZION_INIT_SKIP] tdd_adversarial unavailable" in err
