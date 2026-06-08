"""Span-level claim-support audit, DRIFT-inspired (item 69, Thread A).

Implements a structural, deterministic scaffold for auditing claim support across
an agent trajectory, with an injectable judge for the classification step.  The
structural parts (claim ledger, dependency trace, first-error localisation) are
PURE; the inference is confined to the injected ``judge`` callable, making this
module fully testable without live LLM services.

Design follows DRIFT (arXiv 2606.02060): build a claim ledger over an agent
trajectory (claims introduced → consequential → reused), classify each consequential
claim's support (supported / weakly / missing / contradicted) via an injected judge,
dependency-trace propagation, and localise the FIRST unsupported consequential claim
(the span where the trajectory went wrong).

Maps to existing Cohezion seams
---------------------------------
- ``compound/tape_logger.TapeEntry`` — the native trajectory step format
  (prompt + response; sequence number for ordering).
- ``compound/journey_tracker`` — the 12D position store; this module READS the
  trajectory for auditing, never writes.
- ``compound/retrospection_validator`` — the existing summary validator; claim audit
  COMPOSES it at the framework level (reports alongside it).

Report-only: the audit PROPOSES findings, never modifies the trajectory or logs.

Inference-bearing arm (item 99 queue note, 2026-06-07)
--------------------------------------------------------
The production judge = ``extend_claude`` → Granite-4.1-8B-GGUF on ``:13305`` at
temp=0 (blind — judge sees claim and context, not step identity).  This is the
inference-bearing part; the scaffold runs without it (inject a deterministic judge
for pure tests).

Falsifiable checks
------------------
- Fully-supported trajectory → empty ``findings`` (clean report).
- A trajectory whose claim is later contradicted → that span flagged as
  ``first_error_span``.
- Empty trajectory → ``[]`` (no fabricated findings).
- Deterministic given the judge (no randomness in the structural logic).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class SupportLabel(StrEnum):
    """DRIFT classification for a claim's evidential support."""

    SUPPORTED = "supported"  # Claim appears in prior context with clear backing.
    WEAKLY_SUPPORTED = "weakly"  # Indirect or partial backing.
    MISSING = "missing"  # No backing found in prior context.
    CONTRADICTED = "contradicted"  # Prior context contradicts this claim.


# Judge signature: (claim, prior_context) -> SupportLabel.
# The production judge calls Granite-4.1-8B via extend_claude (inference-bearing arm).
JudgeFn = Callable[[str, str], SupportLabel]


@dataclass(frozen=True)
class ClaimEntry:
    """One claim extracted from a trajectory step."""

    step_index: int  # index into the trajectory list
    claim_text: str  # the claim as a short string
    is_consequential: bool  # True if this claim is re-used in a later step
    support: SupportLabel
    prior_context_chars: int  # how many chars of context the judge received


@dataclass(frozen=True)
class AuditFinding:
    """A single finding from the claim-support audit."""

    step_index: int
    claim_text: str
    support: SupportLabel
    description: str


@dataclass(frozen=True)
class ClaimAuditResult:
    """Full result of a claim-support audit.  Always valid; never raises.

    ``findings`` is empty for a fully-supported trajectory (clean report).
    ``first_error_span`` is ``None`` when no unsupported consequential claim was found.
    """

    trajectory_length: int
    claim_ledger: list[ClaimEntry] = field(default_factory=list)
    findings: list[AuditFinding] = field(default_factory=list)
    first_error_span: int | None = None  # step_index of first problematic claim
    judge_label: str = "deterministic"  # identifies the judge used


# ---------------------------------------------------------------------------
# Claim extraction (structural, deterministic)
# ---------------------------------------------------------------------------


def _extract_claims_from_step(step: dict, step_index: int) -> list[str]:
    """Extract claim-like sentences from a trajectory step's response/output.

    A "claim" in DRIFT is a consequential assertion in the agent output. Here
    we use sentence boundaries as a simple proxy: each sentence ending in '.'
    or '!' is a candidate claim if it's long enough to be informational (>20
    chars).  The PRODUCTION judge (Granite-8B) does the real segmentation; this
    heuristic is the structural skeleton the injected judge works against.

    Pure: no I/O, step not mutated.
    """
    text = step.get("response") or step.get("output") or step.get("text") or ""
    if not text:
        return []
    sentences = []
    for chunk in text.replace("!", ".").split("."):
        chunk = chunk.strip()
        if len(chunk) > 20:  # skip trivial fragments
            sentences.append(chunk)
    return sentences[:10]  # cap: audit at most 10 claims per step (cost guard)


def _build_prior_context(trajectory: list[dict], up_to_index: int) -> str:
    """Concatenate all prior step responses up to (not including) up_to_index."""
    parts = []
    for i in range(up_to_index):
        step = trajectory[i]
        parts.append(step.get("response") or step.get("output") or step.get("text") or "")
    return " ".join(parts)[:4000]  # cap context (token budget: ~1k tokens)


def _is_claim_reused(claim: str, trajectory: list[dict], from_index: int) -> bool:
    """Return True if the claim text appears verbatim (or as a substring) in later steps."""
    claim_lower = claim.lower()
    for i in range(from_index + 1, len(trajectory)):
        step = trajectory[i]
        later_text = (
            (step.get("response") or step.get("output") or step.get("text") or "")
            + " "
            + (step.get("prompt") or "")
        ).lower()
        if claim_lower[:30] in later_text:  # 30-char prefix match (cheap + deterministic)
            return True
    return False


# ---------------------------------------------------------------------------
# Default judge (deterministic proxy for tests)
# ---------------------------------------------------------------------------


def _default_deterministic_judge(claim: str, prior_context: str) -> SupportLabel:
    """Deterministic proxy: classify support by simple substring containment.

    This is the structural fallback — not a quality LLM judge.  Inject
    Granite-4.1-8B-GGUF via ``extend_claude`` at temp=0 for production quality.

    Logic:
    - If any 10-char prefix of the claim appears in prior context → SUPPORTED.
    - If any 5-char prefix appears → WEAKLY_SUPPORTED.
    - Otherwise → MISSING.
    - Never returns CONTRADICTED (that requires semantic understanding — needs LLM).
    """
    if not prior_context:
        return SupportLabel.MISSING
    claim_lower = claim.lower()
    context_lower = prior_context.lower()
    prefix_10 = claim_lower[:10]
    prefix_5 = claim_lower[:5]
    if len(prefix_10) >= 10 and prefix_10 in context_lower:
        return SupportLabel.SUPPORTED
    if len(prefix_5) >= 5 and prefix_5 in context_lower:
        return SupportLabel.WEAKLY_SUPPORTED
    return SupportLabel.MISSING


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def claim_support_audit(
    trajectory: list[dict],
    *,
    judge: JudgeFn | None = None,
) -> ClaimAuditResult:
    """Audit claim support across an agent trajectory.

    Args:
        trajectory: Sequence of step dicts, each with at minimum one of
            ``"response"``, ``"output"``, or ``"text"`` (string).  Compatible with
            ``TapeEntry.__dict__`` objects.
        judge: Callable ``(claim, prior_context) -> SupportLabel``.  Defaults to the
            deterministic proxy.  Inject Granite-4.1-8B-GGUF via ``extend_claude``
            for the inference-bearing production arm (item 69 queue note, 2026-06-07).

    Returns:
        :class:`ClaimAuditResult` — always; never raises.  Empty trajectory → clean
        result (``findings=[]``, ``first_error_span=None``).
    """
    judge_fn = judge or _default_deterministic_judge
    judge_label = "deterministic-proxy" if judge is None else "injected"

    if not trajectory:
        return ClaimAuditResult(
            trajectory_length=0,
            claim_ledger=[],
            findings=[],
            first_error_span=None,
            judge_label=judge_label,
        )

    # Pass 1: extract claims and determine consequentiality.
    all_entries: list[ClaimEntry] = []
    for step_idx, step in enumerate(trajectory):
        claims = _extract_claims_from_step(step, step_idx)
        prior_ctx = _build_prior_context(trajectory, step_idx)
        for claim_text in claims:
            is_consequential = _is_claim_reused(claim_text, trajectory, step_idx)
            support = judge_fn(claim_text, prior_ctx)
            all_entries.append(
                ClaimEntry(
                    step_index=step_idx,
                    claim_text=claim_text,
                    is_consequential=is_consequential,
                    support=support,
                    prior_context_chars=len(prior_ctx),
                )
            )

    # Pass 2: localise findings — only consequential claims that are unsupported.
    _UNSUPPORTED = {SupportLabel.MISSING, SupportLabel.CONTRADICTED}
    findings: list[AuditFinding] = []
    first_error_span: int | None = None
    for entry in all_entries:
        if entry.is_consequential and entry.support in _UNSUPPORTED:
            desc = (
                f"Step {entry.step_index}: consequential claim "
                f"'{entry.claim_text[:60]}…' is {entry.support}"
            )
            findings.append(
                AuditFinding(
                    step_index=entry.step_index,
                    claim_text=entry.claim_text,
                    support=entry.support,
                    description=desc,
                )
            )
            if first_error_span is None:
                first_error_span = entry.step_index

    return ClaimAuditResult(
        trajectory_length=len(trajectory),
        claim_ledger=list(all_entries),
        findings=findings,
        first_error_span=first_error_span,
        judge_label=judge_label,
    )


def claim_support_audit_report(
    trajectory: list[dict],
    *,
    judge: JudgeFn | None = None,
) -> dict:
    """Run the audit and return a human-reviewable report dict.

    Report-only: PROPOSES findings, never modifies the trajectory.  Item 69, Thread A.
    Production judge = ``extend_claude`` → Granite-4.1-8B-GGUF on ``:13305``.
    """
    result = claim_support_audit(trajectory, judge=judge)
    return {
        "trajectory_length": result.trajectory_length,
        "total_claims_audited": len(result.claim_ledger),
        "consequential_claims": sum(1 for e in result.claim_ledger if e.is_consequential),
        "findings_count": len(result.findings),
        "first_error_span": result.first_error_span,
        "findings": [
            {
                "step_index": f.step_index,
                "claim": f.claim_text[:80],
                "support": str(f.support),
                "description": f.description,
            }
            for f in result.findings
        ],
        "judge": result.judge_label,
        # Falsifiable: empty findings = clean trajectory (no unsupported consequential claims).
        "clean": len(result.findings) == 0,
    }
