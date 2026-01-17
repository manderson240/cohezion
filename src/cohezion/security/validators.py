"""
Input Validation and Sanitization.

Provides:
- Query length limits
- Blocked pattern detection (SQL injection, path traversal)
- Unicode normalization
- Content type validation
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """Validation result codes."""
    VALID = "valid"
    TOO_LONG = "too_long"
    BLOCKED_PATTERN = "blocked_pattern"
    INVALID_CHARS = "invalid_chars"
    EMPTY = "empty"


@dataclass
class ValidationError:
    """Validation error details."""
    code: ValidationResult
    message: str
    field: str = ""


# Configuration
MAX_QUERY_LENGTH = 10000
MAX_FIELD_LENGTH = 1000

# Blocked patterns (SQL injection, path traversal, etc.)
BLOCKED_PATTERNS = [
    r";\s*DROP\s+TABLE",
    r";\s*DELETE\s+FROM",
    r"UNION\s+SELECT",
    r"--\s*$",
    r"\.\./",
    r"\.\.\\",
    r"<script>",
    r"javascript:",
    r"data:text/html",
    r"onclick=",
    r"onerror=",
]

BLOCKED_REGEX = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


def validate_input(
    text: str,
    field_name: str = "input",
    max_length: int = MAX_QUERY_LENGTH,
) -> ValidationError | None:
    """
    Validate input text.
    
    Args:
        text: Input to validate
        field_name: Name of field for error messages
        max_length: Maximum allowed length
        
    Returns:
        ValidationError if invalid, None if valid
    """
    if not text or not text.strip():
        return ValidationError(
            code=ValidationResult.EMPTY,
            message=f"{field_name} cannot be empty",
            field=field_name,
        )
    
    if len(text) > max_length:
        return ValidationError(
            code=ValidationResult.TOO_LONG,
            message=f"{field_name} exceeds maximum length of {max_length}",
            field=field_name,
        )
    
    # Check for blocked patterns
    for pattern in BLOCKED_REGEX:
        if pattern.search(text):
            return ValidationError(
                code=ValidationResult.BLOCKED_PATTERN,
                message=f"Potentially malicious content detected in {field_name}",
                field=field_name,
            )
    
    return None


def sanitize_text(text: str) -> str:
    """
    Sanitize text for safe processing.
    
    - Normalize Unicode
    - Strip control characters
    - Collapse whitespace
    
    Args:
        text: Raw input text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Normalize Unicode (NFC form)
    text = unicodedata.normalize("NFC", text)
    
    # Remove control characters except newlines and tabs
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Cc" or c in "\n\t"
    )
    
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()


def validate_json_field(
    value: str | int | float | None,
    field_name: str,
    expected_type: type,
    required: bool = True,
) -> ValidationError | None:
    """Validate a JSON field type."""
    if value is None:
        if required:
            return ValidationError(
                code=ValidationResult.EMPTY,
                message=f"{field_name} is required",
                field=field_name,
            )
        return None
    
    if not isinstance(value, expected_type):
        return ValidationError(
            code=ValidationResult.INVALID_CHARS,
            message=f"{field_name} must be {expected_type.__name__}",
            field=field_name,
        )
    
    return None
