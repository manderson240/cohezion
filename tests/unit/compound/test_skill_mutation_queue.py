"""Tests for SkillMutationQueue — S5 harness invariant and bi-temporal semantics."""

from __future__ import annotations

from datetime import UTC, datetime

from cohezion.compound.skill_mutation_queue import SkillMutation, SkillMutationQueue


class TestSkillMutation:
    def test_is_valid_at_true_when_pending(self):
        m = SkillMutation(mutation_id="a", skill_name="s", patch="p")
        assert m.is_valid_at() is True

    def test_is_valid_at_false_after_rejection(self):
        m = SkillMutation(mutation_id="a", skill_name="s", patch="p", status="rejected")
        assert m.is_valid_at() is False

    def test_is_valid_at_false_when_valid_to_in_past(self):
        past = datetime(2000, 1, 1, tzinfo=UTC)
        m = SkillMutation(mutation_id="a", skill_name="s", patch="p", valid_to=past)
        assert m.is_valid_at() is False

    def test_is_valid_at_true_when_valid_to_in_future(self):
        future = datetime(2099, 1, 1, tzinfo=UTC)
        m = SkillMutation(mutation_id="a", skill_name="s", patch="p", valid_to=future)
        assert m.is_valid_at() is True

    def test_is_valid_at_respects_when_parameter(self):
        t1 = datetime(2026, 1, 1, tzinfo=UTC)
        t2 = datetime(2026, 6, 1, tzinfo=UTC)
        m = SkillMutation(mutation_id="a", skill_name="s", patch="p", valid_from=t2)
        assert m.is_valid_at(t1) is False  # before valid_from
        assert m.is_valid_at(datetime(2026, 12, 1, tzinfo=UTC)) is True


class TestSkillMutationQueue:
    def test_enqueue_returns_mutation_id(self):
        q = SkillMutationQueue()
        mid = q.enqueue("my-skill", "patch content")
        assert isinstance(mid, str)
        assert len(mid) > 8

    def test_enqueue_creates_pending_mutation(self):
        q = SkillMutationQueue()
        mid = q.enqueue("test-skill", "--- patch ---", reason="improve docstring")
        m = q.get(mid)
        assert m is not None
        assert m.status == "pending"
        assert m.skill_name == "test-skill"
        assert m.reason == "improve docstring"

    def test_count_pending(self):
        q = SkillMutationQueue()
        assert q.count_pending() == 0
        q.enqueue("s1", "p1")
        q.enqueue("s2", "p2")
        assert q.count_pending() == 2

    def test_approve_sets_status_approved(self):
        q = SkillMutationQueue()
        mid = q.enqueue("skill", "patch")
        assert q.approve(mid) is True
        assert q.get(mid).status == "approved"

    def test_approve_unknown_id_returns_false(self):
        q = SkillMutationQueue()
        assert q.approve("nonexistent-id") is False

    def test_approve_already_approved_returns_false(self):
        q = SkillMutationQueue()
        mid = q.enqueue("s", "p")
        q.approve(mid)
        assert q.approve(mid) is False  # already approved, not pending

    # S5 harness invariant: is_valid_at() == False after refund
    def test_is_valid_at_false_after_refund(self):
        """S5: refund(mutation_id) must make is_valid_at() return False."""
        q = SkillMutationQueue()
        mid = q.enqueue("test-skill", "some patch")
        m = q.get(mid)

        # Sanity: valid before refund
        assert m.is_valid_at() is True

        # Refund
        result = q.refund(mid)
        assert result is True

        # S5 invariant: is_valid_at() must be False after refund
        assert not m.is_valid_at(), "S5 VIOLATED: mutation still valid after refund"
        assert m.status == "rejected"
        assert m.valid_to is not None

    def test_refund_preserves_mutation_record(self):
        """Bi-temporal: refund NEVER deletes the record (enables time-travel recovery)."""
        q = SkillMutationQueue()
        mid = q.enqueue("skill", "patch")
        q.refund(mid)
        # Record must still exist
        assert q.get(mid) is not None

    def test_refund_sets_valid_to_timestamp(self):
        q = SkillMutationQueue()
        mid = q.enqueue("skill", "patch")
        before = datetime.now(UTC)
        q.refund(mid)
        after = datetime.now(UTC)
        m = q.get(mid)
        assert m.valid_to is not None
        assert before <= m.valid_to <= after

    def test_refund_unknown_id_returns_false(self):
        q = SkillMutationQueue()
        assert q.refund("not-a-real-id") is False

    def test_pending_list_excludes_approved_and_rejected(self):
        q = SkillMutationQueue()
        m1 = q.enqueue("s1", "p1")
        m2 = q.enqueue("s2", "p2")
        m3 = q.enqueue("s3", "p3")
        q.approve(m1)
        q.refund(m2)
        pending = [m.mutation_id for m in q.pending()]
        assert m3 in pending
        assert m1 not in pending
        assert m2 not in pending

    def test_approved_list_returns_only_approved(self):
        q = SkillMutationQueue()
        m1 = q.enqueue("s1", "p1")
        m2 = q.enqueue("s2", "p2")
        q.approve(m1)
        approved = [m.mutation_id for m in q.approved()]
        assert m1 in approved
        assert m2 not in approved

    def test_persist_writes_to_surreal(self):
        from cohezion.core.persistence.surreal_client import get_surreal_client

        client = get_surreal_client()
        client._use_fallback()
        client._client._data.clear()

        q = SkillMutationQueue(persist=True)
        mid = q.enqueue("persist-skill", "patch contents", reason="testing persist")

        m = q.get(mid)
        assert m is not None

        stored = client._client.get(f"pending_mutations:{mid}")
        assert stored is not None
        assert stored["mutation_id"] == mid
        assert stored["skill_name"] == "persist-skill"
        assert stored["status"] == "pending"
        assert stored["reason"] == "testing persist"

    def test_persist_approve_updates_surreal(self):
        from cohezion.core.persistence.surreal_client import get_surreal_client

        client = get_surreal_client()
        client._use_fallback()
        client._client._data.clear()

        q = SkillMutationQueue(persist=True)
        mid = q.enqueue("persist-skill", "patch contents")

        assert q.approve(mid) is True

        stored = client._client.get(f"pending_mutations:{mid}")
        assert stored is not None
        assert stored["status"] == "approved"

    def test_persist_refund_updates_surreal(self):
        from cohezion.core.persistence.surreal_client import get_surreal_client

        client = get_surreal_client()
        client._use_fallback()
        client._client._data.clear()

        q = SkillMutationQueue(persist=True)
        mid = q.enqueue("persist-skill", "patch contents")

        assert q.refund(mid) is True

        stored = client._client.get(f"pending_mutations:{mid}")
        assert stored is not None
        assert stored["status"] == "rejected"
        assert stored["valid_to"] is not None
