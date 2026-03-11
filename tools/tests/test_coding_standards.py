"""
Test suite for coding standards infrastructure.

Validates that linting, formatting, and type checking tools are properly configured
and enforce project standards across all Python components.

Tests follow TDD approach - defining expected behavior before implementation.
"""

import subprocess
import sys
from pathlib import Path
import pytest

# Root paths for each Python component
VAULT_ROOT = Path(__file__).parent.parent.parent
COHEZION_ENGINE = VAULT_ROOT / "tools" / "cohezion-engine"
MCP_SERVER = VAULT_ROOT / "mcp-server"
RESEARCH = VAULT_ROOT / "research"
TOOLS_VAULT_LINKER = VAULT_ROOT / "tools" / "vault_linker"

# Python interpreter from venv
VENV_PYTHON = Path("/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3")


class TestRuffConfiguration:
    """Test ruff linting and formatting configuration."""

    def test_ruff_config_exists_cohezion_engine(self):
        """Verify pyproject.toml has ruff configuration."""
        config_file = COHEZION_ENGINE / "pyproject.toml"
        assert config_file.exists(), "pyproject.toml should exist"
        content = config_file.read_text()
        assert "[tool.ruff]" in content, "Should have [tool.ruff] section"

    def test_ruff_config_exists_mcp_server(self):
        """Verify mcp-server has ruff configuration."""
        config_file = MCP_SERVER / "pyproject.toml"
        assert config_file.exists(), "pyproject.toml should exist"
        content = config_file.read_text()
        assert "[tool.ruff]" in content, "Should have [tool.ruff] section"

    def test_ruff_lint_passes_cohezion_engine(self):
        """Ruff linting should pass on cohezion-engine."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "ruff", "check", "src/", "tests/"],
            cwd=COHEZION_ENGINE,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff should pass:\n{result.stdout}\n{result.stderr}"
        )

    def test_ruff_lint_passes_mcp_server(self):
        """Ruff linting should pass on mcp-server."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "ruff", "check", "."],
            cwd=MCP_SERVER,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff should pass:\n{result.stdout}\n{result.stderr}"
        )

    def test_ruff_lint_passes_research(self):
        """Ruff linting should pass on research component."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "ruff", "check", "."],
            cwd=RESEARCH,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff should pass:\n{result.stdout}\n{result.stderr}"
        )

    def test_ruff_format_check_passes_cohezion_engine(self):
        """Ruff formatting check should pass on cohezion-engine."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "ruff", "format", "--check", "src/", "tests/"],
            cwd=COHEZION_ENGINE,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff format should pass:\n{result.stdout}\n{result.stderr}"
        )

    def test_ruff_format_check_passes_mcp_server(self):
        """Ruff formatting check should pass on mcp-server."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "ruff", "format", "--check", "."],
            cwd=MCP_SERVER,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Ruff format should pass:\n{result.stdout}\n{result.stderr}"
        )


class TestMypyConfiguration:
    """Test mypy type checking configuration."""

    def test_mypy_config_exists_mcp_server(self):
        """Verify mcp-server has mypy configuration."""
        config_file = MCP_SERVER / "pyproject.toml"
        content = config_file.read_text()
        assert "[tool.mypy]" in content, "Should have [tool.mypy] section"

    def test_mypy_passes_mcp_server(self):
        """Mypy type checking should pass on mcp-server."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "mypy", "kyutai_mcp/"],
            cwd=MCP_SERVER,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Mypy should pass:\n{result.stdout}\n{result.stderr}"
        )


class TestPreCommitConfiguration:
    """Test pre-commit hook configuration."""

    def test_precommit_config_exists(self):
        """Verify .pre-commit-config.yaml exists at repo root."""
        config_file = VAULT_ROOT / ".pre-commit-config.yaml"
        assert config_file.exists(), ".pre-commit-config.yaml should exist at repo root"

    def test_precommit_config_has_python_hooks(self):
        """Pre-commit config should include Python linting and formatting hooks."""
        config_file = VAULT_ROOT / ".pre-commit-config.yaml"
        content = config_file.read_text()
        assert "ruff" in content.lower(), "Should include ruff hook"
        assert "pre-commit-hooks" in content, "Should include pre-commit-hooks"

    def test_precommit_installed(self):
        """Pre-commit should be installed in venv."""
        result = subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "show", "pre-commit"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "pre-commit should be installed"


class TestCIConfiguration:
    """Test GitHub Actions CI configuration."""

    def test_ci_workflow_exists(self):
        """Verify GitHub Actions workflow exists."""
        workflow_file = VAULT_ROOT / ".github" / "workflows" / "ci.yaml"
        assert workflow_file.exists(), "ci.yaml workflow should exist"

    def test_ci_workflow_valid_yaml(self):
        """CI workflow should be valid YAML."""
        import yaml

        workflow_file = VAULT_ROOT / ".github" / "workflows" / "ci.yaml"
        content = workflow_file.read_text()
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in ci.yaml: {e}")

    def test_ci_runs_ruff(self):
        """CI workflow should run ruff linting."""
        workflow_file = VAULT_ROOT / ".github" / "workflows" / "ci.yaml"
        content = workflow_file.read_text()
        assert "ruff" in content.lower(), "CI should run ruff"

    def test_ci_runs_tests(self):
        """CI workflow should run pytest."""
        workflow_file = VAULT_ROOT / ".github" / "workflows" / "ci.yaml"
        content = workflow_file.read_text()
        assert "pytest" in content.lower(), "CI should run pytest"


class TestToxConfiguration:
    """Test tox multi-environment configuration."""

    def test_tox_ini_exists(self):
        """Verify tox.ini exists at repo root."""
        tox_file = VAULT_ROOT / "tox.ini"
        assert tox_file.exists(), "tox.ini should exist"

    def test_tox_has_lint_env(self):
        """Tox should have lint environment."""
        tox_file = VAULT_ROOT / "tox.ini"
        content = tox_file.read_text()
        assert "[testenv:lint]" in content, "Should have [testenv:lint] section"

    def test_tox_has_type_env(self):
        """Tox should have type checking environment."""
        tox_file = VAULT_ROOT / "tox.ini"
        content = tox_file.read_text()
        assert "[testenv:type]" in content, "Should have [testenv:type] section"


class TestConsistency:
    """Test consistency across components."""

    def test_all_components_have_ruff_config(self):
        """All Python components should have ruff configuration."""
        components = [
            COHEZION_ENGINE / "pyproject.toml",
            MCP_SERVER / "pyproject.toml",
        ]
        for config_file in components:
            if config_file.exists():
                content = config_file.read_text()
                assert "[tool.ruff]" in content, (
                    f"{config_file} should have ruff config"
                )

    def test_line_length_consistency(self):
        """Line length should be consistent across configurations."""
        # Check mcp-server config
        mcp_config = MCP_SERVER / "pyproject.toml"
        content = mcp_config.read_text()
        assert "line-length = 100" in content, "MCP server should use line-length = 100"

        # Check cohezion-engine config
        engine_config = COHEZION_ENGINE / "pyproject.toml"
        content = engine_config.read_text()
        assert "line-length = 100" in content, (
            "Cohezion engine should use line-length = 100"
        )
