"""Vibe Parser — NL text to VibeIntent.

Uses lightweight keyword extraction (stopword filter + position weighting)
and a vocabulary-based operation classifier. Optionally enriches with
FLUX vault context to improve keyword coverage on domain-specific text.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from cohezion.vibe._vocab import (
    COMPLEXITY_BOOSTERS,
    COMPLEXITY_REDUCERS,
    OPERATION_VOCAB,
    STOPWORDS,
)
from cohezion.vibe.types import OperationType, VibeIntent


if TYPE_CHECKING:
    from cohezion.flux.aggregator import FluxAggregator


logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation, split into word tokens."""
    return re.findall(r"[a-z]+", text.lower())


def _extract_keywords(text: str, top_k: int = 12) -> list[str]:
    """Return the most signal-rich words from text.

    Filters stopwords, deduplicates, and keeps words >= 3 chars.
    Words appearing early in the sentence are given a small position boost.
    """
    tokens = _tokenize(text)
    seen: set[str] = set()
    scored: list[tuple[float, str]] = []
    for i, tok in enumerate(tokens):
        if tok in STOPWORDS or len(tok) < 3 or tok in seen:
            continue
        seen.add(tok)
        position_score = 1.0 / (1 + i * 0.05)
        vocab_score = 1.5 if tok in OPERATION_VOCAB else 1.0
        scored.append((position_score * vocab_score, tok))
    scored.sort(reverse=True)
    return [word for _, word in scored[:top_k]]


def _classify_operation(tokens: list[str]) -> tuple[OperationType, float]:
    """Vote on operation type from token list. Returns (type, confidence)."""
    if not tokens:
        return OperationType.UNKNOWN, 0.0

    votes: dict[OperationType, int] = {}
    for tok in tokens:
        op = OPERATION_VOCAB.get(tok)
        if op is not None:
            votes[op] = votes.get(op, 0) + 1

    if not votes:
        return OperationType.UNKNOWN, 0.1

    total_votes = sum(votes.values())
    best_op = max(votes, key=lambda k: votes[k])
    confidence = votes[best_op] / total_votes
    if confidence >= 0.7:
        confidence = min(1.0, confidence + 0.1)
    return best_op, round(confidence, 3)


def _estimate_complexity(text: str, keywords: list[str]) -> int:
    """Estimate workflow complexity on a 1-5 scale."""
    text_lower = text.lower()
    boost = sum(1 for phrase in COMPLEXITY_BOOSTERS if phrase in text_lower)
    reduce = sum(1 for phrase in COMPLEXITY_REDUCERS if phrase in text_lower)
    ops_count = sum(1 for kw in keywords if kw in OPERATION_VOCAB)
    raw = max(1, ops_count + boost - reduce)
    return max(1, min(5, raw))


class VibeParser:
    """Parses natural language text into a structured VibeIntent.

    Parameters
    ----------
    flux_aggregator : FluxAggregator | None
        Optional FLUX aggregator for vault-enriched keywords.
        When provided, the parser queries FLUX to expand keyword coverage
        with domain-specific terms from prior workflows. Non-blocking —
        failures are silently ignored.
    """

    def __init__(self, flux_aggregator: FluxAggregator | None = None) -> None:
        self._flux = flux_aggregator

    async def parse(self, nl_text: str, top_k_keywords: int = 12) -> VibeIntent:
        """Parse NL text into a VibeIntent.

        Parameters
        ----------
        nl_text : str
            Raw natural language description of the desired workflow.
        top_k_keywords : int
            Max keywords to extract.

        Returns
        -------
        VibeIntent
            Extracted keywords, operation type, complexity, and confidence.
        """
        if not nl_text or not nl_text.strip():
            return VibeIntent(
                raw_text=nl_text,
                keywords=[],
                operation_type=OperationType.UNKNOWN,
                complexity=1,
                confidence=0.0,
            )

        tokens = _tokenize(nl_text)
        keywords = _extract_keywords(nl_text, top_k=top_k_keywords)

        if self._flux is not None:
            keywords = await self._enrich_keywords(nl_text, keywords)

        operation_type, confidence = _classify_operation(tokens)
        complexity = _estimate_complexity(nl_text, keywords)
        sub_intents = self._extract_sub_intents(nl_text)

        return VibeIntent(
            raw_text=nl_text,
            keywords=keywords,
            operation_type=operation_type,
            complexity=complexity,
            confidence=confidence,
            sub_intents=sub_intents,
        )

    async def _enrich_keywords(
        self,
        query: str,
        existing_keywords: list[str],
        *args: Any,
        **kwargs: Any,
    ) -> list[str]:
        """Query FLUX vault to expand keyword list with domain terms."""
        try:
            ctx = await self._flux.get_context(query, top_k=5)  # type: ignore[union-attr]
            for block in ctx.blocks:
                extra = _extract_keywords(block.content, top_k=3)
                for kw in extra:
                    if kw not in existing_keywords:
                        existing_keywords.append(kw)
        except Exception:
            logger.debug("FLUX enrichment failed (non-blocking)")
        return existing_keywords

    @staticmethod
    def _extract_sub_intents(text: str) -> list[str]:
        """Split complex requests into sub-goal strings."""
        parts = re.split(
            r"\s+(?:and then|then|after that|also|additionally|finally)\s+",
            text,
            flags=re.IGNORECASE,
        )
        stripped = text.strip()
        return [
            p.strip() for p in parts if p.strip() and len(p.strip()) > 5 and p.strip() != stripped
        ]
