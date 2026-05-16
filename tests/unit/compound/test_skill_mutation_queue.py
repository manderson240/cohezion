"""Unit tests for SkillMutationQueue — HITL batching layer.

All tests run without a live SurrealDB (enable_persistence=False).
Covers: propose_mutation, dedup, approval cache, batch lifecycle,
bi-temporal validity, semantic_hash determinism, and metrics.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_queue():
    from cohezion.compound.skill_mutation_queue import SkillMutationQueue

    return SkillMutationQueue(enable_persistence=False)


def _run(coro):
    return asyncio.run(coro)


SKILL = "src/cohezion/skills/CODE_REVIEW_PRIME.md"
AGENT = "SkillRefiner-test"
DIFF = "@@ -1,3 +1,4 @@\n+temperature: 0.3\n context: review\n"


# ---------------------------------------------------------------------------
# compute_semantic_hash
# ---------------------------------------------------------------------------


class TestComputeSemanticHash:
    def test_deterministic_for_same_input(self):
        from cohezion.compound.skill_mutation_queue import ChangeType, compute_semantic_hash

        h1 = compute_semantic_hash(DIFF, ChangeType.HYPERPARAMETER)
        h2 = compute_semantic_hash(DIFF, ChangeType.HYPERPARAMETER)
        assert h1 == h2

    def test_different_change_types_produce_different_hashes(self):
        from cohezion.compound.skill_mutation_queue import ChangeType, compute_semantic_hash

        h_hp = compute_semantic_hash(DIFF, ChangeType.HYPERPARAMETER)
        h_arch = compute_semantic_hash(DIFF, ChangeType.ARCHITECTURE)
        assert h_hp != h_arch

    def test_reordered_lines_same_hash(self):
        """Semantically equivalent diffs that differ only in line order hash identically."""
        from cohezion.compound.skill_mutation_queue import ChangeType, compute_semantic_hash

        diff_a = "+line1\n+line2\n"
        diff_b = "+line2\n+line1\n"
        assert compute_semantic_hash(diff_a, ChangeType.CORPUS) == compute_semantic_hash(diff_b, ChangeType.CORPUS)

    def test_different_content_different_hash(self):
        from cohezion.compound.skill_mutation_queue import ChangeType, compute_semantic_hash

        h1 = compute_semantic_hash("+temp: 0.3\n", ChangeType.HYPERPARAMETER)
        h2 = compute_semantic_hash("+temp: 0.9\n", ChangeType.HYPERPARAMETER)
        assert h1 != h2

    def test_returns_hex_string_64_chars(self):
        from cohezion.compound.skill_mutation_queue import ChangeType, compute_semantic_hash

        h = compute_semantic_hash(DIFF, ChangeType.ROUTING)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# PendingMutation
# ---------------------------------------------------------------------------


class TestPendingMutation:
    def test_fields_stored_correctly(self):
        from cohezion.compound.skill_mutation_queue import (
            ChangeType,
            MutationStatus,
            PendingMutation,
            compute_semantic_hash,
        )

        now = datetime.now(UTC)
        mut = PendingMutation(
            id="test-id",
            skill_path=SKILL,
            change_type=ChangeType.HYPERPARAMETER,
            diff_text=DIFF,
            semantic_hash=compute_semantic_hash(DIFF, ChangeType.HYPERPARAMETER),
            proposed_by_agent=AGENT,
            created_at=now,
            valid_from=now,
        )
        assert mut.status == MutationStatus.PENDING
        assert mut.valid_to is None
        assert mut.batch_id is None

    def test_is_valid_at_within_range(self):
        from cohezion.compound.skill_mutation_queue import (
            ChangeType,
            PendingMutation,
            compute_semantic_hash,
        )

        now = datetime.now(UTC)
        mut = PendingMutation(
            id="v1",
            skill_path=SKILL,
            change_type=ChangeType.CORPUS,
            diff_text=DIFF,
            semantic_hash=compute_semantic_hash(DIFF, ChangeType.CORPUS),
            proposed_by_agent=AGENT,
            created_at=now,
            valid_from=now - timedelta(hours=1),
            valid_to=now + timedelta(hours=1),
        )
        assert mut.is_valid_at(now) is True

    def test_is_valid_at_before_valid_from(self):
        from cohezion.compound.skill_mutation_queue import (
            ChangeType,
            PendingMutation,
            compute_semantic_hash,
        )

        now = datetime.now(UTC)
        future = now + timedelta(hours=2)
        mut = PendingMutation(
            id="v2",
            skill_path=SKILL,
            change_type=ChangeType.CORPUS,
            diff_text=DIFF,
            semantic_hash=compute_semantic_hash(DIFF, ChangeType.CORPUS),
            proposed_by_agent=AGENT,
            created_at=now,
            valid_from=future,
        )
        assert mut.is_valid_at(now) is False

    def test_is_valid_at_after_valid_to(self):
        from cohezion.compound.skill_mutation_queue import (
            ChangeType,
            PendingMutation,
            compute_semantic_hash,
        )

        now = datetime.now(UTC)
        mut = PendingMutation(
            id="v3",
            skill_path=SKILL,
            change_type=ChangeType.CORPUS,
            diff_text=DIFF,
            semantic_hash=compute_semantic_hash(DIFF, ChangeType.CORPUS),
            proposed_by_agent=AGENT,
            created_at=now,
            valid_from=now - timedelta(hours=2),
            valid_to=now - timedelta(hours=1),
        )
        assert mut.is_valid_at(now) is False

    def test_to_dict_roundtrip_keys(self):
        from cohezion.compound.skill_mutation_queue import (
            ChangeType,
            PendingMutation,
            compute_semantic_hash,
        )

        now = datetime.now(UTC)
        mut = PendingMutation(
            id="t1",
            skill_path=SKILL,
            change_type=ChangeType.ARCHITECTURE,
            diff_text=DIFF,
            semantic_hash=compute_semantic_hash(DIFF, ChangeType.ARCHITECTURE),
            proposed_by_agent=AGENT,
            created_at=now,
            valid_from=now,
        )
        d = mut.to_dict()
        for key in (
            "id",
            "skill_path",
            "change_type",
            "diff_text",
            "semantic_hash",
            "proposed_by_agent",
            "created_at",
            "valid_from",
            "valid_to",
            "status",
            "batch_id",
        ):
            assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# propose_mutation
# ---------------------------------------------------------------------------


class TestProposeMutation:
    def test_propose_creates_pending_mutation(self):
        from cohezion.compound.skill_mutation_queue import ChangeType, MutationStatus

        q = _make_queue()
        mut = _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        assert mut.skill_path == SKILL
        assert mut.change_type == ChangeType.HYPERPARAMETER
        assert mut.status == MutationStatus.PENDING
        assert len(mut.id) > 0
        assert len(mut.semantic_hash) == 64

    def test_propose_deduplicates_identical_mutations(self):
        """Second identical proposal returns the first mutation unchanged."""
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        m1 = _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        m2 = _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        assert m1.id == m2.id

    def test_different_skill_paths_not_deduped(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        m1 = _run(q.propose_mutation("skill_a.md", ChangeType.CORPUS, DIFF, AGENT))
        m2 = _run(q.propose_mutation("skill_b.md", ChangeType.CORPUS, DIFF, AGENT))
        assert m1.id != m2.id

    def test_propose_assigns_valid_from_default_now(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        before = datetime.now(UTC)
        q = _make_queue()
        mut = _run(q.propose_mutation(SKILL, ChangeType.ROUTING, DIFF, AGENT))
        after = datetime.now(UTC)
        assert before <= mut.valid_from <= after

    def test_get_pending_mutations_returns_proposed(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        pending = _run(q.get_pending_mutations())
        assert len(pending) == 1

    def test_get_pending_filtered_by_skill_path(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        _run(q.propose_mutation("skill_a.md", ChangeType.CORPUS, DIFF, AGENT))
        _run(q.propose_mutation("skill_b.md", ChangeType.CORPUS, DIFF + " extra", AGENT))
        result = _run(q.get_pending_mutations(skill_path="skill_a.md"))
        assert len(result) == 1
        assert result[0].skill_path == "skill_a.md"

    def test_get_pending_filtered_by_change_type(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        _run(q.propose_mutation(SKILL, ChangeType.ARCHITECTURE, DIFF + " x", AGENT))
        result = _run(q.get_pending_mutations(change_type=ChangeType.HYPERPARAMETER))
        assert len(result) == 1
        assert result[0].change_type == ChangeType.HYPERPARAMETER


# ---------------------------------------------------------------------------
# ApprovalCacheEntry and check_approval_cache
# ---------------------------------------------------------------------------


class TestApprovalCache:
    def test_cache_miss_returns_none(self):
        q = _make_queue()
        result = _run(q.check_approval_cache("nonexistent-hash"))
        assert result is None

    def test_cache_hit_returns_entry(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision

        q = _make_queue()
        _run(q.cache_approval("abc123", ApprovalDecision.APPROVED, "human"))
        entry = _run(q.check_approval_cache("abc123"))
        assert entry is not None
        assert entry.decision == ApprovalDecision.APPROVED

    def test_cache_hit_increments_hit_count(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision

        q = _make_queue()
        _run(q.cache_approval("h1", ApprovalDecision.REJECTED, "human"))
        _run(q.check_approval_cache("h1"))
        _run(q.check_approval_cache("h1"))
        entry = q._approval_cache["h1"]
        assert entry.hit_count == 2

    def test_expired_entry_returns_none(self):
        from cohezion.compound.skill_mutation_queue import ApprovalCacheEntry, ApprovalDecision

        q = _make_queue()
        # Manually insert an already-expired entry
        entry = ApprovalCacheEntry(
            semantic_hash="expired-hash",
            decision=ApprovalDecision.APPROVED,
            approved_by="human",
            cached_at=datetime.now(UTC) - timedelta(hours=2),
            applies_to_pattern="*",
            ttl_seconds=3600,  # 1 hour TTL, entry is 2 hours old
        )
        q._approval_cache["expired-hash"] = entry
        result = _run(q.check_approval_cache("expired-hash"))
        assert result is None

    def test_no_ttl_never_expires(self):
        from cohezion.compound.skill_mutation_queue import ApprovalCacheEntry, ApprovalDecision

        q = _make_queue()
        entry = ApprovalCacheEntry(
            semantic_hash="permanent",
            decision=ApprovalDecision.NEEDS_REVIEW,
            approved_by="system",
            cached_at=datetime.now(UTC) - timedelta(days=365),
            applies_to_pattern="*",
            ttl_seconds=None,
        )
        q._approval_cache["permanent"] = entry
        result = _run(q.check_approval_cache("permanent"))
        assert result is not None


# ---------------------------------------------------------------------------
# Batch lifecycle
# ---------------------------------------------------------------------------


class TestBatchCheckpoint:
    def _propose(self, q, diff_suffix=""):
        from cohezion.compound.skill_mutation_queue import ChangeType

        return _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF + diff_suffix, AGENT))

    def test_create_batch_contains_correct_ids(self):
        q = _make_queue()
        m1 = self._propose(q, " a")
        m2 = self._propose(q, " b")
        batch = _run(q.create_batch("session-1", [m1.id, m2.id]))
        assert set(batch.mutations) == {m1.id, m2.id}
        assert batch.mutation_count == 2
        assert batch.session_id == "session-1"

    def test_create_batch_unknown_id_raises(self):
        q = _make_queue()
        with pytest.raises(ValueError, match="Unknown mutation IDs"):
            _run(q.create_batch("s1", ["does-not-exist"]))

    def test_batch_initial_status_pending(self):
        from cohezion.compound.skill_mutation_queue import BatchStatus

        q = _make_queue()
        m = self._propose(q)
        batch = _run(q.create_batch("s2", [m.id]))
        assert batch.status == BatchStatus.PENDING

    def test_mark_reviewed_transitions_status(self):
        from cohezion.compound.skill_mutation_queue import BatchStatus

        q = _make_queue()
        m = self._propose(q)
        batch = _run(q.create_batch("s3", [m.id]))
        reviewed = _run(q.mark_reviewed(batch.batch_id))
        assert reviewed.status == BatchStatus.REVIEWED
        assert reviewed.presented_at is not None

    def test_flush_batch_requires_reviewed_state(self):
        q = _make_queue()
        m = self._propose(q)
        batch = _run(q.create_batch("s4", [m.id]))
        with pytest.raises(ValueError, match="REVIEWED state"):
            _run(q.flush_batch(batch.batch_id))

    def test_flush_batch_approves_cached_mutations(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision, ChangeType, MutationStatus

        q = _make_queue()
        m = _run(q.propose_mutation(SKILL, ChangeType.HYPERPARAMETER, DIFF, AGENT))
        # Cache the decision as approved
        _run(q.cache_approval(m.semantic_hash, ApprovalDecision.APPROVED, "human"))

        batch = _run(q.create_batch("s5", [m.id]))
        _run(q.mark_reviewed(batch.batch_id))
        approved_count = _run(q.flush_batch(batch.batch_id))

        assert approved_count == 1
        assert q._pending[m.id].status == MutationStatus.APPROVED

    def test_flush_batch_rejects_rejected_mutations(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision, ChangeType, MutationStatus

        q = _make_queue()
        m = _run(q.propose_mutation(SKILL, ChangeType.CORPUS, DIFF, AGENT))
        _run(q.cache_approval(m.semantic_hash, ApprovalDecision.REJECTED, "human"))

        batch = _run(q.create_batch("s6", [m.id]))
        _run(q.mark_reviewed(batch.batch_id))
        approved_count = _run(q.flush_batch(batch.batch_id))

        assert approved_count == 0
        assert q._pending[m.id].status == MutationStatus.REJECTED

    def test_flush_batch_sets_flushed_status(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision, BatchStatus, ChangeType

        q = _make_queue()
        m = _run(q.propose_mutation(SKILL, ChangeType.ROUTING, DIFF, AGENT))
        _run(q.cache_approval(m.semantic_hash, ApprovalDecision.APPROVED, "human"))
        batch = _run(q.create_batch("s7", [m.id]))
        _run(q.mark_reviewed(batch.batch_id))
        _run(q.flush_batch(batch.batch_id))

        updated = q.get_batch(batch.batch_id)
        assert updated.status == BatchStatus.FLUSHED
        assert updated.flushed_at is not None

    def test_create_batch_tags_mutations_with_batch_id(self):
        q = _make_queue()
        m = self._propose(q)
        batch = _run(q.create_batch("s8", [m.id]))
        assert q._pending[m.id].batch_id == batch.batch_id


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_initial_metrics_all_zero(self):
        q = _make_queue()
        m = q.get_metrics()
        assert m["total_mutations"] == 0
        assert m["pending"] == 0
        assert m["approval_cache_size"] == 0

    def test_metrics_reflect_proposals(self):
        from cohezion.compound.skill_mutation_queue import ChangeType

        q = _make_queue()
        _run(q.propose_mutation("s1.md", ChangeType.HYPERPARAMETER, DIFF, AGENT))
        _run(q.propose_mutation("s2.md", ChangeType.CORPUS, DIFF + " x", AGENT))
        m = q.get_metrics()
        assert m["total_mutations"] == 2
        assert m["pending"] == 2

    def test_metrics_reflect_cache_entry(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision

        q = _make_queue()
        _run(q.cache_approval("h1", ApprovalDecision.APPROVED, "human"))
        assert q.get_metrics()["approval_cache_size"] == 1

    def test_metrics_reflect_flushed_batch(self):
        from cohezion.compound.skill_mutation_queue import ApprovalDecision, ChangeType

        q = _make_queue()
        m = _run(q.propose_mutation(SKILL, ChangeType.ARCHITECTURE, DIFF, AGENT))
        _run(q.cache_approval(m.semantic_hash, ApprovalDecision.APPROVED, "human"))
        batch = _run(q.create_batch("session-metrics", [m.id]))
        _run(q.mark_reviewed(batch.batch_id))
        _run(q.flush_batch(batch.batch_id))

        metrics = q.get_metrics()
        assert metrics["flushed_batches"] == 1
        assert metrics["approved"] == 1
        assert metrics["pending"] == 0
