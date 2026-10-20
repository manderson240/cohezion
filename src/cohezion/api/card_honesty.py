"""Honesty gates for research cards, enforced at the work-queue's single writer.

Three defects observed on live cards (2026-09-21, vault kanban/e7087d5f9008.md):

1. A card reached ``relevance=APPLY`` from a model verdict alone. No probe ever ran.
2. One arXiv paper was carded twice, once from arxiv.org and once from HF papers.
3. A model summary quoted a phrase ("choice tokens") that is nowhere in the source.

Each gate is a pure function here. ``work_queue_router`` applies them on every POST and
PATCH, because the router is the only writer that the research daemon, the actioner and
ad-hoc scripts all go through.
"""

from __future__ import annotations

import html
import re


# Externally-sourced cards. Internal ``improvement`` findings (datamesh EventConsumer)
# carry their own evidence and feed compound_feeder, so they are out of scope here.
RESEARCH_TYPES = frozenset({"research", "fleet"})

UNVERIFIED_LABEL = "[model summary, unverified]"
UNFAITHFUL_LABEL = "[UNFAITHFUL: quoted span(s) not found in source]"

# arXiv new-style ids (YYMM.NNNNN) behind any of the URL shapes the daemon sees.
_ARXIV_ID_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf|html)/|huggingface\.co/papers/|arxiv:)"
    r"(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)

# Straight or curly double quotes. A 4-char floor skips stray quote marks, not terms:
# the fabricated span on e7087d5f9008 was only 13 characters long.
_QUOTED_SPAN_RE = re.compile('["“”]([^"“”\\n]{4,}?)["“”]')


def canonical_paper_id(url: str) -> str:
    """``arxiv:<id>`` with the version stripped, or ``""`` when the URL names no paper."""
    match = _ARXIV_ID_RE.search(url or "")
    return f"arxiv:{match.group(1)}" if match else ""


def gate_relevance(item_type: str, relevance: str, probe_ref: str) -> str:
    """A research card may only be APPLY when it links a probe result."""
    if item_type in RESEARCH_TYPES and relevance == "APPLY" and not probe_ref:
        return "MONITOR"
    return relevance


def may_mark_actioned(action_route: str, probe_ref: str) -> bool:
    """``actioned`` needs evidence that something consumed the card."""
    return bool(action_route or probe_ref)


def _normalise(text: str) -> str:
    return " ".join(html.unescape(text or "").replace("’", "'").split())


def unfaithful_quotes(summary: str, source: str) -> list[str]:
    """Quoted spans in *summary* that do not appear verbatim in *source*."""
    haystack = _normalise(source)
    spans = (_normalise(s) for s in _QUOTED_SPAN_RE.findall(summary or ""))
    return [span for span in spans if span not in haystack]


def label_summary(summary: str, source: str) -> tuple[str, str]:
    """Return ``(labelled_summary, quote_check)``.

    quote_check is ``"fail"`` when a quoted span is not in the source, ``"pass"`` when
    every quoted span is, and ``"none"`` when nothing was quoted. Model prose is never
    judged for faithfulness; it is only labelled as unverified.
    """
    text = summary or ""
    for label in (UNFAITHFUL_LABEL, UNVERIFIED_LABEL):  # idempotent under re-PATCH
        text = text.removeprefix(label).lstrip()
    if not text.strip():
        return summary or "", "none"
    if unfaithful_quotes(text, source):
        return f"{UNFAITHFUL_LABEL} {text}", "fail"
    quoted = bool(_QUOTED_SPAN_RE.search(text))
    return f"{UNVERIFIED_LABEL} {text}", "pass" if quoted else "none"
