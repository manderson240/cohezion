"""V-model tests for the dev_loop verification-consumer.

Discriminating: each test would FAIL against the most plausible wrong impl
(land regardless of review / land unverifiable proposals / silent-pass on
reviewer error / auto-commit). No network — a scripted FakeChat stands in for
local inference.
"""

from __future__ import annotations

import inspect
import json

from cohezion.actioner import dev_loop
from cohezion.actioner.dev_loop import (
    adversarial_review,
    implement_and_verify,
    ready_proposals,
    run_batch,
)


class FakeChat:
    """Scripted local-inference stand-in: implementation text + review votes."""

    def __init__(
        self, impl="IMPL: edit foo.py, add bar()", votes=("APPROVE", "APPROVE", "APPROVE")
    ):
        self.impl = impl
        self.votes = list(votes)
        self._i = 0
        self.calls: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.calls.append(prompt)
        if "ADVERSARIAL" in prompt:
            v = self.votes[self._i % len(self.votes)]
            self._i += 1
            return f"{v} — because reasons"
        return self.impl


GOOD = {
    "item_id": "i1",
    "proposal": "add a semantic cache floor",
    "falsifiable_step": "uv run pytest tests/test_x.py passes",
}
PLACEHOLDER = {"item_id": "i2", "proposal": "vague idea", "falsifiable_step": "(model omitted)"}


# ── DL1 structural: the review is actually consumed ──────────────────────────
def test_implement_and_verify_calls_adversarial_review():
    src = inspect.getsource(implement_and_verify)
    assert "adversarial_review" in src, "implement_and_verify must invoke the review (consumption)"


def test_three_independent_lenses_are_queried():
    chat = FakeChat()
    implement_and_verify(GOOD, chat)
    review_calls = [c for c in chat.calls if "ADVERSARIAL" in c]
    assert len(review_calls) == 3, "must query all 3 lenses independently"


# ── DL2 discriminating: REJECT consensus blocks landing ──────────────────────
def test_consensus_reject_is_not_green(tmp_path):
    chat = FakeChat(votes=("REJECT", "REJECT", "APPROVE"))  # 1/3 approve
    outcome = implement_and_verify(GOOD, chat)
    assert outcome.review.approvals == 1
    assert outcome.green is False, (
        "1/3 approve must NOT be green (a land-regardless impl fails here)"
    )


def test_consensus_approve_is_green():
    outcome = implement_and_verify(GOOD, FakeChat(votes=("APPROVE", "APPROVE", "REJECT")))  # 2/3
    assert outcome.green is True


# ── DL3 discriminating: unverifiable proposals are skipped, never landed ──────
def test_placeholder_falsifiable_is_not_verifiable():
    chat = FakeChat()
    outcome = implement_and_verify(PLACEHOLDER, chat)
    assert outcome.verifiable is False
    assert outcome.green is False
    assert chat.calls == [], "must not even spend inference on an unverifiable proposal"


def test_ready_proposals_excludes_placeholder(tmp_path):
    pfile = tmp_path / "proposals.jsonl"
    pfile.write_text(json.dumps(GOOD) + "\n" + json.dumps(PLACEHOLDER) + "\n")
    ready = ready_proposals(pfile, implemented_ids=set())
    ids = {p["item_id"] for p in ready}
    assert ids == {"i1"}, "placeholder falsifiable step must be excluded from the ready set"


# ── DL4 safety: reviewer error is a REJECT, never a silent pass ───────────────
def test_reviewer_error_counts_as_reject():
    def raising_chat(prompt: str) -> str:
        if "ADVERSARIAL" in prompt:
            raise RuntimeError("model down")
        return "impl"

    review = adversarial_review(GOOD, "impl", raising_chat)
    assert review.approvals == 0 and review.consensus is False


# ── DL5 safety structural: cannot execute ANY shell command (so no git writes) ─
def test_source_cannot_shell_out():
    # The real safety invariant: dev_loop lands artifacts via file writes only and
    # has no way to run a subprocess — so `git commit/merge/push` is structurally
    # impossible. A wrong impl that shelled out to git would import one of these.
    src = inspect.getsource(dev_loop)
    for banned in ("subprocess", "os.system", "os.popen", "Popen", "os.exec"):
        assert banned not in src, f"dev_loop must not be able to execute commands ({banned!r})"


# ── DL-parse: realistic HEDGED model output (the un-mocked bug, now regression) ─
def test_parse_vote_handles_hedged_output():
    from cohezion.actioner.dev_loop import _parse_vote

    # Real 8B reviewers explain BEFORE the verdict — the old startswith check failed these.
    assert _parse_vote("The change is minimal and passes the test. APPROVE - looks good.") is True
    assert _parse_vote("This has a bug in the edge case and would fail. REJECT.") is False
    assert _parse_vote("**Analysis:** solid.\nAPPROVE") is True
    assert _parse_vote("no clear verdict here") is False  # uncertainty -> reject
    # both tokens present -> first verdict wins (adversarial: a REJECT-then-approve is a reject)
    assert _parse_vote("REJECT because X, though one could APPROVE if X were fixed") is False


def test_hedged_approvals_reach_consensus():
    from cohezion.actioner.dev_loop import adversarial_review

    # A reviewer that hedges then approves must count as APPROVE (was the degenerate 0/3 bug).
    def chat(p):
        return "The implementation addresses the proposal correctly. APPROVE."

    review = adversarial_review(GOOD, "impl", chat)
    assert review.approvals == 3 and review.consensus is True


# ── DL6 discriminating: run_batch lands only green, isolates failures ─────────
def test_run_batch_lands_only_green(tmp_path):
    pfile = tmp_path / "proposals.jsonl"
    pfile.write_text(json.dumps(GOOD) + "\n" + json.dumps(PLACEHOLDER) + "\n")
    ledger = tmp_path / "ledger.jsonl"
    vault = tmp_path / "vault"
    summary = run_batch(
        FakeChat(votes=("APPROVE", "APPROVE", "APPROVE")),
        proposals_path=pfile,
        ledger_path=ledger,
        vault_dir=vault,
    )
    landed = {x["item_id"] for x in summary["landed"]}
    assert landed == {"i1"}, (
        "only the verifiable+consensus item lands; placeholder never enters ready"
    )
    assert ledger.exists() and "i1" in ledger.read_text()


def test_run_batch_isolates_per_item_failure(tmp_path):
    pfile = tmp_path / "proposals.jsonl"
    pfile.write_text(json.dumps(GOOD) + "\n")

    def boom(prompt: str) -> str:
        raise RuntimeError("inference wedged")

    summary = run_batch(
        boom, proposals_path=pfile, ledger_path=tmp_path / "l.jsonl", vault_dir=tmp_path / "v"
    )
    assert summary["landed"] == [] and "i1" in summary["failed"]
