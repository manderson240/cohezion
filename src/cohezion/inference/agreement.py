"""Cross-model semantic agreement — the one elicitation signal that survived falsification.

WHY THIS EXISTS
---------------
`TieredOrchestrator`'s quality gates are LENGTH-based (`min_chars`, `require_nonempty`).
Per the quarter-on-a-string protocol that is the forbidden shape: "a success gate so weak
it can never register a genuine quality failure -- it can't pull the string, so it can't
reclaim and can't trust." A confidently-wrong answer of adequate length passes every
existing gate.

This module supplies a gate that CAN fail on content. It is deliberately the only signal
that survived a falsification run (see the provenance block below): byte-level cross-family
divergence was tested and FALSIFIED, single-model entropy scored at chance. Nothing here is
speculative -- every constant traces to a measured number.

COST
----
Zero extra inference. The tiered cascade already produces an answer at each tier it visits
and currently DISCARDS all but the last. Those discarded answers are the peers. Only the
resident embedding model is called.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request

logger = logging.getLogger(__name__)

ROUTER_URL = "http://localhost:13305"
EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"

# PROVENANCE -- every number below is measured, not chosen.
# Experiment: ~/vaults/cohezion-vault/reports/20260730-bcfd-cross-family-elicitation.md
#   n=140 calibrated (52.9% base accuracy), 2000-sample bootstrap.
#   cross-model semantic agreement  AUROC 0.646, CI [0.547, 0.733]  <- SURVIVED
#   exact-string agreement          AUROC 0.609, CI [0.562, 0.659]  <- survived
#   byte cross-family divergence    AUROC 0.548, CI [0.454, 0.642]  <- FALSIFIED (spans 0.5)
#   single-model entropy            AUROC 0.496                     <- chance
#   placebo                         AUROC 0.522                     <- behaved correctly
# Threshold below is the Youden-optimal split on that run (J=0.256):
#   agreement >= 0.40 -> 65.3% accurate (n=72);  < 0.40 -> 39.7% accurate (n=68)
AGREEMENT_THRESHOLD = 0.40

# The signal is MODEST (AUROC 0.646). It is a triage hint, not a verdict -- so a low score
# damps confidence rather than rejecting outright. Sized so a maximally-divergent peer set
# cannot by itself flip an otherwise-good answer to rejected.
MAX_PENALTY = 0.30


def _embed(texts: list[str]) -> list[list[float]] | None:
    """Embed with the RESIDENT embedding model. Returns None if unavailable."""
    try:
        req = urllib.request.Request(
            f"{ROUTER_URL}/api/v1/embeddings",
            data=json.dumps({"model": EMBED_MODEL, "input": texts}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        return [d["embedding"] for d in data["data"]]
    except Exception as exc:  # noqa: BLE001 -- transport/shape faults are all non-fatal here
        logger.debug("agreement: embedding unavailable (%s)", exc)
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def semantic_agreement(texts: list[str], embed_fn=None) -> float | None:
    """Mean pairwise cosine similarity of `texts` in embedding space.

    Returns a value in [0, 1] where 1.0 means the models said the same thing, or None when
    agreement is UNDEFINED (fewer than two non-empty texts, or the embedder is unavailable).

    None is deliberately distinct from 0.0: "we could not measure agreement" must never be
    silently scored as "the models disagreed". That conflation is how a transport fault
    turns into a confident quality judgement.
    """
    live = [t.strip() for t in texts if t and t.strip()]
    if len(live) < 2:
        return None
    vecs = (embed_fn or _embed)(live)
    if not vecs or len(vecs) < 2:
        return None
    sims = [
        _cosine(vecs[i], vecs[j])
        for i in range(len(vecs))
        for j in range(i + 1, len(vecs))
    ]
    if not sims:
        return None
    return max(0.0, min(1.0, sum(sims) / len(sims)))


def agreement_penalty(agreement: float | None) -> float:
    """Confidence penalty in [0, MAX_PENALTY] implied by an agreement score.

    Zero when agreement is at or above the measured threshold, scaling linearly to
    MAX_PENALTY at total disagreement. Returns 0.0 for None -- an unmeasurable signal must
    not penalise the output.
    """
    if agreement is None or agreement >= AGREEMENT_THRESHOLD:
        return 0.0
    shortfall = (AGREEMENT_THRESHOLD - agreement) / AGREEMENT_THRESHOLD
    return round(MAX_PENALTY * shortfall, 4)
