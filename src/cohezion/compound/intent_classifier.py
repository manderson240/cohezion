"""Intent classifier - 0-token operation type classification via heuristics.

Maps user requests to operation types (generate, analyze, search, transform, persist)
using keyword matching. Reuses OPERATION_KEYWORDS pattern from instruction_expander.py
for consistency and zero LLM token cost.

Example:
    ```python
    classifier = IntentClassifier()

    assert classifier.classify("Generate 10 story ideas") == "generate"
    assert classifier.classify("Analyze the CSV data") == "analyze"
    assert classifier.classify("Search for files") == "search"
    ```
"""

import logging
import re


logger = logging.getLogger(__name__)


# Reused directly from src/cohezion/core/instruction_expander.py for consistency
OPERATION_KEYWORDS: dict[str, list[str]] = {
    "search": [
        "search",
        "find",
        "locate",
        "discover",
        "identify",
        "scan",
        "lookup",
        "query",
        "check",
        "consult",
    ],
    "generate": [
        "generate",
        "create",
        "write",
        "compose",
        "draft",
        "produce",
        "build",
        "implement",
        "seed",
    ],
    "analyze": [
        "analyze",
        "evaluate",
        "assess",
        "examine",
        "review",
        "inspect",
        "verify",
        "validate",
        "test",
    ],
    "transform": [
        "transform",
        "convert",
        "format",
        "parse",
        "extract",
        "refactor",
        "reorganize",
        "normalize",
    ],
    "persist": [
        "store",
        "save",
        "log",
        "archive",
        "persist",
        "cache",
        "record",
        "backup",
    ],
}


class IntentClassifier:
    """Classify user intent → operation type using 0-token heuristics.

    Uses keyword matching to classify requests into operation types without
    calling any LLM. Supports weighted scoring and fallback defaults.

    Example:
        ```python
        classifier = IntentClassifier()
        op_type = classifier.classify("Generate 10 creative ideas")
        assert op_type == "generate"
        ```
    """

    def __init__(self, default_operation: str = "generate"):
        """Initialize classifier.

        Args:
            default_operation: Fallback operation type if no keywords match
        """
        self.default_operation = default_operation
        self.keywords = OPERATION_KEYWORDS

    def classify(self, text: str) -> str:
        """Classify request text to operation type (0 tokens).

        Args:
            text: User request text

        Returns:
            Operation type: "generate", "analyze", "search", "transform", or "persist"
        """
        if not text or not isinstance(text, str):
            return self.default_operation

        text_lower = text.lower()

        # Count keyword matches per operation
        scores = {}
        for operation, keywords in self.keywords.items():
            # Count how many keywords appear in text
            matches = sum(1 for keyword in keywords if self._keyword_in_text(text_lower, keyword))
            scores[operation] = matches

        # Return operation with highest score
        if max(scores.values()) > 0:
            best_operation = max(scores, key=scores.get)
            logger.debug(
                f"Classified '{text[:50]}...' → {best_operation} (score={scores[best_operation]})"
            )
            return best_operation

        # Default fallback
        logger.debug(f"No keywords matched, defaulting to {self.default_operation}")
        return self.default_operation

    def _keyword_in_text(self, text_lower: str, keyword: str) -> bool:
        """Check if keyword appears in text as word boundary.

        Matches whole words only (e.g., 'generate' matches 'generate code'
        but not 'regenerate').

        Args:
            text_lower: Lowercase text to search
            keyword: Keyword to find

        Returns:
            True if keyword found as whole word
        """
        # Use word boundary to avoid partial matches
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text_lower))

    def get_operation_keywords(self, operation: str) -> list[str]:
        """Get list of keywords for an operation type.

        Args:
            operation: Operation type (generate, analyze, search, etc.)

        Returns:
            List of keywords that trigger this operation
        """
        return self.keywords.get(operation, [])

    def get_all_keywords(self) -> dict[str, list[str]]:
        """Get all operation keywords.

        Returns:
            Dictionary mapping operation type → keyword list
        """
        return self.keywords.copy()
