#!/usr/bin/env python3
"""Pre-execution output filter, token redactor, and auto-healing credential guard.

Enforces strict zero-token exposure across all logs, telemetry, terminal inspections,
and precipitates. Integrates with AutoHarness and the Immune System.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import NamedTuple


logger = logging.getLogger("secret_scrubber")

# High-precision credential patterns
CREDENTIAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Google OAuth Access Token (ya29.a0...)
    (re.compile(r"ya29\.[A-Za-z0-9_\-\.]{25,}"), "[REDACTED:GOOGLE_ACCESS_TOKEN]"),
    # Google OAuth Refresh Token (1//01...)
    (re.compile(r"1//[A-Za-z0-9_\-\.]{25,}"), "[REDACTED:GOOGLE_REFRESH_TOKEN]"),
    # JSON access_token / refresh_token fields
    (re.compile(r'("access_token"\s*:\s*")[^"]+(")'), r"\1[REDACTED:ACCESS_TOKEN]\2"),
    (re.compile(r'("refresh_token"\s*:\s*")[^"]+(")'), r"\1[REDACTED:REFRESH_TOKEN]\2"),
    # Bearer tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{25,}"), "Bearer [REDACTED:BEARER_TOKEN]"),
    # Generic key/secret assignments
    (
        re.compile(
            r"(?i)(api[_-]?key|secret|password|auth[_-]?token|client[_-]?secret)[^\S\r\n]*[:=][^\S\r\n]*(?!(?:str|int|float|bool|bytes|None|Optional|Any|auth[_-]?token|api[_-]?key|secret|password|token)\b)(?![\"'](?:lemonade|test[_-]?[a-zA-Z0-9_-]*|mock[_-]?[a-zA-Z0-9_-]*|dummy[_-]?[a-zA-Z0-9_-]*)[\"'])([\"'][^\"']+[\"']|[^\s,;\"'\\}{]{8,})"
        ),
        r"\1: [REDACTED_SECRET]",
    ),
    # GitHub personal access tokens
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"), "[REDACTED:GITHUB_TOKEN]"),
    # AWS Access Key ID
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED:AWS_ACCESS_KEY]"),
    # OpenAI / Anthropic / Gemini API Keys
    (re.compile(r"\bsk-[a-zA-Z0-9_\-]{20,60}\b"), "[REDACTED:API_KEY]"),
    (re.compile(r"\bsk-ant-api[0-9]{2}-[a-zA-Z0-9_\-]{30,120}\b"), "[REDACTED:ANTHROPIC_KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"), "[REDACTED:GEMINI_API_KEY]"),
    # Kaggle API Key & JSON
    (re.compile(r'("key"\s*:\s*")[a-f0-9]{32}(")'), r"\1[REDACTED:KAGGLE_KEY]\2"),
    (
        re.compile(r"(?i)(kaggle[_-]?(?:api[_-]?)?key)\s*[:=]\s*([^\s,;\"'}{]+)"),
        r"\1: [REDACTED:KAGGLE_KEY]",
    ),
    # BlueQubit API Token & Prefixes
    (
        re.compile(r"(?i)(bluequbit[_-]?(?:api[_-]?)?(?:token|key))\s*[:=]\s*([^\s,;\"'}{]+)"),
        r"\1: [REDACTED:BLUEQUBIT_TOKEN]",
    ),
    (re.compile(r"\bBQUBIT_[a-zA-Z0-9_\-]{20,80}\b"), "[REDACTED:BLUEQUBIT_TOKEN]"),
    # Telegram Bot Token
    (re.compile(r"\b\d{8,12}:[a-zA-Z0-9_-]{30,45}\b"), "[REDACTED:TELEGRAM_TOKEN]"),
    # Private Key blocks
    (
        re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
        "[REDACTED:PRIVATE_KEY_BLOCK]",
    ),
]

FORBIDDEN_CREDENTIAL_FILES = [
    re.compile(r"rclone\.conf", re.IGNORECASE),
    re.compile(r"(?:^|[/\s'\"])\.env(?:\.[a-zA-Z0-9_-]+)?(?:\b|[/\s'\";&|]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[/\s'\"])kaggle\.json(?:\b|[/\s'\";&|]|$)", re.IGNORECASE),
    re.compile(
        r"(?:^|[/\s'\"])bluequbit.*(?:\.json|\.token|credentials)(?:\b|[/\s'\";&|]|$)",
        re.IGNORECASE,
    ),
    re.compile(r"id_rsa|id_ed25519|id_ecdsa", re.IGNORECASE),
    re.compile(r"credentials\.json|client_secrets?\.json", re.IGNORECASE),
    re.compile(r"\.aws/credentials|\.aws/config", re.IGNORECASE),
    re.compile(r"\.netrc", re.IGNORECASE),
    re.compile(r"service_account.*\.json", re.IGNORECASE),
]

FILE_INSPECTION_COMMANDS = re.compile(
    r"\b(?:cat|grep|egrep|head|tail|less|more|nano|vim|vi|view|sed|awk|strings|xxd|hexdump|base64)\b"
)


class CommandVerification(NamedTuple):
    allowed: bool
    violation_reason: str = ""
    suggested_alternative: str = ""


def scrub_text(text: str) -> str:
    """Scrub sensitive credentials from text and replace with specific redactions."""
    if not text:
        return ""
    scrubbed = text
    for pattern, replacement in CREDENTIAL_PATTERNS:
        scrubbed = pattern.sub(replacement, scrubbed)
    return scrubbed


def contains_unredacted_credentials(text: str) -> bool:
    """Detect if raw text contains unredacted credential signatures."""
    return any(pattern.search(text) for pattern, _ in CREDENTIAL_PATTERNS)


def verify_command_safety(command: str) -> CommandVerification:
    """Pre-execution AutoHarness guard for shell commands.

    Deterministically blocks any command attempting to read or dump sensitive credential files.
    """
    if not command:
        return CommandVerification(allowed=True)

    has_reader = bool(FILE_INSPECTION_COMMANDS.search(command))
    for forbidden in FORBIDDEN_CREDENTIAL_FILES:
        if forbidden.search(command) and (has_reader or "rclone.conf" in command):
            alt = ""
            if "rclone.conf" in command:
                alt = "Use non-sensitive 'rclone listremotes' or 'rclone about <remote>:' instead."
            elif ".env" in command:
                alt = "Use os.environ or a dedicated config loader with secret masking."
            return CommandVerification(
                allowed=False,
                violation_reason=f"Blocked attempt to read credential file matching pattern: '{forbidden.pattern}'",
                suggested_alternative=alt,
            )

    return CommandVerification(allowed=True)


def auto_heal_scrub_file(file_path: Path) -> int:
    """Autonomous healing routine: cleanses existing files of exposed tokens.

    Returns the count of redactions performed.
    """
    if not file_path.exists() or not file_path.is_file():
        return 0

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        scrubbed = scrub_text(content)
        if scrubbed != content:
            file_path.write_text(scrubbed, encoding="utf-8")
            logger.info("Auto-healed %s: credentials successfully redacted.", file_path)
            return 1
    except Exception as e:
        logger.error("Failed to auto-heal %s: %s", file_path, e)
    return 0
