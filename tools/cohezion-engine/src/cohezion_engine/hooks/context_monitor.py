#!/usr/bin/env python3
"""Claude Code PostToolUse hook: monitor context usage and warn at thresholds.

Protocol:
  - Reads JSON from stdin (Claude Code hook format)
  - Exit 0 always (informational output only)
  - Prints context status to stdout at 80% (WARNING) and 90% (CLEAR_NEEDED)
  - Writes a context snapshot to the session directory on status transitions

Environment:
  CZ_TEST_SESSION_JSONL: Override session JSONL path (for testing)
  CZ_TEST_SESSION_DIR:   Override session directory path (for testing)
"""

import os
import sys
from pathlib import Path

# Add project src to path if running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cohezion_engine.context import (
    _find_active_session_jsonl,
    estimate_context,
    read_previous_status,
    write_context_snapshot,
    write_current_status,
)


def _get_session_dir() -> Path | None:
    """Return the session directory, using test override if set."""
    test_dir = os.environ.get("CZ_TEST_SESSION_DIR")
    if test_dir:
        return Path(test_dir)
    try:
        from cohezion_engine.session import get_session_dir

        return get_session_dir()
    except Exception:
        return None


def main() -> int:
    try:
        sys.stdin.read()
    except Exception:
        pass

    # Support test override of session JSONL path
    test_jsonl = os.environ.get("CZ_TEST_SESSION_JSONL")
    session_jsonl = Path(test_jsonl) if test_jsonl else _find_active_session_jsonl()

    result = estimate_context(session_jsonl=session_jsonl)
    status = result["status"]
    pct = result.get("percentage", 0.0)

    # Write snapshot on status transitions to WARNING or CLEAR_NEEDED
    session_dir = _get_session_dir()
    if session_dir is not None:
        prev_status = read_previous_status(session_dir)
        if status != prev_status and status in ("WARNING", "CLEAR_NEEDED"):
            try:
                write_context_snapshot(session_dir, result)
            except Exception:
                pass  # Never block the hook on snapshot failure
        write_current_status(session_dir, status)

    if status == "CLEAR_NEEDED":
        print(
            f"\n⚠️  CONTEXT CRITICAL: {pct:.1f}% used — CLEAR_NEEDED\n"
            "   Write continuation file and trigger session handoff immediately!\n"
            "   Run: cz session send-clear <plan.md>",
            flush=True,
        )
    elif status == "WARNING":
        print(
            f"⚡ Context: {pct:.1f}% — WARNING (80%+ threshold reached). "
            "Wrap up current task and prepare for handoff.",
            flush=True,
        )
    # OK status: no output (stay silent)

    return 0


if __name__ == "__main__":
    sys.exit(main())
