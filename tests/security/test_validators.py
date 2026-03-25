"""Tests for security/validators.py.

Covers input/output validation rules and safety checks.
"""

from __future__ import annotations

from cohezion.security.validators import (
    ValidationResult,
    sanitize_text,
    validate_input,
    validate_json_field,
)


def test_validate_input_basic():
    """[P0] Should allow clean input."""
    result = validate_input("Hello, this is a normal query.")
    assert result is None

def test_validate_input_empty():
    """[P0] Should reject empty input."""
    result = validate_input("")
    assert result.code == ValidationResult.EMPTY
    assert "cannot be empty" in result.message

def test_validate_input_too_long():
    """[P0] Should reject long input."""
    result = validate_input("a" * 20, max_length=10)
    assert result.code == ValidationResult.TOO_LONG

def test_validate_input_sql_injection():
    """[P0] Should detect SQL injection patterns."""
    result = validate_input("SELECT * FROM users; DROP TABLE students;")
    assert result.code == ValidationResult.BLOCKED_PATTERN

def test_validate_input_path_traversal():
    """[P0] Should detect path traversal."""
    result = validate_input("../../../etc/passwd")
    assert result.code == ValidationResult.BLOCKED_PATTERN

def test_sanitize_text():
    """[P0] Should normalize and clean text."""
    text = "Line 1\n\n\nLine 2    with spaces"
    sanitized = sanitize_text(text)
    assert sanitized == "Line 1\n\nLine 2 with spaces"

def test_validate_json_field():
    """[P0] Should validate field type."""
    # Success
    assert validate_json_field(123, "age", int) is None
    # Failure
    result = validate_json_field("not-int", "age", int)
    assert result.code == ValidationResult.INVALID_CHARS
