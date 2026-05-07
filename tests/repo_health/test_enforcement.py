"""TDD enforcement tests for repository health.

These tests define the expected state of the repository.
They should fail initially (documenting current state),
then pass as fixes are applied.
"""

import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent
SYNC_CHECK_PATHS = ["src/cohezion/", "tests/", "scripts/"]


def _ruff_check(select: str, paths: list[str]) -> subprocess.CompletedProcess:
    """Run ruff check on specified paths (not archives)."""
    return subprocess.run(
        ["ruff", "check", "--select", select, *paths],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


class TestCriticalLintErrors:
    """Critical lint errors in active source that could cause runtime failures."""

    @pytest.mark.fast
    def test_bare_except_clauses(self):
        """E722: Bare except clauses are dangerous - catch specific exceptions."""
        result = _ruff_check("E722", SYNC_CHECK_PATHS)
        assert result.returncode == 0, (
            f"Bare except in active source:\n{result.stdout}"
        )

    @pytest.mark.fast
    def test_undefined_names(self):
        """F821: Undefined names will cause NameError at runtime."""
        result = _ruff_check("F821", SYNC_CHECK_PATHS)
        assert result.returncode == 0, (
            f"Undefined names in active source:\n{result.stdout}"
        )

    @pytest.mark.fast
    def test_import_star_undefined(self):
        """F405: from X import * may hide undefined names."""
        result = _ruff_check("F405", SYNC_CHECK_PATHS)
        assert result.returncode == 0, (
            f"Import star issues in active source:\n{result.stdout}"
        )


class TestHighPriorityStyle:
    """High priority style issues affecting code quality."""

    @pytest.mark.fast
    def test_core_modules_line_length(self):
        """E501: Core modules must respect 100 character limit."""
        result = _ruff_check("E501", ["src/cohezion/"])
        assert result.returncode == 0, (
            f"Line too long in core modules:\n{result.stdout}"
        )

    @pytest.mark.fast
    def test_implicit_optional(self):
        """RUF013: PEP 484 requires explicit Optional[T] instead of implicit."""
        result = _ruff_check("RUF013", SYNC_CHECK_PATHS)
        assert result.returncode == 0, (
            f"Implicit Optional in active source:\n{result.stdout}"
        )


class TestImportOrganization:
    """Import organization and unused import detection."""

    @pytest.mark.fast
    def test_imports_sorted_in_core(self):
        """I001: Imports should be sorted in core modules."""
        result = _ruff_check("I001", ["src/cohezion/"])
        assert result.returncode == 0, (
            f"Unsorted imports in core:\n{result.stdout}"
        )

    @pytest.mark.fast
    def test_no_unused_imports_in_core(self):
        """F401: No unused imports in core or tests."""
        result = _ruff_check("F401", ["src/cohezion/", "tests/"])
        assert result.returncode == 0, (
            f"Unused imports in core/tests:\n{result.stdout}"
        )


class TestSubmoduleHealth:
    """Submodule synchronization and health."""

    @pytest.mark.fast
    def test_submodule_clean(self):
        """anthropic-delivery submodule should be clean if present."""
        submodule_path = PROJECT_ROOT / "anthropic-delivery"
        if not submodule_path.exists():
            pytest.skip("Submodule not initialized")
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=submodule_path,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", (
            f"Submodule has uncommitted changes:\n{result.stdout}"
        )


class TestDocumentation:
    """Documentation completeness checks."""

    @pytest.mark.fast
    def test_repo_health_documentation_exists(self):
        """Repo health documentation should exist."""
        docs_path = PROJECT_ROOT / "_bmad" / "docs" / "repo_health"
        if not docs_path.parent.exists():
            pytest.skip("_bmad docs directory not present")
        assert docs_path.exists(), "Repo health documentation directory missing"

    @pytest.mark.fast
    def test_lint_patterns_database_exists(self):
        """Lint patterns database should exist for learning."""
        db_path = (
            PROJECT_ROOT / "_bmad" / "docs" / "repo_health" / "lint_patterns.md"
        )
        if not db_path.parent.exists():
            pytest.skip("_bmad docs directory not present")
        assert db_path.exists(), "Lint patterns database missing"
