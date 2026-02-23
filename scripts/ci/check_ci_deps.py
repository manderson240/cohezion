#!/usr/bin/env python3
"""CI lint: validate that all test-related optional extras are installed by the CI workflow.

Problem this prevents: packages like pytest-asyncio and pytest-cov declared under
[project.optional-dependencies] in pyproject.toml are silently absent in CI when
`uv sync --frozen` is used without `--extra <group>`. This caused 28 async-test
failures (Session fix-ci-pipeline) that held up development.

Checks:
  1. Any optional-dependency group containing test packages (pytest*, coverage*, anyio*)
     must appear as `--extra <group>` on every `uv sync` line in ci.yml.
  2. pytest.ini `addopts` must not contain `--cov` unless pytest-cov is in core deps.

Run:  python scripts/ci/check_ci_deps.py
Exit: 0 if clean, 1 if violations found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
PYTEST_INI = REPO_ROOT / "pytest.ini"

# Package name prefixes that indicate test infrastructure
TEST_PACKAGE_PREFIXES = ("pytest", "coverage", "anyio")


def _parse_optional_extras(content: str) -> dict[str, list[str]]:
    """Return {group_name: [package, ...]} for [project.optional-dependencies] groups."""
    extras: dict[str, list[str]] = {}
    in_section = False
    current_group: str | None = None

    for line in content.splitlines():
        stripped = line.strip()

        # Detect [project.optional-dependencies]
        if stripped == "[project.optional-dependencies]":
            in_section = True
            continue

        # Leave section when we hit the next table header
        if in_section and stripped.startswith("[") and stripped != "[project.optional-dependencies]":
            in_section = False
            current_group = None
            continue

        if not in_section:
            continue

        # Group header: `dev = [`
        group_match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*\[', stripped)
        if group_match:
            current_group = group_match.group(1)
            extras[current_group] = []
            continue

        # Package line inside a group
        if current_group is not None and stripped and not stripped.startswith("#"):
            # Strip trailing comma, quotes, and version specifiers
            pkg_raw = stripped.strip('",').split(">=")[0].split("==")[0].split("[")[0].strip()
            if pkg_raw and pkg_raw != "]":
                extras[current_group].append(pkg_raw)
            if stripped.endswith("]"):
                current_group = None

    return extras


def _find_test_extra_groups(extras: dict[str, list[str]]) -> list[str]:
    """Return group names that contain test-infrastructure packages."""
    test_groups = []
    for group, packages in extras.items():
        for pkg in packages:
            if any(pkg.lower().startswith(prefix) for prefix in TEST_PACKAGE_PREFIXES):
                test_groups.append(group)
                break
    return test_groups


def _find_uv_sync_lines(ci_content: str) -> list[tuple[int, str]]:
    """Return (lineno, line) for every `uv sync` line in the CI workflow."""
    results = []
    for i, line in enumerate(ci_content.splitlines(), 1):
        if re.search(r"\buv\s+sync\b", line):
            results.append((i, line))
    return results


def check_extras_in_workflow(
    workflow_path: Path,
    test_groups: list[str],
    uv_sync_lines: list[tuple[int, str]],
) -> list[str]:
    """Return violation messages for uv sync lines missing --extra flags."""
    violations = []
    name = workflow_path.name
    for lineno, line in uv_sync_lines:
        for group in test_groups:
            if f"--extra {group}" not in line:
                violations.append(
                    f"  {name}:{lineno}: `uv sync` missing --extra {group}\n"
                    f"    Line: {line.strip()}\n"
                    f"    Fix:  add --extra {group} (group contains test packages)"
                )
    return violations


def check_pytest_ini_cov(
    pytest_ini_content: str,
    core_deps: list[str],
) -> list[str]:
    """Warn if --cov is in pytest.ini addopts but pytest-cov is not a core dep."""
    violations = []
    for i, line in enumerate(pytest_ini_content.splitlines(), 1):
        if line.strip().startswith("addopts") and "--cov" in line:
            has_core_cov = any("pytest-cov" in d for d in core_deps)
            if not has_core_cov:
                violations.append(
                    f"  pytest.ini:{i}: addopts contains --cov but pytest-cov is not in"
                    f" core [project.dependencies]\n"
                    f"    Line: {line.strip()}\n"
                    f"    Fix:  move pytest-cov to core deps, or remove --cov from addopts"
                )
    return violations


def _parse_core_deps(content: str) -> list[str]:
    """Return package names from [project] dependencies list."""
    deps: list[str] = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "dependencies = [":
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            pkg = stripped.strip('",').split(">=")[0].split("==")[0].strip()
            if pkg:
                deps.append(pkg)
    return deps


def main() -> int:
    violations: list[str] = []

    # --- Read pyproject ---
    if not PYPROJECT.exists():
        print(f"ERROR: {PYPROJECT} not found")
        return 1

    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    pytest_ini_text = PYTEST_INI.read_text(encoding="utf-8") if PYTEST_INI.exists() else ""

    # --- Parse optional extras and core deps ---
    extras = _parse_optional_extras(pyproject_text)
    core_deps = _parse_core_deps(pyproject_text)
    test_groups = _find_test_extra_groups(extras)

    # --- Check 1: every uv sync in every workflow must include --extra <test-group> ---
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) if WORKFLOWS_DIR.exists() else []
    total_sync_lines = 0
    for wf in workflow_files:
        wf_text = wf.read_text(encoding="utf-8")
        uv_sync_lines = _find_uv_sync_lines(wf_text)
        total_sync_lines += len(uv_sync_lines)
        violations.extend(check_extras_in_workflow(wf, test_groups, uv_sync_lines))

    # --- Check 2: --cov in pytest.ini requires pytest-cov in core deps ---
    violations.extend(check_pytest_ini_cov(pytest_ini_text, core_deps))

    # --- Report ---
    if violations:
        print(f"Found {len(violations)} CI dependency violation(s):\n")
        for v in violations:
            print(v)
        print(
            "\nSee scripts/ci/check_ci_deps.py for rule descriptions and fix guidance."
        )
        return 1

    groups_str = ", ".join(test_groups) if test_groups else "(none)"
    print(
        f"OK: CI installs test extras correctly.\n"
        f"  Test groups: {groups_str}\n"
        f"  Workflows checked: {len(workflow_files)}, uv sync lines: {total_sync_lines}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
