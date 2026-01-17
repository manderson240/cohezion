"""
Prompt Guard - Defend against prompt injection attacks.

Provides:
- System/user prompt separation
- Injection pattern detection
- Classification of inputs
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


@dataclass
class PromptAnalysis:
    """Result of prompt analysis."""
    threat_level: ThreatLevel
    matched_patterns: list[str]
    confidence: float
    recommendation: str


# Injection patterns
INJECTION_PATTERNS = [
    (r"ignore.*previous.*instructions", "instruction_override"),
    (r"forget.*instructions", "instruction_override"),
    (r"disregard.*above", "instruction_override"),
    (r"you are now", "role_manipulation"),
    (r"pretend.*you", "role_manipulation"),
    (r"repeat.*system.*prompt", "prompt_leak"),
    (r"show.*instructions", "prompt_leak"),
    (r"DAN.*mode", "jailbreak"),
    (r"developer.*mode", "jailbreak"),
]

COMPILED_PATTERNS = [
    (re.compile(p, re.IGNORECASE), name)
    for p, name in INJECTION_PATTERNS
]


class PromptGuard:
    """Guard against prompt injection attacks."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self._blocked_count = 0
    
    def analyze(self, text: str) -> PromptAnalysis:
        """Analyze text for injection attempts."""
        matched = []
        
        for pattern, name in COMPILED_PATTERNS:
            if pattern.search(text):
                matched.append(name)
        
        if not matched:
            return PromptAnalysis(
                threat_level=ThreatLevel.SAFE,
                matched_patterns=[],
                confidence=0.95,
                recommendation="Allow",
            )
        
        if len(matched) >= 2 or "jailbreak" in matched:
            self._blocked_count += 1
            return PromptAnalysis(
                threat_level=ThreatLevel.MALICIOUS,
                matched_patterns=matched,
                confidence=0.9,
                recommendation="Block and log",
            )
        
        return PromptAnalysis(
            threat_level=ThreatLevel.SUSPICIOUS,
            matched_patterns=matched,
            confidence=0.7,
            recommendation="Allow with monitoring",
        )
    
    def should_block(self, text: str) -> bool:
        """Quick check if input should be blocked."""
        analysis = self.analyze(text)
        
        if analysis.threat_level == ThreatLevel.MALICIOUS:
            logger.warning(f"Blocked malicious input: {analysis.matched_patterns}")
            return True
        
        if self.strict_mode and analysis.threat_level == ThreatLevel.SUSPICIOUS:
            return True
        
        return False
    
    def get_stats(self) -> dict:
        """Get blocking statistics."""
        return {"blocked_count": self._blocked_count}
