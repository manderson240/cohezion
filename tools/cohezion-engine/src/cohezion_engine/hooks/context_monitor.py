#!/usr/bin/env python3
"""Claude Code PostToolUse hook: monitor context usage and warn at thresholds.

Protocol:
  - Reads JSON from stdin (Claude Code hook format)
  - Exit 0 always (informational output only)
  - Prints context status to stdout at 80% (WARNING) and 90% (CLEAR_NEEDED)

Environment:
  CZ_TEST_SESSION_JSONL: Override session JSONL path (for testing)
"""
import json
import os
import sys
from pathlib import Path

# Add project src to path if running standalone
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cohezion_engine.context import estimate_context, _find_active_session_jsonl


def main() -> int:
    try:
        # Read hook input (we don't need it, but must consume stdin)
        sys.stdin.read()
    except Exception:
        pass

    # Support test override of session JSONL path
    test_jsonl = os.environ.get("CZ_TEST_SESSION_JSONL")
    session_jsonl = Path(test_jsonl) if test_jsonl else _find_active_session_jsonl()

    result = estimate_context(session_jsonl=session_jsonl)
    status = result["status"]
    pct = result.get("percentage", 0.0)

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
