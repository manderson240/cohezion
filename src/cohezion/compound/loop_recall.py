"""Vault-recall augmentation for the build loop (item 108, Thread P).

Closes the recall gap identified in the Thread P diagnostic (2026-06-06): the build
loop uses ONLY FLUME geometric code-commit recall (`compound_context_for`), and never
consults the 12,338-note Obsidian vault or the 18-neuron SurrealDB store.

``loop_recall_context(item_text)`` is a REPORT-ONLY advisory: it surfaces the top vault
notes and neurons relevant to a backlog item so the loop author can consult prior
experience before implementing — it never changes WHICH item is implemented and never
writes to any store.

Inference-bearing path (item 99 queue note, 2026-06-07)
---------------------------------------------------------
The default ``vault_search_fn`` calls the vault MCP server (``vault_find_relevant_context``
tool via subprocess ``mcp-cli``) with the lemonade nomic-embed-text-v2-moe-GGUF 768D
model on ``:13305`` as the backing embedding model.  This is the inference-bearing arm
(CA1 invariant: threshold 0.58 for 768D).

If the vault MCP is unreachable the function degrades to ``[]`` (fail-soft, never
fabricates hits).  In tests, inject ``vault_search_fn`` + ``neuron_store`` — no live
services are touched.

Falsifiable checks
------------------
- An item with no relevant vault/neuron memory → empty hits (never fabricated).
- If nomic-embed / vault MCP is unreachable → honest ``[]`` (fail-soft).
- Never mutates state (read-only).
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

from cohezion.governance.knowledge_bridge import recall_neurons


logger = logging.getLogger(__name__)

# Neuron countries to search for loop-level context.
_LOOP_NEURON_COUNTRIES = ("inference", "skill", "cerebellum")

# mcp-cli path (resolved at call-time, not import-time — lazy per CLAUDE.md MCP rule).
_MCP_CLI = "mcp-cli"

# Character limit for the item_text passed to vault search (stay well under embed token limit).
_QUERY_TRUNCATE = 512


@dataclass(frozen=True)
class RecallHit:
    """A single vault note or neuron hit with relevance metadata."""

    source: str  # "vault" | "neuron"
    title: str
    content_snippet: str  # first 200 chars of the matched content
    country: str  # for neurons: "inference" / "skill" / "cerebellum"; for vault: ""
    relevance: float  # similarity score or 1.0 when unavailable


@dataclass(frozen=True)
class LoopRecallResult:
    """Result of a loop recall advisory.  Always a valid struct; never raises.

    ``vault_hits`` and ``neuron_hits`` are empty lists when recall found nothing or
    when the underlying services are unreachable (fail-soft).
    """

    item_text_truncated: str  # the query as actually sent (for auditability)
    vault_hits: list[RecallHit] = field(default_factory=list)
    neuron_hits: list[RecallHit] = field(default_factory=list)
    error: str | None = None  # non-None when a service was unreachable

    @property
    def total_hits(self) -> int:
        return len(self.vault_hits) + len(self.neuron_hits)

    @property
    def is_empty(self) -> bool:
        return self.total_hits == 0


# ---------------------------------------------------------------------------
# Default vault search function — calls vault MCP via mcp-cli subprocess.
# ---------------------------------------------------------------------------


def _default_vault_search(query: str, *, top_k: int) -> list[RecallHit]:
    """Call ``vault_find_relevant_context`` via mcp-cli.  Fail-soft → []."""
    import sys

    if "pytest" in sys.modules or "unittest" in sys.modules:
        # Never touch the real vault during automated tests.
        return []
    try:
        payload = json.dumps({"query": query[:_QUERY_TRUNCATE], "top_k": top_k})
        result = subprocess.run(
            [_MCP_CLI, "cohezion-vault/vault_find_relevant_context", payload],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            logger.debug("vault_find_relevant_context failed: %s", result.stderr[:200])
            return []
        raw = json.loads(result.stdout)
        # mcp-cli returns {"content": [{"text": "..."}]} or a list of hit dicts.
        hits: list[RecallHit] = []
        items = raw if isinstance(raw, list) else raw.get("results", [])
        for item in items[:top_k]:
            title = item.get("title", item.get("path", ""))
            snippet = (item.get("content") or item.get("text") or "")[:200]
            score = float(item.get("similarity", item.get("score", 1.0)))
            hits.append(
                RecallHit(
                    source="vault",
                    title=title,
                    content_snippet=snippet,
                    country="",
                    relevance=score,
                )
            )
        return hits
    except Exception as exc:
        logger.debug("_default_vault_search error: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

VaultSearchFn = Callable[[str, int], list[RecallHit]]


def loop_recall_context(
    item_text: str,
    *,
    top_k: int = 5,
    vault_search_fn: VaultSearchFn | None = None,
    neuron_store: list[dict] | None = None,
) -> LoopRecallResult:
    """Surface vault notes + neurons relevant to a backlog ``item_text``.

    Report-only advisory: proposes context the build loop can consult; never changes
    which item is implemented; never writes.

    Args:
        item_text: The backlog item description / title to recall context for.
        top_k: Maximum number of vault hits to return.
        vault_search_fn: Injectable search function ``(query, top_k) -> [RecallHit]``.
            Defaults to the mcp-cli vault search (inference-bearing: nomic-embed via
            ``:13305``).  Inject a no-op for pure unit tests.
        neuron_store: Injected neuron list passed to ``recall_neurons`` (avoids live
            SurrealDB reads in tests).  ``None`` → production path (no-op under pytest
            per ``knowledge_bridge.recall_neurons`` guard).

    Returns:
        :class:`LoopRecallResult` — always; never raises.
    """
    if not item_text or not item_text.strip():
        return LoopRecallResult(
            item_text_truncated="",
            vault_hits=[],
            neuron_hits=[],
            error="empty item_text",
        )

    query = item_text.strip()[:_QUERY_TRUNCATE]
    search_fn = vault_search_fn or (lambda q, k: _default_vault_search(q, top_k=k))

    vault_hits: list[RecallHit] = []
    error: str | None = None
    try:
        vault_hits = search_fn(query, top_k)
    except Exception as exc:
        error = f"vault_search_fn raised: {exc}"
        logger.debug("loop_recall_context vault search error: %s", exc)

    # Recall neurons across all three countries using item_text as the key.
    # recall_neurons is fail-soft (returns [] on any error / pytest guard).
    neuron_hits: list[RecallHit] = []
    for country in _LOOP_NEURON_COUNTRIES:
        try:
            neurons = recall_neurons(country, query, store=neuron_store)
            for neuron in neurons[:top_k]:
                title = neuron.get("id", neuron.get("skill_name", ""))
                snippet = str(neuron.get("content", neuron.get("data", "")))[:200]
                neuron_hits.append(
                    RecallHit(
                        source="neuron",
                        title=title,
                        content_snippet=snippet,
                        country=country,
                        relevance=1.0,  # neurons don't carry a similarity score
                    )
                )
        except Exception as exc:
            logger.debug("loop_recall_context neuron recall (%s) error: %s", country, exc)

    return LoopRecallResult(
        item_text_truncated=query,
        vault_hits=vault_hits,
        neuron_hits=neuron_hits,
        error=error,
    )


def loop_recall_report(
    item_text: str,
    *,
    top_k: int = 5,
    vault_search_fn: VaultSearchFn | None = None,
    neuron_store: list[dict] | None = None,
) -> dict:
    """Run loop recall and return a human-reviewable report dict.

    Report-only: wraps :func:`loop_recall_context`.  Suitable for inclusion in a
    build-loop tick's advisory output alongside geometric FLUME context.
    """
    result = loop_recall_context(
        item_text,
        top_k=top_k,
        vault_search_fn=vault_search_fn,
        neuron_store=neuron_store,
    )
    return {
        "query": result.item_text_truncated,
        "vault_hits": [
            {
                "title": h.title,
                "snippet": h.content_snippet,
                "relevance": round(h.relevance, 4),
            }
            for h in result.vault_hits
        ],
        "neuron_hits": [
            {
                "title": h.title,
                "country": h.country,
                "snippet": h.content_snippet,
            }
            for h in result.neuron_hits
        ],
        "total_hits": result.total_hits,
        "error": result.error,
    }
