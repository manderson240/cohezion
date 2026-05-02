"""TDD enforcement tests for repository health.

These tests define the expected state of the repository.
They should fail initially (documenting current state),
then pass as fixes are applied.
"""

import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestCriticalLintErrors:
    """Critical lint errors that could cause runtime failures."""

    @pytest.mark.fast
    def test_no_bare_except_clauses(self):
        """E722: Bare except clauses are dangerous - catch specific exceptions."""
        result = subprocess.run(
            ["ruff", "check", "--select", "E722", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bare except clauses found:\n{result.stdout}"

    @pytest.mark.fast
    def test_no_undefined_names(self):
        """F821: Undefined names will cause NameError at runtime."""
        result = subprocess.run(
            ["ruff", "check", "--select", "F821", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Undefined names found:\n{result.stdout}"

    @pytest.mark.fast
    def test_no_import_star_undefined(self):
        """F405: from X import * may hide undefined names."""
        result = subprocess.run(
            ["ruff", "check", "--select", "F405", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Import star issues found:\n{result.stdout}"


class TestHighPriorityStyle:
    """High priority style issues affecting code quality."""

    @pytest.mark.fast
    def test_core_modules_line_length(self):
        """E501: Core modules must respect 100 character limit."""
        core_path = PROJECT_ROOT / "src" / "cohezion"
        result = subprocess.run(
            ["ruff", "check", "--select", "E501", str(core_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Line too long in core modules:\n{result.stdout}"

    @pytest.mark.fast
    def test_no_implicit_optional(self):
        """RUF013: PEP 484 requires explicit Optional[T] instead of implicit."""
        result = subprocess.run(
            ["ruff", "check", "--select", "RUF013", "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Implicit Optional found:\n{result.stdout}"


class TestImportOrganization:
    """Import organization and unused import detection."""

    @pytest.mark.fast
    def test_imports_sorted_in_core(self):
        """I001: Imports should be sorted in core modules."""
        core_path = PROJECT_ROOT / "src" / "cohezion"
        result = subprocess.run(
            ["ruff", "check", "--select", "I001", str(core_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Unsorted imports in core:\n{result.stdout}"

    @pytest.mark.fast
    def test_no_unused_imports_in_core(self):
        """F401: No unused imports in core modules."""
        core_path = PROJECT_ROOT / "src" / "cohezion"
        result = subprocess.run(
            ["ruff", "check", "--select", "F401", str(core_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Unused imports in core:\n{result.stdout}"


class TestSubmoduleHealth:
    """Submodule synchronization and health."""

    @pytest.mark.fast
    def test_submodule_clean(self):
        """anthropic-delivery submodule should be clean."""
        submodule_path = PROJECT_ROOT / "anthropic-delivery"
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=submodule_path,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", f"Submodule has uncommitted changes:\n{result.stdout}"


class TestDocumentation:
    """Documentation completeness checks."""

    @pytest.mark.fast
    def test_repo_health_documentation_exists(self):
        """Repo health documentation should exist."""
        docs_path = PROJECT_ROOT / "_bmad" / "docs" / "repo_health"
        assert docs_path.exists(), "Repo health documentation directory missing"

    @pytest.mark.fast
    def test_lint_patterns_database_exists(self):
        """Lint patterns database should exist for learning."""
        db_path = PROJECT_ROOT / "_bmad" / "docs" / "repo_health" / "lint_patterns.md"
        assert db_path.exists(), "Lint patterns database missing"
