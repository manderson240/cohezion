"""Import smoke test: verify source modules import without error.

This test runs in CI and catches:
- Missing functions (e.g. build_gaia_mcp_tier was missing after consolidation)
- SyntaxErrors (e.g. semantic_cache duplicate __init__)
- Broken imports (e.g. TraceType → ExperienceTraceType rename mismatch)
- Missing constants (e.g. LEMONADE_NPU_BASE_URL not in config.defaults)

Selection: COHEZION_IMPORT_SMOKE_BASE if set, else the merge-base with main or the
last tag. With no base or no changed files it imports every source module, which is
what happens in CI's shallow clone.

A module may only skip when a third-party package it needs is not installed. Every
other failure is a hard failure, unless the module is listed in _KNOWN_BROKEN. That
list may only shrink: strict xfail fails the run when a listed module starts working.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


_SRC = Path(__file__).resolve().parents[2] / "src"

# Code defects, not environment gaps.
_KNOWN_BROKEN: dict[str, str] = {
    "cohezion.agents.adk_swarm.aimo_specialists.agent": (
        "imports cohezion.sandbox.aimo, which is not in src/; also uses instructions= and "
        "adk.tool, which google.adk rejects"
    ),
    "cohezion.agents.adk_swarm.aimo_specialists.orchestrator": (
        "imports cohezion.sandbox.aimo, which is not in src/"
    ),
    "cohezion.flume.git_encoder": (
        "imports cohezion.swarm.git_health, deleted in 92e9e4a5b; needs a wiring target"
    ),
    "cohezion.competition.neurogolf.eval": "script-style sibling import of tiny_conv_arc",
    "cohezion.skills.kaggle.modules.badge-collector.scripts.badge_tracker": (
        "script-style sibling import of badge_registry"
    ),
    "cohezion.skills.kaggle.modules.comp-report.scripts.competition_details": (
        "script-style sibling import of utils"
    ),
    "cohezion.skills.kaggle.modules.comp-report.scripts.list_competitions": (
        "script-style sibling import of utils"
    ),
}


def _get_changed_modules() -> list[str]:
    """Get module names for all changed Python source files."""
    # Try env var first (CI passes base SHA), then merge-base, then last tag
    base_sha = os.environ.get("COHEZION_IMPORT_SMOKE_BASE")
    if not base_sha:
        for cmd in [
            ["git", "merge-base", "HEAD", "origin/main"],
            ["git", "merge-base", "HEAD", "main"],
            ["git", "describe", "--tags", "--abbrev=0"],
        ]:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                base_sha = result.stdout.strip()
                break

    if base_sha:
        cmd = ["git", "diff", "--name-only", f"{base_sha}..HEAD", "--", "src/cohezion/"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        files = [
            f
            for f in result.stdout.splitlines()
            if f.endswith(".py") and "__init__" not in f and "CLAUDE" not in f and "test_" not in f
        ]
        if not files:
            # No changes detected — fall through to all source files
            base_sha = None

    if not base_sha:
        # No base or no changes — test all source files
        cmd = ["git", "ls-files", "src/cohezion/"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        files = [
            f
            for f in result.stdout.splitlines()
            if f.endswith(".py") and "__init__" not in f and "CLAUDE" not in f and "test_" not in f
        ]

    modules = set()
    for f in files:
        mod = f.replace("src/", "").replace("/", ".").replace(".py", "")
        modules.add(mod)

    return sorted(modules)


def _importing_file(exc: Exception) -> Path | None:
    """The last real file in exc's traceback, which is the one that ran the import."""
    importer = None
    tb = exc.__traceback__
    while tb:
        filename = tb.tb_frame.f_code.co_filename
        if not filename.startswith("<"):
            importer = Path(filename)
        tb = tb.tb_next
    return importer


def _missing_third_party(exc: Exception) -> str | None:
    """Name the absent third-party package behind exc, or None if exc is anything else."""
    if not isinstance(exc, ModuleNotFoundError) or not exc.name:
        return None
    root = exc.name.split(".")[0]
    # A file beside the importer means a script-style sibling import, so a real defect.
    importer = _importing_file(exc)
    if importer and (
        (importer.parent / f"{root}.py").exists() or (importer.parent / root).is_dir()
    ):
        return None
    try:
        return root if importlib.util.find_spec(root) is None else None
    except ValueError:  # already in sys.modules without a spec, so it is present
        return None


def _import_in_fresh_process(module_name: str) -> tuple[bool, str]:
    """Import in a new interpreter with this sys.path. Returns (success, stderr tail)."""
    # This tree goes first: importing cohezion can put another checkout's src on sys.path.
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(_SRC), *(p for p in sys.path if p)])}
    # Imports can write to the cwd, and -c puts the cwd on sys.path, so use an empty one.
    with tempfile.TemporaryDirectory() as cwd:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib,sys; importlib.import_module(sys.argv[1])",
                module_name,
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=cwd,
            env=env,
        )
    return result.returncode == 0, result.stderr[-800:]


def _check_import(module_name: str) -> tuple[str, str]:
    """Try to import a module. Returns (status, detail); status is ok, skip or fail."""
    try:
        importlib.import_module(module_name)
        return "ok", ""
    except SystemExit as e:
        return "skip", f"{module_name} calls sys.exit at import: {e}"
    except Exception as e:
        missing = _missing_third_party(e)
        if missing:
            return "skip", f"third-party package {missing} is not installed"
        failure = f"{type(e).__name__}: {e}"
    # Another test's imports can break this one, so only a fresh process can convict it.
    success, stderr = _import_in_fresh_process(module_name)
    if success:
        return "ok", ""
    return "fail", f"{failure}\n{stderr}"


_CHANGED_MODULES = [m for m in _get_changed_modules() if m not in _KNOWN_BROKEN]


@pytest.mark.parametrize("module_name", _CHANGED_MODULES, ids=_CHANGED_MODULES)
def test_module_imports_cleanly(module_name: str) -> None:
    """Every selected module must import, or be missing only a third-party package."""
    status, detail = _check_import(module_name)
    if status == "skip":
        pytest.skip(detail)
    if status == "fail":
        pytest.fail(f"Failed to import {module_name}: {detail}")


@pytest.mark.parametrize(
    "module_name",
    [
        pytest.param(m, marks=pytest.mark.xfail(strict=True, reason=r))
        for m, r in sorted(_KNOWN_BROKEN.items())
    ],
)
def test_known_broken_module_imports(module_name: str) -> None:
    """Runs on every selection, so a fixed module has to come off the list."""
    success, stderr = _import_in_fresh_process(module_name)
    assert success, stderr


@pytest.mark.parametrize("module_name", sorted(_KNOWN_BROKEN))
def test_known_broken_entry_is_a_real_file(module_name: str) -> None:
    """A deleted or renamed module would otherwise stay "broken" on the list forever."""
    assert (_SRC / (module_name.replace(".", "/") + ".py")).is_file()


def _write_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, body: str) -> str:
    (tmp_path / f"{name}.py").write_text(body)
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


@pytest.mark.parametrize(
    "body",
    [
        "import cohezion.no_such_module_smoke",
        "from json import no_such_name_smoke",
        "import json.no_such_submodule_smoke",
        "raise ValueError('broken at import')",
        "def broken(:\n    pass",
    ],
    ids=[
        "internal-module",
        "name-from-installed",
        "submodule-of-installed",
        "runtime-error",
        "syntax-error",
    ],
)
def test_check_import_fails_real_defects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, body: str
) -> None:
    name = "smoke_fixture_" + request.node.callspec.id.replace("-", "_")
    status, detail = _check_import(_write_module(tmp_path, monkeypatch, name, body))
    assert status == "fail", detail


def test_check_import_fails_script_style_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "smoke_scripts"
    scripts.mkdir()
    (scripts / "smoke_sibling.py").write_text("")
    (scripts / "smoke_script.py").write_text("import smoke_sibling")
    monkeypatch.syspath_prepend(str(tmp_path))
    status, detail = _check_import("smoke_scripts.smoke_script")
    assert status == "fail", detail


def test_fresh_process_imports_this_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = f"import cohezion\nassert cohezion.__file__.startswith({str(_SRC)!r}), cohezion.__file__"
    name = _write_module(tmp_path, monkeypatch, "smoke_fixture_tree", body)
    success, stderr = _import_in_fresh_process(name)
    assert success, stderr


def test_check_import_skips_absent_third_party(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = _write_module(
        tmp_path, monkeypatch, "smoke_fixture_absent", "import absent_package_smoke"
    )
    assert _check_import(name) == (
        "skip",
        "third-party package absent_package_smoke is not installed",
    )


def test_check_import_clears_failure_caused_by_test_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "import sys\nassert 'smoke_poison' not in sys.modules"
    name = _write_module(tmp_path, monkeypatch, "smoke_fixture_order", body)
    monkeypatch.setitem(sys.modules, "smoke_poison", object())
    assert _check_import(name) == ("ok", "")
