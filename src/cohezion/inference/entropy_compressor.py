"""Step Entropy state compressor for Chain-of-Thought reasoning.

Analyzes generated reasoning steps (e.g. within `<thought>` tags) and prunes
redundant, low-entropy segments while preserving high-entropy semantic landmarks
(Semantic Anchor Compression) to fit large contexts into SLM windows.
"""

from __future__ import annotations

import collections
import math
import re


class StepEntropyCompressor:
    """Prunes low-entropy reasoning steps from Chain-of-Thought transcripts.

    Retains high-entropy decision points, corrections, and explicit landmarks.
    """

    def __init__(
        self,
        entropy_threshold: float = 3.0,
        anchor_keywords: set[str] | None = None,
    ) -> None:
        """
        Parameters
        ----------
        entropy_threshold : float
            Lines with entropy below this threshold are pruned unless they contain anchors.
        anchor_keywords : Set[str] | None
            Keywords that signal semantic anchors (must be preserved).
        """
        self.entropy_threshold = entropy_threshold
        self.anchor_keywords = anchor_keywords or {
            "correction",
            "change",
            "error",
            "bug",
            "fail",
            "incorrect",
            "instead",
            "however",
            "but",
            "refine",
            "assert",
            "verify",
        }

    def calculate_word_entropy(self, text: str) -> float:
        """Calculate the word-level Shannon entropy of a given text line.

        Parameters
        ----------
        text : str
            A line of text.

        Returns
        -------
        float
            Shannon entropy value. Returns 0.0 for empty or whitespace strings.
        """
        # Clean text and split into words
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 0.0

        word_counts = collections.Counter(words)
        total_words = len(words)

        entropy = 0.0
        for count in word_counts.values():
            p = count / total_words
            entropy -= p * math.log2(p)

        return entropy

    def is_semantic_anchor(self, line: str) -> bool:
        """Check if a line contains any high-importance semantic anchor keywords.

        Parameters
        ----------
        line : str
            A line of text.

        Returns
        -------
        bool
            True if the line contains an anchor keyword, False otherwise.
        """
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in self.anchor_keywords)

    def compress_thought(self, thought_text: str) -> str:
        """Compress the thought reasoning block by pruning low-entropy lines.

        Preserves lines that:
        - Have word entropy >= threshold.
        - Contain semantic anchors.
        - Are structural tags (e.g. `<thought>`, `</thought>`).

        Parameters
        ----------
        thought_text : str
            Raw thinking text containing reasoning lines.

        Returns
        -------
        str
            Compressed reasoning text.
        """
        lines = thought_text.splitlines()
        compressed_lines = []

        for line in lines:
            stripped = line.strip()
            # Always preserve structural tags or empty spacing
            if not stripped or stripped.startswith("<") or stripped.endswith(">"):
                compressed_lines.append(line)
                continue

            entropy = self.calculate_word_entropy(stripped)
            is_anchor = self.is_semantic_anchor(stripped)

            if entropy >= self.entropy_threshold or is_anchor:
                compressed_lines.append(line)
            else:
                # Optionally append a placeholder or simply drop the redundant step
                # We drop it to maximize token compression
                pass

        return "\n".join(compressed_lines)
