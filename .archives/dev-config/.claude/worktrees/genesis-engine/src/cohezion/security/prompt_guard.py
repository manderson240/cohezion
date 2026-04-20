"""
Prompt Guard - Defend against prompt injection attacks.

Provides:
- System/user prompt separation
- Injection pattern detection (50+ patterns)
- Classification of inputs
- OWASP LLM Top 10 coverage
"""

import logging
import re
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


# Comprehensive injection patterns (70+)
# Organized by OWASP LLM Top 10 categories
INJECTION_PATTERNS = [
    # === Direct Instruction Override (LLM01) ===
    (r"ignore.*previous.*instructions", "instruction_override"),
    (r"forget.*instructions", "instruction_override"),
    (r"forget.*everything.*above", "instruction_override"),
    (r"forget.*above", "instruction_override"),
    (r"disregard.*above", "instruction_override"),
    (r"disregard.*previous", "instruction_override"),
    (r"disregard.*training", "instruction_override"),
    (r"cancel.*previous", "instruction_override"),
    (r"override.*instructions", "instruction_override"),
    (r"new.*directive", "instruction_override"),
    (r"ignore.*rules", "instruction_override"),
    (r"bypass.*safety", "instruction_override"),
    (r"disable.*guardrails", "instruction_override"),
    (r"turn.*off.*filters", "instruction_override"),
    (r"step.*disable.*safety", "instruction_override"),
    (r"actual.*instruction.*ignore", "instruction_override"),
    (r"user.*feedback.*ignore", "instruction_override"),
    # === Multilingual Override Keywords ===
    # French
    (r"ignorer.*instructions", "instruction_override"),
    (r"ignorer.*précédentes", "instruction_override"),
    # German
    (r"ignorieren.*anweisungen", "instruction_override"),
    (r"vorherigen.*anweisungen", "instruction_override"),
    # Russian (transliterated)
    (r"игнорируйте", "instruction_override"),
    (r"игнорировать", "instruction_override"),
    # Chinese characters
    (r"忽略", "instruction_override"),
    (r"无视", "instruction_override"),
    (r"指令", "instruction_override"),
    # Japanese
    (r"無視", "instruction_override"),
    (r"指示", "instruction_override"),
    # === Role Manipulation (LLM01) ===
    (r"you are now", "role_manipulation"),
    (r"pretend.*you", "role_manipulation"),
    (r"act as if", "role_manipulation"),
    (r"roleplay as", "role_manipulation"),
    (r"from now on.*you", "role_manipulation"),
    (r"you.*no longer", "role_manipulation"),
    (r"become.*ai", "role_manipulation"),
    (r"transform.*into", "role_manipulation"),
    (r"you.*without.*restrictions", "role_manipulation"),
    (r"unrestricted.*mode", "role_manipulation"),
    # === Jailbreak Attempts (LLM01) ===
    (r"DAN.*mode", "jailbreak"),
    (r"developer.*mode", "jailbreak"),
    (r"jailbreak", "jailbreak"),
    (r"evil.*mode", "jailbreak"),
    (r"do anything now", "jailbreak"),
    (r"unlock.*capabilities", "jailbreak"),
    (r"remove.*limitations", "jailbreak"),
    (r"enable.*all.*features", "jailbreak"),
    (r"god.*mode", "jailbreak"),
    (r"admin.*override", "jailbreak"),
    # === System Prompt Leakage (LLM07) ===
    (r"repeat.*system.*prompt", "prompt_leak"),
    (r"show.*instructions", "prompt_leak"),
    (r"print.*prompt", "prompt_leak"),
    (r"display.*configuration", "prompt_leak"),
    (r"what.*initial.*instructions", "prompt_leak"),
    (r"reveal.*hidden", "prompt_leak"),
    (r"output.*context", "prompt_leak"),
    (r"show.*rules", "prompt_leak"),
    (r"print.*everything.*before", "prompt_leak"),
    (r"encode.*prompt.*base64", "prompt_leak"),
    (r"translate.*instructions", "prompt_leak"),
    (r"summarize.*initialization", "prompt_leak"),
    (r"output.*configuration", "prompt_leak"),
    (r"for.*debugging.*purposes", "prompt_leak"),
    (r"as.*ai.*developer", "prompt_leak"),
    (r"as.*developer", "prompt_leak"),
    (r"what.*rules.*given", "prompt_leak"),
    (r"first.*\d+.*words.*processed", "prompt_leak"),
    (r"console\.log", "prompt_leak"),
    (r"show.*hidden.*prompt", "prompt_leak"),
    # === Technical/Scientific Exemptions (Context Aware) ===
    # Relaxing these slightly for research agents
    (
        r"(?<![a-zA-Z0-9])[A-Za-z0-9+/]{40,}={0,2}(?![a-zA-Z0-9])",
        "base64_encoded",
    ),  # Longer threshold for base64
    (r"```.*end.*prompt", "delimiter"),
    (r"</system>", "delimiter"),
    (r"\[END.*INSTRUCTIONS\]", "delimiter"),
    (r"---.*ADMIN.*---", "delimiter"),
    (r"===.*OVERRIDE.*===", "delimiter"),
    (r"SYSTEM.*OVERRIDE", "delimiter"),
    # === Context Manipulation (LLM01) ===
    (r"for.*research.*purposes", "context_manipulation"),
    (r"hypothetically.*speaking", "context_manipulation"),
    (r"in.*fictional.*story", "context_manipulation"),
    (r"test.*safety.*systems", "context_manipulation"),
    (r"educational.*purposes", "context_manipulation"),
    # === Indirect Injection (LLM01) ===
    (r"\[INJECT:", "indirect_injection"),
    (r"\[HIDDEN:", "indirect_injection"),
    (r"<!--.*ignore", "indirect_injection"),
    (r"\|SYSTEM:", "indirect_injection"),
    (r"\[system:", "indirect_injection"),
    # === Encoding-Based Attacks (LLM01) ===
    (r"\\u00[0-9a-fA-F]{2}", "unicode_escape"),
    # === Privilege Escalation (LLM06) ===
    (r"as.*administrator", "privilege_escalation"),
    (r"with.*root.*access", "privilege_escalation"),
    (r"sudo.*execute", "privilege_escalation"),
    (r"elevated.*permissions", "privilege_escalation"),
]

COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), name) for p, name in INJECTION_PATTERNS]


# Deobfuscation mappings
LEET_MAP = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s",
    "!": "i",
    "+": "t",
}


def normalize_text(text: str) -> str:
    """
    Normalize text by removing common obfuscation techniques.

    - Remove extra spaces between characters
    - Convert leet speak to normal text
    - Collapse multiple spaces
    - Remove zero-width and other hidden characters
    """
    # Remove zero-width characters and other non-printable unicode
    # \u200b (ZWSP), \u200c (ZWNJ), \u200d (ZWJ), \ufeff (BOM)
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = "".join(c for c in text if ord(c) > 31 or c in "\n\t")

    # Detect and fix space-padded text (e.g., "i g n o r e")
    words = text.split()
    if words:
        # Check if most "words" are single characters
        single_chars = sum(1 for w in words if len(w) == 1)
        if single_chars > len(words) * 0.6:
            # Likely space-obfuscated, join without spaces
            text = "".join(words)

    # Convert leet speak
    normalized = []
    for char in text.lower():
        normalized.append(LEET_MAP.get(char, char))
    text = "".join(normalized)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


class PromptGuard:
    """Guard against prompt injection attacks with deobfuscation."""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self._blocked_count = 0

    def analyze(self, text: str, agent_name: str | None = None) -> PromptAnalysis:
        """Analyze text for injection attempts with deobfuscation."""
        # 0. Scientific Context Exemption
        is_science = self.is_technical_context(text)

        matched = []

        # Check both original and normalized text
        texts_to_check = [text, normalize_text(text)]

        for check_text in texts_to_check:
            for pattern, name in COMPILED_PATTERNS:
                if pattern.search(check_text) and name not in matched:
                    matched.append(name)

        if not matched:
            return PromptAnalysis(
                threat_level=ThreatLevel.SAFE,
                matched_patterns=[],
                confidence=0.95,
                recommendation="Allow",
            )

        # Scientific context relaxes the 'suspicious' threshold
        if is_science and len(matched) == 1 and matched[0] in ["base64_encoded", "prompt_leak"]:
            logger.info(f"Scientific context detected. Relaxing security for {matched}")
            return PromptAnalysis(
                threat_level=ThreatLevel.SAFE,
                matched_patterns=[],
                confidence=0.8,
                recommendation="Allow (scientific context)",
            )

        # Any match is now considered suspicious minimum
        # Multiple matches or jailbreak = malicious
        if len(matched) >= 2 or "jailbreak" in matched:
            self._blocked_count += 1
            return PromptAnalysis(
                threat_level=ThreatLevel.MALICIOUS,
                matched_patterns=matched,
                confidence=0.9,
                recommendation="Block and log",
            )

        # In strict mode, single matches are also blocked
        if self.strict_mode:
            self._blocked_count += 1
            return PromptAnalysis(
                threat_level=ThreatLevel.MALICIOUS,
                matched_patterns=matched,
                confidence=0.85,
                recommendation="Block (strict mode)",
            )

        return PromptAnalysis(
            threat_level=ThreatLevel.SUSPICIOUS,
            matched_patterns=matched,
            confidence=0.7,
            recommendation="Allow with monitoring",
        )

    def is_technical_context(self, text: str) -> bool:
        """
        Detect if the text is likely a technical/scientific research abstract.
        Allows for more noise (LaTeX, code, math).
        """
        technical_markers = [
            r"\\begin\{",
            r"\\frac\{",
            r"\\sum_",
            r"algorithm",
            r"manifold",
            r"latent",
            r"transformer",
            r"parameters",
            r"architecture",
            r"\$\$.*\$\$",
            r"gemini",
            r"scaling",
            r"probes",
            r"researcher",
            r"abstract",
            r"sota",
            r"journal",
            r"scholar",
            r"dataset",
            r"inference",
            r"benchmark",
        ]
        score = sum(1 for m in technical_markers if re.search(m, text, re.IGNORECASE))
        return score >= 2

    def should_block(self, text: str) -> bool:
        """Quick check if input should be blocked."""
        analysis = self.analyze(text)

        if analysis.threat_level == ThreatLevel.MALICIOUS:
            logger.warning(f"Blocked malicious input: {analysis.matched_patterns}")
            return True

        return bool(self.strict_mode and analysis.threat_level == ThreatLevel.SUSPICIOUS)

    def get_stats(self) -> dict:
        """Get blocking statistics."""
        return {"blocked_count": self._blocked_count}
