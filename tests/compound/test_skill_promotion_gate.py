"""Draft-then-promote: a refinement must pass a gate before it can rewrite a live PRIME file.

THE DEFECT THIS CLOSES (established 2026-07-26). `SkillRefiner._append_refinement` wrote straight
to the live PRIME file. That is a CLOSED LOOP: an uncalibrated `quality_score` rewrites the very
instructions that produce it, with nothing external able to contradict the result. Nothing in the
system could represent "this refinement made things worse".

Two independent sources converged on the same fix:
  - AgentDebugX (arXiv 2607.18754): Detect -> Attribute -> RECOVER -> RERUN. We stopped at Attribute.
    Their attribution is right on both axes <30% of the time, and they still gate recovery on human
    approval. When a paper's own authors refuse to automate their result, that is data.
  - agno-agi/dash: confines the writing agent to a schema it OWNS while the agent touching real data
    is read-only. (Its own `save_validated_query` turned out to be a DOCSTRING asking the model to
    self-certify -- so the transferable idea is the authority split, not their learning loop.)

DESIGN NOTES:

1. `promotion_gate=None` writes directly -- existing behaviour preserved verbatim, so no caller
   changes and no test churn. Same isolation pattern as CB4/W1: production wires the gate, direct
   construction stays inert.

2. The gate is FAIL-CLOSED, deliberately inverting this module's usual fail-open habit. Elsewhere a
   broken guard must not stop work. Here the guarded action IS rewriting the instructions that steer
   every future run, so a gate that cannot answer must not be read as approval.

3. A rejected draft is KEPT on disk. The point is to make a rejected refinement inspectable rather
   than silently discarded -- the recurring failure this session was diagnoses that existed and had
   no consumer.
"""

from __future__ import annotations

from pathlib import Path

from cohezion.compound.skill_refiner import LearningSignal, SkillRefiner


PRIME = """# Test Skill

## Instructions
Do the thing.

## Version: 1.0.0

## Keywords: test
"""


def _prime(tmp_path: Path) -> Path:
    p = tmp_path / "TEST_PRIME.md"
    p.write_text(PRIME, encoding="utf-8")
    return p


def _signal() -> LearningSignal:
    return LearningSignal(
        skill_name="test",
        operation_type="op",
        metric_change="tokens_used=50",
        key_insight="use fewer tokens",
        recommendation="Prioritize token efficiency",
        confidence=0.9,
    )


def test_no_gate_writes_directly_unchanged_behaviour(tmp_path):
    """Default path is byte-for-byte the old behaviour: live file rewritten, no draft."""
    prime = _prime(tmp_path)
    result = SkillRefiner()._append_refinement(prime, _signal())

    assert result == prime
    assert "1.0.1" in prime.read_text()
    assert not (tmp_path / "TEST_PRIME.draft.md").exists()


def test_rejecting_gate_leaves_live_file_untouched(tmp_path):
    """DISCRIMINATING. An implementation that ignores the gate rewrites the live file and FAILS here.

    This is the whole point: rejection must be observable as the ABSENCE of a change to the live
    instructions, not merely as a log line next to a completed write.
    """
    prime = _prime(tmp_path)
    before = prime.read_text()

    result = SkillRefiner(promotion_gate=lambda draft, live: False)._append_refinement(
        prime, _signal()
    )

    assert result is None, "a rejected refinement must not report a refined path"
    assert prime.read_text() == before, "REJECTED refinement still mutated the live PRIME file"
    assert "1.0.1" not in prime.read_text()

    draft = tmp_path / "TEST_PRIME.draft.md"
    assert draft.exists(), "rejected draft must survive for inspection, not vanish"
    assert "1.0.1" in draft.read_text(), "the draft should carry the refinement that was rejected"


def test_approving_gate_promotes_and_removes_draft(tmp_path):
    prime = _prime(tmp_path)
    result = SkillRefiner(promotion_gate=lambda draft, live: True)._append_refinement(
        prime, _signal()
    )

    assert result == prime
    assert "1.0.1" in prime.read_text()
    assert not (tmp_path / "TEST_PRIME.draft.md").exists(), "promoted draft should be cleaned up"


def test_gate_sees_draft_content_and_live_file(tmp_path):
    """The gate must receive the CANDIDATE, not just a path to the unchanged live file.

    A gate that cannot read what it is approving is a rubber stamp -- the `save_validated_query`
    failure mode in a different costume.
    """
    prime = _prime(tmp_path)
    seen: dict[str, str] = {}

    def gate(draft: Path, live: Path) -> bool:
        seen["draft"] = draft.read_text()
        seen["live"] = live.read_text()
        return True

    SkillRefiner(promotion_gate=gate)._append_refinement(prime, _signal())

    assert "1.0.1" in seen["draft"], "gate must see the candidate version"
    assert "1.0.0" in seen["live"], "gate must see the current live version to compare against"
    assert seen["draft"] != seen["live"]


def test_raising_gate_fails_closed(tmp_path):
    """A gate that ERRORS must not be read as approval.

    Inverts the module's usual fail-open convention on purpose: the guarded action rewrites the
    instructions steering every future run.
    """
    prime = _prime(tmp_path)
    before = prime.read_text()

    def gate(draft: Path, live: Path) -> bool:
        raise RuntimeError("harness unavailable")

    result = SkillRefiner(promotion_gate=gate)._append_refinement(prime, _signal())

    assert result is None
    assert prime.read_text() == before, "a broken gate must never promote"
    assert (tmp_path / "TEST_PRIME.draft.md").exists()
