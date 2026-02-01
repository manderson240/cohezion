"""Agent Security - Input validation and output filtering."""

import logging
from dataclasses import dataclass

from cohezion.security.output_filter import OutputFilter
from cohezion.security.prompt_guard import PromptGuard, ThreatLevel

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Configuration for agent security."""

    strict_mode: bool = False
    redact_pii: bool = True
    block_toxic: bool = True
    confidence_threshold: float = 0.7


@dataclass
class SecurityResult:
    """Result of security validation."""

    is_valid: bool
    threat_level: ThreatLevel
    message: str
    filtered_content: str | None = None
    matched_patterns: list[str] | None = None
    redactions: list[str] | None = None
    warnings: list[str] | None = None


class AgentSecurity:
    """Security layer for agent input validation and output filtering."""

    def __init__(self, config: SecurityConfig | None = None):
        """Initialize agent security.

        Args:
            config: Security configuration. Uses defaults if not provided.
        """
        self.config = config or SecurityConfig()
        self._prompt_guard = PromptGuard(strict_mode=self.config.strict_mode)
        self._output_filter = OutputFilter(
            redact_pii=self.config.redact_pii,
            block_toxic=self.config.block_toxic,
        )

    def validate_input(self, prompt: str) -> tuple[bool, str]:
        """Validate input prompt for security threats.

        Args:
            prompt: Input prompt to validate.

        Returns:
            Tuple of (is_valid, message).
        """
        analysis = self._prompt_guard.analyze(prompt)

        if analysis.threat_level == ThreatLevel.MALICIOUS:
            logger.warning(f"Blocked malicious input: {analysis.matched_patterns}")
            return False, f"Blocked: {analysis.recommendation}"

        if self.config.strict_mode and analysis.threat_level == ThreatLevel.SUSPICIOUS:
            logger.info(f"Suspicious input in strict mode: {analysis.matched_patterns}")
            return False, f"Blocked (strict mode): {analysis.recommendation}"

        if analysis.threat_level == ThreatLevel.SUSPICIOUS:
            logger.info(f"Suspicious input allowed: {analysis.matched_patterns}")

        return True, analysis.recommendation

    def filter_output(self, output: str, confidence: float = 1.0) -> str:
        """Filter output for safety concerns.

        Args:
            output: Output text to filter.
            confidence: Confidence score for the output (0.0 - 1.0).

        Returns:
            Filtered output string.
        """
        filtered_result = self._output_filter.filter(output)

        if filtered_result.result.value == "toxic_detected":
            logger.warning("Output blocked due to toxic content")
            return filtered_result.content

        if filtered_result.redactions:
            logger.info(f"PII redacted: {', '.join(filtered_result.redactions)}")

        if confidence < self.config.confidence_threshold:
            filtered_result.content = self._output_filter.add_confidence_warning(
                filtered_result.content,
                confidence,
                self.config.confidence_threshold,
            )
            logger.info(f"Added low confidence warning (confidence={confidence:.2f})")

        return filtered_result.content

    def get_stats(self) -> dict[str, any]:
        """Get security statistics.

        Returns:
            Dictionary with security stats from prompt guard and output filter.
        """
        return {
            "prompt_guard": self._prompt_guard.get_stats(),
            "output_filter": self._output_filter.get_stats(),
        }

    def analyze_input(self, prompt: str) -> SecurityResult:
        """Analyze input and return detailed security result.

        Args:
            prompt: Input prompt to analyze.

        Returns:
            SecurityResult with detailed analysis.
        """
        analysis = self._prompt_guard.analyze(prompt)

        is_valid = analysis.threat_level != ThreatLevel.MALICIOUS
        if self.config.strict_mode:
            is_valid = is_valid and analysis.threat_level != ThreatLevel.SUSPICIOUS

        return SecurityResult(
            is_valid=is_valid,
            threat_level=analysis.threat_level,
            message=analysis.recommendation,
            matched_patterns=analysis.matched_patterns if not is_valid else None,
        )

    def analyze_output(self, output: str, confidence: float = 1.0) -> SecurityResult:
        """Analyze output and return detailed security result.

        Args:
            output: Output text to analyze.
            confidence: Confidence score for the output (0.0 - 1.0).

        Returns:
            SecurityResult with detailed analysis.
        """
        filtered_result = self._output_filter.filter(output)

        is_valid = filtered_result.result.value != "toxic_detected"

        return SecurityResult(
            is_valid=is_valid,
            threat_level=ThreatLevel.SAFE,
            message=filtered_result.warnings[0]
            if filtered_result.warnings
            else "Clean",
            filtered_content=filtered_result.content,
            redactions=filtered_result.redactions,
            warnings=filtered_result.warnings,
        )
