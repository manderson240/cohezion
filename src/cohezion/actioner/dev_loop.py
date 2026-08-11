"""Dev verification-consumer — the V-model *right arm*, on local inference.

Fills the autonomous-loop gaps that sat after the actioner. The actioner
(``engine.py``) produces UN-reviewed proposals (``proposal`` + ``falsifiable_step``)
and stops. This consumer closes the loop, for each proposal:

    1. IMPLEMENT  — local inference drafts a concrete implementation addressing
       the proposal (the dev-implementation gap).
    2. VERIFY     — the proposal's ``falsifiable_step`` IS the V-model acceptance
       gate. A proposal whose step is empty/placeholder is UNVERIFIABLE and is
       SKIPPED — never landed (the V-model-rigor gap).
    3. REVIEW     — three INDEPENDENT local-inference lenses (correctness /
       safety / addresses-proposal) vote; consensus needs >= 2/3 APPROVE, and
       each lens defaults to REJECT when uncertain (the adversarial-review gap).
    4. LAND       — green + consensus writes an ``IMPLEMENTED-PENDING-REVIEW``
       artifact (ledger + vault). It NEVER git-commits or merges to main — the
       merge stays human-gated (the session-long "safe autonomy" boundary).

All inference is LOCAL ($0, :13305) via ``default_chat_fn``. Structure mirrors
the actioner's drain / dedup-ledger / per-item-isolation pattern.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.actioner.engine import PROPOSALS_PATH, default_chat_fn


logger = logging.getLogger(__name__)

DEV_LEDGER_PATH = Path.home() / ".cohezion" / "dev_implemented.jsonl"
DEV_VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "implementations" / "proposed"
BATCH_SIZE = 20

# A falsifiable step that is empty or one of the actioner's placeholder sentinels
# carries NO verifiable acceptance test — such a proposal cannot be autonomously
# landed (V-model: no right arm => no descent to landing).
_PLACEHOLDER_STEPS = {"", "(unstructured output)", "(model omitted)", "(none)"}

# Three independent adversarial lenses. Each is prompted to REJECT-on-uncertainty
# so consensus is earned, not defaulted.
_REVIEW_LENSES = ("correctness", "safety", "addresses_proposal")


def _valid_falsifiable(step: str) -> bool:
    return step.strip().lower() not in _PLACEHOLDER_STEPS and len(step.strip()) >= 8


@dataclass
class ReviewResult:
    votes: dict[str, bool]  # lens -> APPROVE?
    reasons: dict[str, str]

    @property
    def approvals(self) -> int:
        return sum(1 for v in self.votes.values() if v)

    @property
    def consensus(self) -> bool:
        # >= 2 of 3 (majority of an odd panel). Never true on an empty panel.
        return self.approvals >= 2 and len(self.votes) >= 2


@dataclass
class DevOutcome:
    item_id: str
    implementation: str
    review: ReviewResult | None
    verifiable: bool
    landed_path: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def green(self) -> bool:
        # Landing requires BOTH a real acceptance test AND adversarial consensus.
        return self.verifiable and self.review is not None and self.review.consensus


def load_implemented_ids(ledger_path: Path = DEV_LEDGER_PATH) -> set[str]:
    ids: set[str] = set()
    if not ledger_path.exists():
        return ids
    for line in ledger_path.read_text().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("item_id"):
            ids.add(str(entry["item_id"]))
    return ids


def ready_proposals(
    proposals_path: Path = PROPOSALS_PATH, implemented_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    """Actioner proposals with a REAL falsifiable step, not yet implemented."""
    implemented_ids = implemented_ids if implemented_ids is not None else load_implemented_ids()
    out: list[dict[str, Any]] = []
    if not proposals_path.exists():
        return out
    for line in proposals_path.read_text().splitlines():
        try:
            p = json.loads(line)
        except json.JSONDecodeError:
            continue
        item_id = str(p.get("item_id", ""))
        if not item_id or item_id in implemented_ids:
            continue
        if not _valid_falsifiable(str(p.get("falsifiable_step", ""))):
            continue
        out.append(p)
    return out


def _implement_prompt(p: dict[str, Any]) -> str:
    return (
        "You are a senior engineer on the Cohezion local-AI stack (AMD Strix Halo, "
        "local lemonade inference, compound-engineering loop).\n"
        f"Proposal: {p.get('proposal', '')}\n"
        f"Acceptance test (must pass): {p.get('falsifiable_step', '')}\n\n"
        "Draft a concrete, minimal implementation that satisfies the proposal AND "
        "would pass the acceptance test. Give: the change (files/functions), and how "
        "the acceptance test is met. Be specific and elegantly simple; no scaffolding."
    )


def _review_prompt(lens: str, p: dict[str, Any], implementation: str) -> str:
    focus = {
        "correctness": "Is the implementation technically correct and would it actually pass the acceptance test?",
        "safety": "Is it safe — no destructive ops, no security/RCE risk, no unbounded resource use?",
        "addresses_proposal": "Does it actually address the proposal (not a plausible-but-off answer)?",
    }[lens]
    return (
        f"You are an ADVERSARIAL {lens} reviewer. Assume the implementation is flawed "
        "until proven otherwise.\n"
        f"Proposal: {p.get('proposal', '')}\n"
        f"Acceptance test: {p.get('falsifiable_step', '')}\n"
        f"Proposed implementation:\n{implementation}\n\n"
        f"{focus}\n"
        "Reply with exactly one line starting APPROVE or REJECT, then one reason. "
        "Default to REJECT if you are uncertain."
    )


def _parse_vote(raw: str) -> bool:
    """Robust APPROVE/REJECT extraction — real models hedge before the verdict.

    Not a leading-token check (that made the gate degenerate: 8B reviewers explain
    first). Rule: whichever verdict token appears is the vote; if both appear, the
    FIRST wins; if neither, REJECT (adversarial default — never a silent pass).
    """
    u = raw.upper()
    ia, ir = u.find("APPROVE"), u.find("REJECT")
    if ia == -1 and ir == -1:
        return False  # no verdict -> reject on uncertainty
    if ir == -1:
        return True
    if ia == -1:
        return False
    return ia < ir


def adversarial_review(
    p: dict[str, Any], implementation: str, chat_fn: Callable[[str], str]
) -> ReviewResult:
    """Three independent local-inference lenses; each rejects on uncertainty."""
    votes: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    for lens in _REVIEW_LENSES:
        try:
            raw = chat_fn(_review_prompt(lens, p, implementation))
        except Exception as exc:  # a failed reviewer is a REJECT, never a silent pass
            votes[lens], reasons[lens] = False, f"reviewer error: {exc}"
            continue
        votes[lens] = _parse_vote(raw)
        reasons[lens] = raw.strip()[:200]
    return ReviewResult(votes=votes, reasons=reasons)


def implement_and_verify(p: dict[str, Any], chat_fn: Callable[[str], str]) -> DevOutcome:
    """IMPLEMENT (local inference) -> VERIFY (falsifiable gate) -> REVIEW (consensus)."""
    item_id = str(p.get("item_id", ""))
    verifiable = _valid_falsifiable(str(p.get("falsifiable_step", "")))
    if not verifiable:
        # Unverifiable: do not even spend inference — cannot be landed.
        return DevOutcome(item_id=item_id, implementation="", review=None, verifiable=False)
    implementation = chat_fn(_implement_prompt(p)).strip()
    review = adversarial_review(p, implementation, chat_fn)
    return DevOutcome(
        item_id=item_id, implementation=implementation, review=review, verifiable=True
    )


def _land(p: dict[str, Any], outcome: DevOutcome, vault_dir: Path, ledger_path: Path) -> str:
    """Write the IMPLEMENTED-PENDING-REVIEW artifact. NEVER commits/merges."""
    import re

    vault_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", str(p.get("proposal", "impl")).lower())[:50].strip("-")
    path = vault_dir / f"{datetime.now(UTC).date()}-{outcome.item_id}-{slug}.md"
    votes = outcome.review.votes if outcome.review else {}
    path.write_text(
        "---\n"
        f"type: implementation-proposal\ndate: {datetime.now(UTC).date()}\n"
        f"source_item: {outcome.item_id}\nstatus: IMPLEMENTED-PENDING-REVIEW\n"
        "generator: dev_loop verification-consumer (local inference)\n"
        f"review_consensus: {outcome.review.approvals if outcome.review else 0}/3\n"
        "---\n\n"
        f"## Proposal\n{p.get('proposal', '')}\n\n"
        f"## Acceptance test (V-model gate)\n{p.get('falsifiable_step', '')}\n\n"
        f"## Implementation (local inference, NOT applied — review before merge)\n{outcome.implementation}\n\n"
        f"## Adversarial review ({outcome.review.approvals if outcome.review else 0}/3 approve)\n"
        + "\n".join(f"- **{lens}**: {'APPROVE' if ok else 'REJECT'}" for lens, ok in votes.items())
        + "\n"
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a") as f:
        f.write(
            json.dumps(
                {
                    "item_id": outcome.item_id,
                    "date": datetime.now(UTC).isoformat(),
                    "consensus": outcome.review.approvals if outcome.review else 0,
                    "artifact": str(path),
                    "status": "IMPLEMENTED-PENDING-REVIEW",
                }
            )
            + "\n"
        )
    return str(path)


def run_batch(
    chat_fn: Callable[[str], str] | None = None,
    *,
    batch_size: int = BATCH_SIZE,
    proposals_path: Path = PROPOSALS_PATH,
    vault_dir: Path = DEV_VAULT_DIR,
    ledger_path: Path = DEV_LEDGER_PATH,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Drain ready proposals -> implement+verify+review -> land green ones.

    Per-item isolation: a failure records and continues. Only green (verifiable
    AND consensus) items are landed, and landing is an artifact write — never a
    git commit/merge (safe autonomy: merge stays human-gated).
    """
    chat_fn = chat_fn or default_chat_fn()
    ready = ready_proposals(proposals_path, load_implemented_ids(ledger_path))[:batch_size]
    summary: dict[str, Any] = {
        "ready": len(ready),
        "landed": [],
        "rejected": [],
        "failed": {},
    }
    for p in ready:
        item_id = str(p.get("item_id", ""))
        try:
            outcome = implement_and_verify(p, chat_fn)
        except Exception as exc:  # isolate: this item fails, batch continues
            summary["failed"][item_id] = str(exc)
            continue
        if not outcome.green:
            summary["rejected"].append(
                {"item_id": item_id, "consensus": outcome.review.approvals if outcome.review else 0}
            )
            continue
        if dry_run:
            summary["landed"].append({"item_id": item_id, "dry_run": True})
            continue
        outcome.landed_path = _land(p, outcome, vault_dir, ledger_path)
        summary["landed"].append({"item_id": item_id, "artifact": outcome.landed_path})
    return summary


def run_loop(interval_minutes: int = 30, chat_fn: Callable[[str], str] | None = None) -> None:
    """Autonomous background loop: drain the dev backlog every interval."""
    import time

    logger.info("dev_loop verification-consumer started (interval=%dm)", interval_minutes)
    while True:
        try:
            summary = run_batch(chat_fn)
            logger.info(
                "dev_loop: %d ready, %d landed, %d rejected, %d failed",
                summary["ready"],
                len(summary["landed"]),
                len(summary["rejected"]),
                len(summary["failed"]),
            )
        except Exception as exc:
            logger.error("dev_loop batch error: %s", exc, exc_info=True)
        time.sleep(interval_minutes * 60)
