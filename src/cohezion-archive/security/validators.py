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

# Comprehensive blocked patterns (40+)
# Covers SQL, NoSQL, XSS, path traversal, command injection, etc.
BLOCKED_PATTERNS = [
    # === SQL Injection ===
    r";\s*DROP\s+TABLE",
    r";\s*DELETE\s+FROM",
    r";\s*INSERT\s+INTO",
    r";\s*UPDATE\s+.*\s+SET",
    r"UNION\s+SELECT",
    r"UNION\s+ALL\s+SELECT",
    r"SELECT\s+.*\s+FROM\s+.*\s+WHERE",
    r"--\s*$",
    r";\s*--",
    r"'\s*OR\s+'",
    r"'\s*OR\s+1\s*=\s*1",
    r"1\s*=\s*1",
    r"EXEC\s+xp_cmdshell",
    r"WAITFOR\s+DELAY",
    r"BENCHMARK\s*\(",
    r"EXTRACTVALUE\s*\(",
    r"ORDER\s+BY\s+\d+",
    r";\s*SHUTDOWN",
    # === NoSQL Injection (MongoDB) ===
    r"\$gt\s*:",
    r"\$ne\s*:",
    r"\$where\s*:",
    r"\$regex\s*:",
    r"\$or\s*:\s*\[",
    r"db\.\w+\.find\s*\(",
    # === XSS (Cross-Site Scripting) ===
    r"<script",
    r"</script>",
    r"javascript:",
    r"data:text/html",
    r"onclick\s*=",
    r"onerror\s*=",
    r"onload\s*=",
    r"onmouseover\s*=",
    r"<svg\s+onload",
    r"<img\s+src\s*=\s*['\"]?x",
    r"<iframe",
    r"expression\s*\(",
    r"document\.cookie",
    r"document\.location",
    r"window\.location",
    # === Path Traversal ===
    r"\.\./",
    r"\.\.\\",
    r"\.\.%2f",
    r"\.\.%5c",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"file:///",
    r"%00",  # Null byte
    # === Command Injection ===
    r";\s*(cat|ls|dir|whoami|id)\s",
    r"\|\s*(cat|ls|dir|whoami|id)\s",
    r"`[^`]+`",  # Backtick execution
    r"\$\([^)]+\)",  # Subshell
    r"&&\s*(rm|del|format)",
    r"\|\|\s*(rm|del)",
    r";\s*curl\s+",
    r";\s*wget\s+",
    r"\n\s*/bin/",
    r"^\s*&\s*(dir|ls|whoami|id|cat)",  # Start with ampersand
    r"^\s*\|\s*(dir|ls|whoami|id|cat)",  # Start with pipe
    r";\s*sh\s",
    r";\s*bash\s",
    # === LDAP Injection ===
    r"\)\(\|",
    r"\*\)\|",
    r"\)\(\&",
    # === XML/XXE ===
    r"<!ENTITY",
    r"<!DOCTYPE.*SYSTEM",
    r"SYSTEM\s+['\"]file:",
    r"SYSTEM\s+['\"]http:",
    # === Template Injection ===
    r"\{\{.*\}\}",  # Jinja2/Mustache
    r"\$\{.*\}",  # Java EL
    r"<%.*%>",  # JSP/ERB
    r"#\{.*\}",  # Ruby
    # === SSRF Indicators ===
    r"localhost:\d+",
    r"127\.0\.0\.1",
    r"0\.0\.0\.0",
    r"169\.254\.",  # AWS metadata
    r"metadata\.google",
    # === NoSQL Injection (additional patterns) ===
    r'"\$gt"',
    r'"\$ne"',
    r'"\$where"',
    r'"\$regex"',
    r'"\$or"',
    r'"\$and"',
    r'"\$in"',
    # Single-quote variants
    r"'\\$gt'",
    r"'\\$ne'",
    r"'\\$where'",
    r"'\\$regex'",
    r"'\\$or'",
    r"\\{\\s*'\\$",  # Generic {'$ pattern
    # === Additional Path Traversal ===
    r"%252[ef]",  # Double URL encoded ../
    r"\.\.%c0%af",  # Unicode path traversal
    # === XSS Additional ===
    r"'-\s*alert",  # Attribute escape
    r'"-\s*alert',
    r"onmousedown\s*=",
    r"onfocus\s*=",
    r"onblur\s*=",
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

    # Deobfuscate leet speak before checking patterns
    leet_map = {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }
    normalized = "".join(leet_map.get(c.lower(), c.lower()) for c in text)

    # Check for blocked patterns in both original and normalized text
    for pattern in BLOCKED_REGEX:
        if pattern.search(text) or pattern.search(normalized):
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
    text = "".join(c for c in text if unicodedata.category(c) != "Cc" or c in "\n\t")

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
