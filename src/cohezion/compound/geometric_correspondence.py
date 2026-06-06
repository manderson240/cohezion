"""Geometric correspondence in the compound loop (user request 2026-06-06; Learning 311).

Operationalizes Learning 311 ("encode hypotheses into 256D FLUME VAE thought vectors and measure
structural overlap with existing trajectory data") toward COMPOUND-ENGINEERING SOLUTION REUSE: for a
NEW problem, FLUME-encode it and the prior SOLVED items, measure geometric correspondence (cosine
structural overlap), and surface the top-k prior solutions to compound on — "you solved a
geometrically-similar problem in commit <ref>; build on it."

Advisory / report-only: it PROVIDES context (which prior commit corresponds to the new problem); it
never auto-applies a change. Wiring it into the live executor's pre-execution step is a SEPARATE,
permission-gated behaviour change. The encoder is INJECTABLE (deterministic in tests); the default is
the FLUME 256D encoder, which itself falls back to a hash embedding when no VAE checkpoint is present
(so it never hard-fails). Pure given the encoder — no writes.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np


Encoder = Callable[[str], np.ndarray]

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_BACKLOG = _REPO / "docs" / "IMPROVEMENT_BACKLOG.md"
# Capture a DONE row: bolded title + the DONE <hash>. TODO/BLOCKED rows are NOT prior solutions.
_DONE_ROW = re.compile(
    r"\|\s*\d+\s*\|.*?\*\*(.+?)\*\*.*?\|\s*DONE\s+([0-9a-f]{7,40})", re.IGNORECASE
)


@dataclass(frozen=True)
class CorrespondenceMatch:
    """A prior solved item geometrically corresponding to a new problem."""

    ref: str  # the prior work's reference (commit hash / item id)
    score: float  # geometric correspondence (cosine structural overlap) in [-1, 1]
    text: str  # the prior item's text


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def geometric_correspondence(
    query: str,
    corpus: Iterable[dict],
    *,
    encoder: Encoder,
    top_k: int = 3,
    floor: float = 0.0,
) -> list[CorrespondenceMatch]:
    """Top-k prior items geometrically corresponding to ``query`` (Learning 311). Advisory.

    ``corpus`` items are dicts with ``text`` (the prior item) and ``ref`` (its commit/id). Returns
    the geometrically-nearest prior solutions (cosine >= ``floor``), sorted by score desc then ref.
    Deterministic given ``encoder``; pure — does not mutate ``corpus``, does not write.
    """
    qv = encoder(query)
    out: list[CorrespondenceMatch] = []
    for item in corpus:
        score = _cosine(qv, encoder(str(item["text"])))
        if score >= floor:
            out.append(
                CorrespondenceMatch(ref=str(item["ref"]), score=score, text=str(item["text"]))
            )
    out.sort(key=lambda m: (-m.score, m.ref))
    return out[:top_k]


def _flume_encoder() -> Encoder:
    """Default encoder: the FLUME 256D text encoder (hash-embedding fallback if no VAE checkpoint).

    Lazy + fail-soft: if FLUME cannot be constructed, returns a deterministic hash-based fallback so
    correspondence still works (degraded) rather than hard-failing.
    """
    try:
        from cohezion.flume.vae_encoder import get_encoder

        return get_encoder().encode
    except Exception:
        # Deterministic hash fallback (same idea as vae_encoder's own fallback).
        def _hash_enc(text: str) -> np.ndarray:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            return rng.standard_normal(256)

        return _hash_enc


def _backlog_solution_corpus(backlog_path: Path) -> list[dict]:
    """Prior SOLVED items from the backlog: each DONE row → {text: <title>, ref: <hash>}."""
    try:
        lines = backlog_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    corpus: list[dict] = []
    for line in lines:
        m = _DONE_ROW.search(line)
        if m:
            corpus.append({"text": m.group(1).strip(), "ref": m.group(2)})
    return corpus


def correspondences_from_backlog(
    query: str,
    *,
    backlog_path: Path | None = None,
    encoder: Encoder | None = None,
    top_k: int = 3,
    floor: float = 0.0,
) -> list[CorrespondenceMatch]:
    """Inject geometric correspondence INTO the loop: for a new item ``query``, surface the prior
    DONE items (the loop's own solved work) geometrically closest to it — the compound-engineering
    retrieval ("compound on commit <ref>"). Corpus = backlog DONE rows; TODO/BLOCKED are excluded
    (not yet solutions). Encoder defaults to FLUME. Advisory/report-only; pure.
    """
    enc = encoder or _flume_encoder()
    corpus = _backlog_solution_corpus(backlog_path or _DEFAULT_BACKLOG)
    return geometric_correspondence(query, corpus, encoder=enc, top_k=top_k, floor=floor)


def compound_context_for(
    item_text: str,
    *,
    backlog_path: Path | None = None,
    encoder: Encoder | None = None,
    top_k: int = 3,
    floor: float = 0.0,
) -> str:
    """Advisory compound-engineering context for a NEW item (item 67 — wires item 66 into the tick).

    The build-loop tick calls this BEFORE implementing an item: it surfaces the geometrically-
    corresponding prior COMMITS to compound on (from :func:`correspondences_from_backlog`). Returns a
    human-readable advisory string; report-only — it does NOT alter what gets implemented (wiring it
    into the LIVE executor pre-step is a separate gated change). Pure given the encoder.
    """
    matches = correspondences_from_backlog(
        item_text, backlog_path=backlog_path, encoder=encoder, top_k=top_k, floor=floor
    )
    if not matches:
        return "No geometrically-corresponding prior solution found — treat as a novel item."
    lines = [
        "Compound-engineering context — prior commits geometrically near this item (compound on them):"
    ]
    lines.extend(f"  - {m.ref} (correspondence {m.score:.2f}): {m.text}" for m in matches)
    return "\n".join(lines)
