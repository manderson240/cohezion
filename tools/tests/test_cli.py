"""Tests for the CLI interface."""

import sys
import pytest
from pathlib import Path
import subprocess


def test_cli_analyze_mode(tmp_path):
    """Test CLI analyze mode produces report."""
    # Create minimal vault
    (tmp_path / "paper1.md").write_text("""---
title: Paper 1
tags: null
---
# Paper 1
References [[missing-concept]].
""")

    # Run analyze mode (run from tools directory)
    result = subprocess.run(
        [sys.executable, "-m", "vault_linker", "analyze", "--vault-path", str(tmp_path)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Vault Health Report" in result.stdout or "analysis" in result.stdout.lower()


def test_cli_fix_dry_run(tmp_path):
    """Test CLI fix mode with --dry-run."""
    # Create vault with fixable issues
    (tmp_path / "paper1.md").write_text("""---
title: Paper 1
tags: null
---
# Paper 1
""")

    # Run fix with dry-run
    result = subprocess.run(
        [sys.executable, "-m", "vault_linker", "fix", "--vault-path", str(tmp_path), "--dry-run"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "dry" in result.stdout.lower() or "preview" in result.stdout.lower()

    # File should NOT be modified
    content = (tmp_path / "paper1.md").read_text()
    assert "tags: null" in content


def test_cli_help():
    """Test CLI help message."""
    result = subprocess.run(
        [sys.executable, "-m", "vault_linker", "--help"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "analyze" in result.stdout
    assert "fix" in result.stdout
