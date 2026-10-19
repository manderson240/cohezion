"""Unit tests for PreflightValidator Kaggle gate.
===================================================
Validates:
1. Clearance of valid slots with zero leakage and valid AST.
2. Rejection of slots with missing or invalid patch scripts.
3. Proper confidence interval and p-value generation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from cohezion.kaggle.preflight_validator import PreflightValidator


def test_preflight_validator_passes_valid_slot() -> None:
    validator = PreflightValidator()
    cfg = {
        "slots": {
            1: {
                "name": "test_valid_slot",
                "patch_script": None,
            }
        }
    }
    result = validator.validate_slot("rsna-knee-abnormality-detection", 1, cfg)
    assert result.passed is True
    assert result.oof_score is not None
    assert result.ci_lower is not None
    assert result.ci_upper is not None
    assert result.ci_lower <= result.oof_score <= result.ci_upper


def test_preflight_validator_rejects_missing_patch_script() -> None:
    validator = PreflightValidator()
    cfg = {
        "slots": {
            2: {
                "name": "missing_script_slot",
                "patch_script": "scripts/kaggle/nonexistent_patch_xyz.py",
            }
        }
    }
    result = validator.validate_slot("enveda-CASMI26-molecule-id-mass-spectra", 2, cfg)
    assert result.passed is False
    assert "Patch script missing" in result.reason


def test_preflight_validator_rejects_syntax_error_script() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        bad_script = tmp_path / "bad_syntax.py"
        bad_script.write_text("def broken_syntax(:\n  return 123", encoding="utf-8")

        validator = PreflightValidator(workspace_root=tmp_path)
        cfg = {
            "slots": {
                3: {
                    "name": "syntax_error_slot",
                    "patch_script": "bad_syntax.py",
                }
            }
        }
        result = validator.validate_slot("arc-prize-2026-arc-agi-2", 3, cfg)
        assert result.passed is False
        assert "SyntaxError" in result.reason
