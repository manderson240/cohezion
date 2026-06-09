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


def correspondence_is_discriminating(corpus: dict[str, list[str]], encoder: Encoder) -> bool:
    """Metacognitive self-check: does the encoder DISCRIMINATE related from unrelated? (item 68).

    ``corpus`` maps a group label → its member texts. Returns True iff BOTH hold:
      (a) every item's self-correspondence ``cosine(e(x), e(x)) ≈ 1.0`` (no zero/degenerate vectors),
      (b) the MEAN within-group correspondence strictly exceeds the MEAN cross-group correspondence
          (related items are geometrically nearer than unrelated ones).
    A vacuous corpus (<2 items, or no within/cross pair to compare) → True. This validates item-66's
    FLUME substrate is signal, not noise — and FALSELY-passes nothing: a degenerate encoder mapping
    everything to one vector has self≈1 but intra==inter, so it returns False. Pure (injected encoder).
    """
    items = [(g, t) for g, texts in corpus.items() for t in texts]
    if len(items) < 2:
        return True  # vacuous
    vecs = [(g, encoder(t)) for g, t in items]
    # (a) self-correspondence ≈ 1.0 for every item (guards zero/degenerate vectors).
    if any(abs(_cosine(v, v) - 1.0) > 1e-6 for _g, v in vecs):
        return False
    # (b) mean intra-group > mean inter-group correspondence.
    intra: list[float] = []
    inter: list[float] = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            c = _cosine(vecs[i][1], vecs[j][1])
            (intra if vecs[i][0] == vecs[j][0] else inter).append(c)
    if not intra or not inter:
        return True  # only one group, or all singletons → nothing to discriminate (vacuous)
    return (sum(intra) / len(intra)) > (sum(inter) / len(inter))


def correspondence_margin(corpus: dict[str, list[str]], encoder: Encoder) -> float:
    """HOW discriminating is the encoder — ``mean_intra - mean_inter`` (item 117). Report-only.

    The quantified dual of item-68 ``correspondence_is_discriminating`` (which returns only a
    boolean): the calibration CONFIDENCE of the FLUME substrate. Composes the SAME intra/inter
    pairwise computation, returning the DIFFERENCE of the means instead of the ``>`` boolean. A large
    positive margin = the geometric index reliably separates related from unrelated items; a margin
    near 0 = item-66 results are near-noise (the honest open question); a negative margin = the index
    is anti-correlated (worse than chance). Mirrors item-61 ``rho_selection_margin``.

    A perfectly-separating encoder (intra ≈ 1, inter ≈ 0) → margin ≈ 1.0; a degenerate encoder
    (intra == inter) → 0.0; a vacuous corpus (< 2 items, or no within/cross pair to compare) → 0.0.
    Pure (injected encoder, no writes).
    """
    items = [(g, t) for g, texts in corpus.items() for t in texts]
    if len(items) < 2:
        return 0.0  # vacuous — nothing to compare
    vecs = [(g, encoder(t)) for g, t in items]
    intra: list[float] = []
    inter: list[float] = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            c = _cosine(vecs[i][1], vecs[j][1])
            (intra if vecs[i][0] == vecs[j][0] else inter).append(c)
    if not intra or not inter:
        return 0.0  # only one group, or all singletons → no discrimination measurable (vacuous)
    return (sum(intra) / len(intra)) - (sum(inter) / len(inter))


def novelty_density(
    items: Iterable[str],
    corpus: Iterable[dict],
    *,
    encoder: Encoder,
    novelty_threshold: float = 0.5,
) -> float:
    """Fraction of ``items`` that are geometrically NOVEL vs ``corpus`` (item 95). Report-only.

    Eagleman memory-density theory of subjective time: novelty → rich/dense memory, routine →
    compressed/impoverished. A self-monitor over the loop's OWN output. For each item text, its MAX
    geometric correspondence to the corpus is computed (via :func:`geometric_correspondence`); the
    item is NOVEL when that max is strictly BELOW ``novelty_threshold`` (geometrically distinct from
    all prior work) and ROUTINE when at/above it (the loop near-duplicating — an item already in the
    corpus scores ≈ 1.0 → routine). Returns the novel fraction in ``[0, 1]``: HIGH = a healthy
    exploring regime, LOW = a spinning / near-duplicating regime. Empty ``items`` → ``0.0`` (no
    ZeroDivision); empty ``corpus`` → every item novel (nothing to resemble). Report-only — flags,
    never gates. Pure given the injected ``encoder``. Distinct from item-80 journey-novelty (FLUME
    trajectories); this is novelty of BACKLOG ITEMS. Caveat: inherits geometric-correspondence's
    short-title imperfection (item 68) → advisory only.
    """
    item_list = [str(t) for t in items]
    if not item_list:
        return 0.0
    corpus_list = list(corpus)  # materialize: iterated once per item (avoid generator exhaustion)
    novel = 0
    for text in item_list:
        # floor=-1.0 keeps EVERY corpus item a candidate so top_k=1 is the true maximum correspondence.
        matches = geometric_correspondence(text, corpus_list, encoder=encoder, top_k=1, floor=-1.0)
        max_corr = matches[0].score if matches else -1.0
        if max_corr < novelty_threshold:
            novel += 1
    return novel / len(item_list)


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
