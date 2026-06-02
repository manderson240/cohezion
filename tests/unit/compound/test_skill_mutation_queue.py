"""Unit tests for SkillMutationQueue and its bi-temporal S5 invariants."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from cohezion.compound.skill_mutation_queue import SkillMutation, SkillMutationQueue


@pytest.mark.unit
class TestSkillMutation:
    """Tests for individual SkillMutation properties and bi-temporal validity."""

    def test_mutation_default_state(self) -> None:
        m = SkillMutation(
            mutation_id="mut-1",
            skill_name="test_skill_PRIME",
            patch="diff --git ...",
            reason="test reason",
        )
        assert m.status == "pending"
        assert m.valid_to is None
        assert m.valid_from <= datetime.now(UTC)

    def test_is_valid_at_now(self) -> None:
        m = SkillMutation(
            mutation_id="mut-1",
            skill_name="test_skill_PRIME",
            patch="diff --git ...",
        )
        assert m.is_valid_at() is True

    def test_is_valid_at_future_and_past(self) -> None:
        now = datetime.now(UTC)
        m = SkillMutation(
            mutation_id="mut-1",
            skill_name="test_skill_PRIME",
            patch="diff --git ...",
            valid_from=now,
        )
        # Past should be invalid
        assert m.is_valid_at(now - timedelta(seconds=5)) is False
        # Future/present should be valid
        assert m.is_valid_at(now + timedelta(seconds=5)) is True

    def test_is_valid_at_rejected(self) -> None:
        m = SkillMutation(
            mutation_id="mut-1",
            skill_name="test_skill_PRIME",
            patch="diff --git ...",
            status="rejected",
        )
        assert m.is_valid_at() is False


@pytest.mark.unit
class TestSkillMutationQueue:
    """Tests for SkillMutationQueue operations."""

    def test_enqueue_and_get(self) -> None:
        queue = SkillMutationQueue(persist=False)
        mut_id = queue.enqueue(
            skill_name="math_reasoning_PRIME",
            patch="patch data",
            reason="optimizing loop",
        )
        assert mut_id is not None
        assert len(mut_id) > 0

        m = queue.get(mut_id)
        assert m is not None
        assert m.mutation_id == mut_id
        assert m.skill_name == "math_reasoning_PRIME"
        assert m.patch == "patch data"
        assert m.reason == "optimizing loop"
        assert m.status == "pending"

    def test_approve_updates_status(self) -> None:
        queue = SkillMutationQueue(persist=False)
        mut_id = queue.enqueue(
            skill_name="math_reasoning_PRIME",
            patch="patch data",
        )

        assert queue.count_pending() == 1
        assert len(queue.pending()) == 1
        assert len(queue.approved()) == 0

        success = queue.approve(mut_id)
        assert success is True

        m = queue.get(mut_id)
        assert m is not None
        assert m.status == "approved"
        assert queue.count_pending() == 0
        assert len(queue.pending()) == 0
        assert len(queue.approved()) == 1

        # Double approval should fail/return False
        assert queue.approve(mut_id) is False

    def test_refund_supersedes_and_rejects(self) -> None:
        """S5 harness invariant: refund(mutation_id) must set valid_to=now() and status=rejected."""
        queue = SkillMutationQueue(persist=False)
        mut_id = queue.enqueue(
            skill_name="math_reasoning_PRIME",
            patch="patch data",
        )

        m = queue.get(mut_id)
        assert m is not None
        assert m.valid_to is None
        assert m.status == "pending"

        t_before = datetime.now(UTC)
        time.sleep(0.01)  # small sleep to ensure temporal delta

        success = queue.refund(mut_id)
        assert success is True

        t_after = datetime.now(UTC)

        assert m.status == "rejected"
        assert m.valid_to is not None
        assert t_before <= m.valid_to <= t_after

    def test_is_valid_at_false_after_refund(self) -> None:
        """bi-temporal: is_valid_at() must return False after refund."""
        queue = SkillMutationQueue(persist=False)
        mut_id = queue.enqueue(
            skill_name="math_reasoning_PRIME",
            patch="patch data",
        )

        m = queue.get(mut_id)
        assert m is not None
        assert m.is_valid_at() is True

        queue.refund(mut_id)
        assert m.is_valid_at() is False
        # Even when querying historical timestamps after refund time, it should be false because status is rejected
        assert m.is_valid_at(datetime.now(UTC) + timedelta(seconds=10)) is False
