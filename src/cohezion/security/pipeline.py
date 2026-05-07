"""Elegant simplified security guardrails.

Replaces 7,361 lines of scattered security modules with unified guardrail system.
Single responsibility: validate input/output against security policies.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto


logger = logging.getLogger(__name__)


class GuardrailAction(Enum):
    """Action to take after guardrail check."""

    ALLOW = auto()
    BLOCK = auto()
    SANITIZE = auto()
    LOG_AND_ALLOW = auto()


@dataclass
class GuardrailResult:
    """Result of guardrail check."""

    action: GuardrailAction
    reason: str = ""
    modified_input: str | None = None


@dataclass
class SecurityPolicy:
    """Security policy configuration."""

    # Input validation
    max_input_length: int = 10000
    forbidden_patterns: list[str] = None
    required_patterns: list[str] = None

    # Output validation
    max_output_length: int = 50000
    output_filters: list[str] = None

    def __post_init__(self):
        if self.forbidden_patterns is None:
            self.forbidden_patterns = []
        if self.required_patterns is None:
            self.required_patterns = []
        if self.output_filters is None:
            self.output_filters = []


class Guardrail:
    """Individual guardrail check."""

    def __init__(
        self,
        name: str,
        check_fn: Callable[[str], tuple[bool, str]],
    ):
        self.name = name
        self.check_fn = check_fn

    def check(self, text: str) -> tuple[bool, str]:
        """Run guardrail check. Returns (passed, reason)."""
        return self.check_fn(text)


class SecurityPipeline:
    """Unified security pipeline.

    Replaces 7,361 lines with ~200 lines.
    Single responsibility: validate content against security policies.
    """

    def __init__(self, policy: SecurityPolicy | None = None):
        self.policy = policy or SecurityPolicy()
        self.input_guardrails: list[Guardrail] = []
        self.output_guardrails: list[Guardrail] = []
        self._setup_default_guardrails()

    def _setup_default_guardrails(self) -> None:
        """Setup default security guardrails."""
        # Input length guardrail
        self.add_input_guardrail(
            "input_length",
            lambda text: (
                len(text) <= self.policy.max_input_length,
                f"Input exceeds max length: {len(text)} > {self.policy.max_input_length}",
            ),
        )

        # Forbidden patterns guardrail
        if self.policy.forbidden_patterns:
            self.add_input_guardrail(
                "forbidden_patterns",
                lambda text: self._check_patterns(text, self.policy.forbidden_patterns),
            )

        # Output length guardrail
        self.add_output_guardrail(
            "output_length",
            lambda text: (
                len(text) <= self.policy.max_output_length,
                f"Output exceeds max length: {len(text)} > {self.policy.max_output_length}",
            ),
        )

    def _check_patterns(self, text: str, patterns: list[str]) -> tuple[bool, str]:
        """Check if text matches any forbidden patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Matched forbidden pattern: {pattern}"
        return True, ""

    def add_input_guardrail(
        self,
        name: str,
        check_fn: Callable[[str], tuple[bool, str]],
    ) -> None:
        """Add input guardrail."""
        self.input_guardrails.append(Guardrail(name, check_fn))
        logger.debug(f"Added input guardrail: {name}")

    def add_output_guardrail(
        self,
        name: str,
        check_fn: Callable[[str], tuple[bool, str]],
    ) -> None:
        """Add output guardrail."""
        self.output_guardrails.append(Guardrail(name, check_fn))
        logger.debug(f"Added output guardrail: {name}")

    def check_input(self, text: str) -> GuardrailResult:
        """Check input against all guardrails."""
        for guardrail in self.input_guardrails:
            passed, reason = guardrail.check(text)
            if not passed:
                logger.warning(f"Input guardrail '{guardrail.name}' failed: {reason}")
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"{guardrail.name}: {reason}",
                )

        return GuardrailResult(action=GuardrailAction.ALLOW)

    def check_output(self, text: str) -> GuardrailResult:
        """Check output against all guardrails."""
        for guardrail in self.output_guardrails:
            passed, reason = guardrail.check(text)
            if not passed:
                logger.warning(f"Output guardrail '{guardrail.name}' failed: {reason}")
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"{guardrail.name}: {reason}",
                )

        return GuardrailResult(action=GuardrailAction.ALLOW)

    def sanitize(self, text: str) -> str:
        """Sanitize text by applying output filters."""
        sanitized = text
        for pattern in self.policy.output_filters:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized


class SimpleSecurity:
    """Minimal security for basic use cases."""

    def __init__(self):
        self.forbidden_words = ["password", "secret", "key", "token"]
        self.max_length = 10000

    def check(self, text: str) -> bool:
        """Simple security check."""
        if len(text) > self.max_length:
            return False

        text_lower = text.lower()
        return all(word not in text_lower for word in self.forbidden_words)

    def sanitize(self, text: str) -> str:
        """Sanitize sensitive content."""
        result = text
        for word in self.forbidden_words:
            result = result.replace(word, "[REDACTED]")
        return result
