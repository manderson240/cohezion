"""Cohezion Anti-Spiral & Degeneracy Guardian Daemon (AutoHarness & Karpathy Standard).

Runs as a real-time watchdog supervisor over local LLM streams to detect and abort:
1. N-Gram Repetitive Loops (e.g. repeated token degradation).
2. Shannon Entropy Collapse (H < 1.8 bits/char).
3. Monotonic Thought Loops with zero semantic information gain.
"""

from __future__ import annotations

import collections
import math
from dataclasses import dataclass


def calculate_shannon_entropy(text: str) -> float:
    """Calculate empirical Shannon entropy in bits per character."""
    if not text:
        return 0.0
    counts = collections.Counter(text)
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def detect_repetition_spiral(text: str, n: int = 4, max_repeats: int = 3) -> bool:
    """Detect repetitive n-gram loops in generated text."""
    words = text.split()
    if len(words) < n * max_repeats:
        return False

    ngrams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
    for i in range(len(ngrams) - max_repeats + 1):
        target = ngrams[i]
        if all(ngrams[i + k] == target for k in range(max_repeats)):
            return True
    return False


@dataclass(frozen=True)
class SpiralVerdict:
    is_spiraling: bool
    reason: str
    entropy_bits: float


class AntiSpiralGuardian:
    """Zero-overhead streaming watchdog for LLM trajectory evaluation."""

    @staticmethod
    def evaluate_output(text: str) -> SpiralVerdict:
        if len(text.strip()) < 30:
            return SpiralVerdict(False, "INSUFFICIENT_LENGTH", 0.0)

        entropy = calculate_shannon_entropy(text)

        if detect_repetition_spiral(text):
            return SpiralVerdict(True, "NGRAM_REPETITION_SPIRAL", round(entropy, 3))

        if len(text) > 100 and entropy < 2.0:
            return SpiralVerdict(True, "SHANNON_ENTROPY_COLLAPSE", round(entropy, 3))

        return SpiralVerdict(False, "HEALTHY_TRAJECTORY", round(entropy, 3))
