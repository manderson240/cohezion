"""Cohezion knowledge layer — wiki, graph, and retrieval utilities."""

import contextlib


# Wiring-sweep 2026-06-22: llm_wiki.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.knowledge.llm_wiki import (
        LLMWiki as LLMWiki,
    )
    from cohezion.knowledge.llm_wiki import (
        WikiEntry as WikiEntry,
    )
