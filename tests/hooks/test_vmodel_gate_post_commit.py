"""Unit tests for scripts/hooks/vmodel_gate_post_commit.py.

The hook itself lives under scripts/ (invoked from .git/hooks/post-commit), not
src/, so the test manipulates sys.path to import it. Covers the pure functions
that don't touch git/SurrealDB — the network-touching path is verified by the
end-to-end invocation in CI / by committing the hook itself.
"""

from __future__ import annotations

import sys
from pathlib import Path


_HOOK_DIR = Path(__file__).resolve().parents[2] / "scripts" / "hooks"
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

import vmodel_gate_post_commit as h  # noqa: E402


def test_escape_sql_string_handles_quotes_and_backslashes() -> None:
    assert h._escape_sql_string("it's") == "it\\'s"
    assert h._escape_sql_string("back\\slash") == "back\\\\slash"
    assert h._escape_sql_string("no specials") == "no specials"


def test_paired_test_for_maps_src_cohezion_module_convention() -> None:
    """src/cohezion/<mod>/<name>.py → tests/<mod>/test_<name>.py (when exists)."""
    paired = h._paired_test_for("src/cohezion/inference/registry.py")
    assert paired == "tests/inference/test_registry.py"


def test_paired_test_for_returns_none_when_no_mirror_exists() -> None:
    """Files without a paired test (e.g. a bespoke competition module with no
    test file yet) return None, which the hook records as passed=False."""
    paired = h._paired_test_for("src/cohezion/competition/sei_accelathon/assessment.py")
    assert paired is None


def test_paired_test_for_handles_non_python_files() -> None:
    """Docs / configs don't get paired tests via this function — the hook
    routes them to level='architecture' separately."""
    assert h._paired_test_for("src/cohezion/skills/CAPABILITY_REGISTRY_PRIME.md") is None
    assert h._paired_test_for("README.md") is None


def test_basic_auth_produces_valid_header() -> None:
    header = h._basic_auth("root", "root")
    # Decoded: "root:root" → base64 "cm9vdDpyb290"
    assert header == "Basic cm9vdDpyb290"


def test_session_id_prefers_env_var_over_fallback() -> None:
    import os

    original = os.environ.get("COHEZION_SESSION_ID")
    try:
        os.environ["COHEZION_SESSION_ID"] = "test-session-xyz"
        assert h._session_id("abc123def") == "test-session-xyz"
        del os.environ["COHEZION_SESSION_ID"]
        assert h._session_id("abc123def") == "auto-abc123def"
    finally:
        if original is not None:
            os.environ["COHEZION_SESSION_ID"] = original
