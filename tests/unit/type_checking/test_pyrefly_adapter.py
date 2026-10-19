"""Unit tests for Pyrefly Type Checking Adapter (Google/Meta Adoption, arXiv/Blog 2026)."""

from pathlib import Path

import pytest

from cohezion.type_checking.pyrefly_adapter import (
    PyreflyAdapter,
    PyreflyDiagnostic,
)


@pytest.fixture
def adapter() -> PyreflyAdapter:
    return PyreflyAdapter()


class TestPyreflyAdapter:
    def test_availability(self, adapter: PyreflyAdapter) -> None:
        # Pyrefly is installed in our virtual environment
        assert adapter.is_available() is True

    def test_check_snippet_valid_code(self, adapter: PyreflyAdapter) -> None:
        valid_snippet = "def add(a: int, b: int) -> int: return a + b\nres: int = add(1, 2)"
        result = adapter.check_snippet(valid_snippet)
        assert result.returncode == 0
        assert result.passed is True
        assert result.errors_count == 0
        assert len(result.diagnostics) == 0

    def test_check_snippet_unsound_union_google_example(self, adapter: PyreflyAdapter) -> None:
        # The exact Google blog example demonstrating Pyrefly's sound union checking
        snippet = "def process_id(x: int) -> None: pass\nval: int | None = None\nprocess_id(val)"
        result = adapter.check_snippet(snippet)
        assert result.passed is False
        assert result.errors_count >= 1

        diag = result.diagnostics[0]
        assert diag.severity == "ERROR"
        assert diag.error_code == "bad-argument-type"
        assert "not assignable to parameter `x` with type `int`" in diag.message
        assert diag.suggestion is not None
        assert "Consider narrowing the value with an `is not None` check" in diag.suggestion

    def test_parse_diagnostics_raw_block(self, adapter: PyreflyAdapter) -> None:
        raw_output = """
ERROR Argument `int | None` is not assignable to parameter `x` with type `int` in function `process_id` [bad-argument-type]
 --> foo.py:8:12
  |
8 | process_id(val)
  |            ^^^
  The declared type does not allow `None`. Consider narrowing the value with an `is not None` check.
 INFO 1 error
"""
        diags = adapter.parse_diagnostics(raw_output)
        assert len(diags) == 1
        d = diags[0]
        assert d.file == "foo.py"
        assert d.line == 8
        assert d.column == 12
        assert d.severity == "ERROR"
        assert d.error_code == "bad-argument-type"
        assert "process_id(val)" in (d.offending_code or "")
        assert d.suggestion == "Consider narrowing the value with an `is not None` check."

    def test_generate_remediation_prompt(self, adapter: PyreflyAdapter) -> None:
        diag = PyreflyDiagnostic(
            file="service.py",
            line=42,
            column=10,
            severity="ERROR",
            error_code="bad-argument-type",
            message="Argument `str | None` cannot be passed to `str`",
            offending_code="clean_name(user_input)",
            suggestion="Consider narrowing with `if user_input is not None:`",
        )
        prompt = adapter.generate_remediation_prompt(diag)
        assert "service.py:42:10" in prompt
        assert "bad-argument-type" in prompt
        assert "clean_name(user_input)" in prompt
        assert "Consider narrowing with `if user_input is not None:`" in prompt

    def test_check_files_on_self(self, adapter: PyreflyAdapter) -> None:
        self_path = Path("src/cohezion/type_checking/pyrefly_adapter.py")
        result = adapter.check_files([self_path])
        assert result.passed is True
        assert result.errors_count == 0
        assert result.duration_ms >= 0.0

    def test_diagnostic_serialization(self) -> None:
        diag = PyreflyDiagnostic(
            file="test.py",
            line=1,
            column=2,
            severity="WARNING",
            error_code="missing-import",
            message="Module missing",
        )
        data = diag.to_dict()
        assert data["file"] == "test.py"
        assert data["severity"] == "WARNING"
        assert data["error_code"] == "missing-import"
