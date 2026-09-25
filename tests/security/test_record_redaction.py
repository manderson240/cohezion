"""Process-wide log redaction must not depend on import order or logging configuration order.

Until 2026-09-25 redaction reached the root handler only because ``security/adversarial_tester``
called ``logging.basicConfig`` as an import side effect of the eager ``cohezion.core`` facade and
``log_redactor`` then attached a filter to that handler. Making the facade lazy silently turned
redaction off. These tests run in fresh interpreters so the global LogRecord factory is real.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path


SRC = Path(__file__).resolve().parents[2] / "src"
SECRET = "sk-live-9f8e7d6c5b4a"


def _run(body: str) -> str:
    out = subprocess.run(
        [sys.executable, "-c", body],
        capture_output=True,
        text=True,
        timeout=120,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
    )
    assert out.returncode == 0, out.stderr[-800:]
    return out.stderr


def test_redacted_when_logging_configured_after_import() -> None:
    err = _run(
        "import logging, cohezion.core.event_bus\n"
        "logging.basicConfig(level=logging.INFO)\n"
        f"logging.getLogger('x').info('api_key={SECRET}')\n"
    )
    assert "[REDACTED]" in err
    assert SECRET not in err


def test_redacted_when_logging_configured_before_import() -> None:
    err = _run(
        "import logging\n"
        "logging.basicConfig(level=logging.INFO)\n"
        "import cohezion\n"
        f"logging.getLogger('x').warning('password=%s', '{SECRET}')\n"
    )
    assert SECRET not in err
    assert "[REDACTED]" in err


def test_redaction_does_not_load_package_facades() -> None:
    err = _run(
        "import sys, cohezion\n"
        "heavy = [m for m in sys.modules if m.startswith(('cohezion.security', 'cohezion.core'))]\n"
        "print(heavy, file=sys.stderr)\n"
    )
    assert err.strip() == "[]"


def test_install_is_idempotent_and_preserves_non_string_args() -> None:
    from cohezion._redaction import install_record_redaction

    install_record_redaction()  # may or may not be first in this process
    assert install_record_redaction() is False
    record = logging.getLogRecordFactory()("n", logging.INFO, __file__, 1, "count=%d", (3,), None)
    assert record.getMessage() == "count=3"
