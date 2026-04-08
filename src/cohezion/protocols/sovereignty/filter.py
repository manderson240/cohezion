"""Sovereignty Filter for the EcoResilience Swarm.
Provides a deterministic scrubbing layer to prevent Indigenous Traditional Ecological Knowledge (TEK)
identifiers from leaking to external cloud providers during the 'Calculation' phase.
"""

from __future__ import annotations

import logging
import re
from typing import Set, Tuple, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SovereigntyConfig(BaseModel):
    """Configuration for the Sovereignty Filter."""

    # List of sacred entities/terms that must be scrubbed
    protected_terms: Set[str] = Field(default_factory=set)
    # Mapping of sensitive terms to generic descriptors (e.g., "Sabu-Sabu" -> "Native Plant A")
    replacement_map: Dict[str, str] = Field(default_factory=dict)
    # Patterns that indicate high-precision coordinates or ritual sites
    sensitive_patterns: List[str] = Field(default_factory=list)


class SovereigntyFilter:
    """
    Deterministic scrubbing layer for TEK data privacy.
    Follows the 'Sovereignty Audit' requirements for zero-leakage.
    """

    def __init__(self, config: SovereigntyConfig):
        self.config = config
        # Compile regex for sensitive patterns for performance
        self._pattern_regex = (
            re.compile("|".join(self.config.sensitive_patterns), re.IGNORECASE)
            if self.config.sensitive_patterns
            else None
        )

    def scrub(self, text: str) -> Tuple[str, List[str]]:
        """
        Scrubs sensitive TEK data from text.
        Returns the cleaned text and a list of the terms that were scrubbed.
        """
        cleaned_text = text
        scrubbed_terms = []

        # 1. Replacement Map based scrubbing (Specific -> Generic)
        for term, replacement in self.config.replacement_map.items():
            if term.lower() in cleaned_text.lower():
                # Use case-insensitive replacement
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                cleaned_text = pattern.sub(replacement, cleaned_text)
                scrubbed_terms.append(term)

        # 2. Protected Terms scrubbing (Removal/Masking)
        for term in self.config.protected_terms:
            if term.lower() in cleaned_text.lower():
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                cleaned_text = pattern.sub("[PROTECTED_TEK]", cleaned_text)
                scrubbed_terms.append(term)

        # 3. Pattern-based scrubbing (e.g., coordinates, specific site formats)
        if self._pattern_regex:
            matches = self._pattern_regex.findall(cleaned_text)
            if matches:
                scrubbed_terms.extend(matches)
                cleaned_text = self._pattern_regex.sub("[SENSITIVE_GEODATA]", cleaned_text)

        return cleaned_text, list(set(scrubbed_terms))


# Pre-configured instance for the Sundarbans / EcoResilience baseline
baseline_config = SovereigntyConfig(
    protected_terms={"Secret Ritual Site", "Ancestral Burial Ground"},
    replacement_map={
        "Sabu-Sabu": "Indigenous Salt-Filter Plant",
        "Mangrove Heart": "Primary Ecological Node",
    },
    sensitive_patterns=[
        r"\d{1,3}\.\d{4,},\s*\d{1,3}\.\d{4,}",  # Rough coordinate patterns
    ],
)
sovereignty_filter = SovereigntyFilter(baseline_config)
