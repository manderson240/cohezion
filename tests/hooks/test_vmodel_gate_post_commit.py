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

import vmodel_gate_post_commit as h


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


# ---------------------------------------------------------------------------
# Structural import-drift gate (L367 / ARC Lesson 2)
# ---------------------------------------------------------------------------


def test_resolve_cohezion_module_finds_package_init(tmp_path) -> None:
    (tmp_path / "src" / "cohezion" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "pkg" / "__init__.py").write_text("X = 1")
    resolved = h._resolve_cohezion_module("cohezion.pkg", tmp_path)
    assert resolved is not None
    assert resolved.name == "__init__.py"


def test_resolve_cohezion_module_finds_submodule_file(tmp_path) -> None:
    (tmp_path / "src" / "cohezion" / "inference").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "inference" / "fleet.py").write_text("def route(): pass")
    resolved = h._resolve_cohezion_module("cohezion.inference.fleet", tmp_path)
    assert resolved is not None
    assert resolved.name == "fleet.py"


def test_resolve_cohezion_module_returns_none_for_non_existent(tmp_path) -> None:
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    assert h._resolve_cohezion_module("cohezion.does_not_exist", tmp_path) is None


def test_top_level_names_extracts_defs_classes_assignments(tmp_path) -> None:
    f = tmp_path / "m.py"
    f.write_text(
        "import os\n"
        "from typing import List as L\n"
        "CONST = 42\n"
        "annotated: int = 7\n"
        "def func(): pass\n"
        "async def afunc(): pass\n"
        "class MyClass: pass\n"
    )
    names = h._top_level_names(f)
    assert names == {"os", "L", "CONST", "annotated", "func", "afunc", "MyClass"}


def test_top_level_names_returns_empty_on_syntax_error(tmp_path) -> None:
    f = tmp_path / "broken.py"
    f.write_text("def foo(\n")  # unterminated
    assert h._top_level_names(f) == set()


def test_check_import_drift_clean_when_all_names_exist(tmp_path) -> None:
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "api.py").write_text(
        "def submit(): pass\nclass KaggleAPI: pass\n"
    )
    caller = tmp_path / "caller.py"
    caller.write_text("from cohezion.api import submit, KaggleAPI\n")
    assert h._check_import_drift(caller, tmp_path) == []


def test_check_import_drift_flags_missing_symbol(tmp_path) -> None:
    """This is the AGI_GOLF critical finding #3 — importing a symbol
    that doesn't exist in the target module."""
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "api.py").write_text(
        "class KaggleAPI:\n    def submit_to_competition(self): pass\n"
    )
    caller = tmp_path / "caller.py"
    # submit_adapter doesn't exist — classic latent bug
    caller.write_text("from cohezion.api import submit_adapter, KaggleAPI\n")
    drifts = h._check_import_drift(caller, tmp_path)
    assert len(drifts) == 1
    assert "submit_adapter" in drifts[0]
    assert "not defined" in drifts[0]


def test_check_import_drift_flags_missing_module(tmp_path) -> None:
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    caller = tmp_path / "caller.py"
    caller.write_text("from cohezion.nonexistent import foo\n")
    drifts = h._check_import_drift(caller, tmp_path)
    assert len(drifts) == 1
    assert "not found" in drifts[0]


def test_check_import_drift_ignores_non_cohezion_imports(tmp_path) -> None:
    caller = tmp_path / "caller.py"
    caller.write_text("import os\nfrom pathlib import Path\nfrom third_party_lib import function\n")
    # We only care about cohezion.* drift; external libs are not our concern
    assert h._check_import_drift(caller, tmp_path) == []


def test_check_import_drift_skips_wildcard_imports(tmp_path) -> None:
    """`from cohezion.api import *` bypasses the check — we can't statically
    resolve which names are pulled in by a wildcard."""
    (tmp_path / "src" / "cohezion").mkdir(parents=True)
    (tmp_path / "src" / "cohezion" / "api.py").write_text("X = 1\n")
    caller = tmp_path / "caller.py"
    caller.write_text("from cohezion.api import *\n")
    assert h._check_import_drift(caller, tmp_path) == []
