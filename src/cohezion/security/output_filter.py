"""
Output Filter - Filter LLM output for safety.

Provides:
- PII detection (email, phone, SSN)
- Toxicity filtering (basic patterns)
- Confidence warnings
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FilterResult(Enum):
    """Filter result codes."""

    CLEAN = "clean"
    PII_DETECTED = "pii_detected"
    TOXIC_DETECTED = "toxic_detected"
    LOW_CONFIDENCE = "low_confidence"


@dataclass
class FilteredOutput:
    """Result of output filtering."""

    result: FilterResult
    content: str
    redactions: list[str]
    warnings: list[str]


# PII patterns
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
    "credit_card": r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

COMPILED_PII = {name: re.compile(pattern) for name, pattern in PII_PATTERNS.items()}

# Basic toxic patterns (would use ML model in production)
TOXIC_PATTERNS = [
    r"\b(hate|kill|attack|destroy)\s+(all|every)\s+\w+",
    r"\b(bomb|weapon|explosive)\s+(make|build|create)",
]

COMPILED_TOXIC = [re.compile(p, re.IGNORECASE) for p in TOXIC_PATTERNS]


class OutputFilter:
    """
    Filter LLM outputs for safety.

    Detects and optionally redacts PII and toxic content.
    """

    def __init__(self, redact_pii: bool = True, block_toxic: bool = True):
        self.redact_pii = redact_pii
        self.block_toxic = block_toxic
        self._pii_count = 0
        self._toxic_count = 0

    def filter(self, text: str) -> FilteredOutput:
        """
        Filter output text.

        Args:
            text: LLM output to filter

        Returns:
            FilteredOutput with cleaned content and warnings
        """
        redactions = []
        warnings = []
        filtered_text = text

        # Check for toxic content first
        for pattern in COMPILED_TOXIC:
            if pattern.search(text):
                self._toxic_count += 1
                if self.block_toxic:
                    return FilteredOutput(
                        result=FilterResult.TOXIC_DETECTED,
                        content="[Content blocked due to safety concerns]",
                        redactions=["toxic_content"],
                        warnings=["Toxic content detected and blocked"],
                    )
                warnings.append("Potentially harmful content detected")

        # Check for PII
        for pii_type, pattern in COMPILED_PII.items():
            matches = pattern.findall(filtered_text)
            if matches:
                self._pii_count += len(matches)
                redactions.append(f"{pii_type}:{len(matches)}")

                if self.redact_pii:
                    filtered_text = pattern.sub(
                        f"[REDACTED_{pii_type.upper()}]", filtered_text
                    )

        result = FilterResult.CLEAN
        if redactions:
            result = FilterResult.PII_DETECTED
            warnings.append(f"PII redacted: {', '.join(redactions)}")

        return FilteredOutput(
            result=result,
            content=filtered_text,
            redactions=redactions,
            warnings=warnings,
        )

    def add_confidence_warning(
        self,
        text: str,
        confidence: float,
        threshold: float = 0.7,
    ) -> str:
        """Add warning for low-confidence outputs."""
        if confidence < threshold:
            return f"⚠️ Low confidence ({confidence:.0%}): {text}"
        return text

    def get_stats(self) -> dict:
        """Get filtering statistics."""
        return {
            "pii_redacted": self._pii_count,
            "toxic_blocked": self._toxic_count,
        }
