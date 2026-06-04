# class attrs treated as immutable config; never mutated per-instance
"""Prompt optimizer - compress verbose requests to token-efficient format.

Applies template-based substitution, filler word removal, and entity extraction
to compress requests without calling any LLM. All operations are 0-token heuristics.

Example:
    ```python
    optimizer = PromptOptimizer()
    original = "Please, could you kindly generate a list of 10 creative story ideas?"
    compressed = optimizer.optimize(original)
    # Result: "Generate 10 creative story ideas" (53% token reduction)
    ```
"""

import logging
import re


logger = logging.getLogger(__name__)


class PromptOptimizer:
    """Compress verbose prompts to token-efficient format (0 tokens).

    Removes filler words, normalizes whitespace, and applies template-based
    compression without LLM calls.

    Example:
        ```python
        optimizer = PromptOptimizer()
        result = optimizer.optimize("Please generate 10 story ideas please")
        assert "please" not in result.lower()
        ```
    """

    # Filler words to remove
    FILLER_WORDS = [
        "please",
        "kindly",
        "could you",
        "can you",
        "would you",
        "will you",
        "thank you",
        "thanks",
        "appreciate",
        "humbly request",
        "respectfully",
        "sincerely",
        "so on",
        "et cetera",
        "i think",
        "it seems",
        "maybe",
        "possibly",
        "perhaps",
        "hmm",
        "uh",
        "um",
    ]

    # Redundant phrase patterns
    REDUNDANCY_PATTERNS = [
        (r"\b(very|really|quite)\s+(very|really|quite)\b", r"$1"),  # Repeated intensifiers
        (r"\b(and\s+)+and\b", "and"),  # Repeated "and"
        (r"\s+", " "),  # Multiple spaces
    ]

    def __init__(self, enable_filler_removal: bool = True, estimate_tokens: bool = True):
        """Initialize optimizer.

        Args:
            enable_filler_removal: Whether to remove filler words
            estimate_tokens: Whether to estimate token savings
        """
        self.enable_filler_removal = enable_filler_removal
        self.estimate_tokens = estimate_tokens

    def optimize(self, text: str) -> str:
        """Compress text via heuristics (0 tokens).

        Args:
            text: Original prompt text

        Returns:
            Compressed prompt text
        """
        if not text or not isinstance(text, str):
            return text

        original_tokens = self._estimate_tokens(text)

        # Remove filler words
        if self.enable_filler_removal:
            text = self._remove_filler_words(text)

        # Remove redundancy
        text = self._remove_redundancy(text)

        # Normalize whitespace
        text = self._normalize_whitespace(text)

        # Trim punctuation
        text = text.strip()

        compressed_tokens = self._estimate_tokens(text)

        if self.estimate_tokens and original_tokens > 0:
            reduction_pct = 100 * (1 - compressed_tokens / original_tokens)
            logger.debug(
                f"Optimized prompt: {original_tokens} → {compressed_tokens} tokens "
                f"({reduction_pct:.1f}% reduction)"
            )

        return text

    def _remove_filler_words(self, text: str) -> str:
        """Remove filler words (case-insensitive).

        Args:
            text: Text to process

        Returns:
            Text with filler words removed
        """
        # Build pattern that matches filler words as whole words
        for filler in self.FILLER_WORDS:
            pattern = r"\b" + re.escape(filler) + r"\b"
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        return text

    def _remove_redundancy(self, text: str) -> str:
        """Remove redundant phrases.

        Args:
            text: Text to process

        Returns:
            Text with redundancy reduced
        """
        for pattern, replacement in self.REDUNDANCY_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace (trim, deduplicate).

        Args:
            text: Text to process

        Returns:
            Normalized text
        """
        # Replace multiple spaces with single space
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation).

        Uses heuristic: ~1.3 tokens per word on average.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        words = text.split()
        return int(len(words) * 1.3)

    def extract_entities(self, text: str) -> dict:
        """Extract entities from text via regex (0 tokens).

        Extracts file paths, numbers, and quoted strings.

        Args:
            text: Text to process

        Returns:
            Dictionary with extracted entities
        """
        # File paths (*.py, *.md, *.txt, *.json)
        files = re.findall(r"\b[\w/\-.]+\.(py|md|txt|json|yaml|yml|csv)\b", text)

        # Numbers
        numbers = re.findall(r"\b\d+\b", text)

        # Quoted strings
        quotes = re.findall(r'"([^"]+)"', text)

        return {"files": files, "numbers": numbers, "quotes": quotes}

    def get_compression_stats(self, original: str, compressed: str) -> dict:
        """Get compression statistics.

        Args:
            original: Original text
            compressed: Compressed text

        Returns:
            Dictionary with compression metrics
        """
        original_tokens = self._estimate_tokens(original)
        compressed_tokens = self._estimate_tokens(compressed)

        return {
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "tokens_saved": original_tokens - compressed_tokens,
            "reduction_pct": (
                100 * (1 - compressed_tokens / original_tokens) if original_tokens > 0 else 0.0
            ),
            "original_chars": len(original),
            "compressed_chars": len(compressed),
        }

    def prune_rules(
        self,
        rules_content: str,
        task_description: str | None = None,
        seen_word_sets: list[set[str]] | None = None,
    ) -> tuple[str, list[set[str]]]:
        """Deduplicate and contextually prune rules blocks based on task relevance.

        Uses zero-cost overlap coefficient and keyword relevance mapping to keep
        only non-redundant and task-relevant rules.

        Args:
            rules_content: Raw rules markdown text
            task_description: Optional task description to prune by relevance
            seen_word_sets: List of word sets already processed (for cross-file dedup)

        Returns:
            Tuple of (pruned_rules_content, updated_seen_word_sets)
        """
        if not rules_content:
            return rules_content, seen_word_sets or []

        if seen_word_sets is None:
            seen_word_sets = []

        desc_lower = task_description.lower() if task_description else ""

        # Split into blocks
        raw_blocks = rules_content.split("\n\n")
        pruned_blocks = []

        # Category keyword triggers
        categories = {
            "test": ["test", "pytest", "mock", "assert", "unit", "coverage"],
            "git": ["git", "commit", "branch", "stash", "pr", "repo", "lfs"],
            "db": ["db", "surreal", "persist", "sql", "kv", "table"],
            "physics": ["spin", "manifold", "hiho", "coherence", "quantum", "spinor"],
            "mcp": ["mcp", "stdio", "tool", "server", "agents.md"],
            "kaggle": ["kaggle", "leaderboard", "blackwell", "gpu", "submission"],
            "ui": ["web", "next.js", "component", "react", "agui", "anima", "ts", "typescript"],
        }

        for block in raw_blocks:
            cleaned_block = block.strip()
            if not cleaned_block:
                continue

            # Always keep headers, titles, and structural markers
            if cleaned_block.startswith("#") and len(cleaned_block.splitlines()) == 1:
                pruned_blocks.append(cleaned_block)
                continue

            # Extract words for deduplication
            words = set(re.findall(r"\b\w+\b", cleaned_block.lower()))
            if not words:
                pruned_blocks.append(cleaned_block)
                continue

            # 1. Deduplication check (Overlap coefficient >= 0.65)
            is_redundant = False
            for seen_set in seen_word_sets:
                intersection = words.intersection(seen_set)
                min_len = min(len(words), len(seen_set))
                if min_len > 0 and (len(intersection) / min_len) >= 0.65:
                    is_redundant = True
                    break

            if is_redundant:
                logger.debug(f"Pruning redundant rules block: {cleaned_block[:60]}...")
                continue

            # 2. Relevance check
            # Keep if block contains mandatory/critical core terms
            is_core = any(
                term in cleaned_block.upper()
                for term in [
                    "MANDATORY",
                    "CONSTRAINTS",
                    "CRITICAL",
                    "CONSTITUTION",
                    "CHARTER",
                    "INVARIANT",
                    "RULES",
                ]
            )

            # Keep headers, short templates, or if no task description is provided
            if len(cleaned_block) < 60 or is_core or not desc_lower:
                pruned_blocks.append(cleaned_block)
                seen_word_sets.append(words)
                continue

            # Determine block category based on rule content
            block_lower = cleaned_block.lower()
            matched_categories = []
            for cat, keywords in categories.items():
                if any(kw in block_lower for kw in keywords):
                    matched_categories.append(cat)

            # If block belongs to specific categories, check if the task references them
            keep = True
            if matched_categories:
                # Keep only if at least one matched category is referenced in task_description
                has_task_reference = False
                for cat in matched_categories:
                    # Check if task description has any keyword of this category
                    if any(kw in desc_lower for kw in categories[cat]):
                        has_task_reference = True
                        break
                if not has_task_reference:
                    keep = False

            if keep:
                pruned_blocks.append(cleaned_block)
                seen_word_sets.append(words)
            else:
                logger.debug(
                    f"Pruning irrelevant rules block ({'/'.join(matched_categories)}): {cleaned_block[:60]}..."
                )

        return "\n\n".join(pruned_blocks), seen_word_sets
