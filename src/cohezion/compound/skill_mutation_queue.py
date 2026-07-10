"""SkillMutationQueue — bi-temporal HITL batching for skill refinements.

Harness invariant S5: refund(mutation_id) sets valid_to=now() and status=rejected.
After refund, is_valid_at() must return False for that mutation.

All mutations have:
  - valid_from: datetime when mutation was created
  - valid_to: datetime when mutation was superseded/rejected (None = currently valid)
  - status: pending | approved | rejected

Bi-temporal design:
  - valid_from/valid_to tracks when the mutation was VALID in the system
  - Refund = set valid_to = now(), status = rejected (SurrealDB time-travel recovers prior state)
  - Pending mutations await human approval before applying to skill files
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class SkillMutation:
    """A pending or applied skill file mutation."""

    mutation_id: str
    skill_name: str
    patch: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    valid_from: datetime = field(default_factory=_now)
    valid_to: datetime | None = None
    reason: str = ""

    def is_valid_at(self, when: datetime | None = None) -> bool:
        """True when this mutation is currently active.

        A mutation is active if:
        - valid_from <= when
        - valid_to is None OR valid_to > when
        - status is not 'rejected'
        """
        when = when or _now()
        if self.status == "rejected":
            return False
        if self.valid_from > when:
            return False
        return self.valid_to is None or self.valid_to > when


class SkillMutationQueue:
    """In-memory bi-temporal queue for skill mutations.

    When SurrealDB is available, mutations are persisted to the
    pending_mutations table with full bi-temporal schema.
    Falls back to in-memory storage without raising.
    """

    def __init__(self, persist: bool = False) -> None:
        self._mutations: dict[str, SkillMutation] = {}
        self._persist = persist

    def enqueue(self, skill_name: str, patch: str, reason: str = "") -> str:
        """Add a new pending mutation. Returns mutation_id."""
        mutation_id = str(uuid.uuid4())
        m = SkillMutation(
            mutation_id=mutation_id,
            skill_name=skill_name,
            patch=patch,
            reason=reason,
        )
        self._mutations[mutation_id] = m
        logger.info("SkillMutation enqueued: %s skill=%s", mutation_id[:8], skill_name)
        if self._persist:
            self._write_surreal(m)
        return mutation_id

    def approve(self, mutation_id: str) -> bool:
        """Approve a pending mutation. Returns True if found and updated."""
        m = self._mutations.get(mutation_id)
        if m is None or m.status != "pending":
            return False
        m.status = "approved"
        logger.info("SkillMutation approved: %s", mutation_id[:8])
        if self._persist:
            self._update_surreal(m)
        return True

    def expire_stale(self, ttl_hours: float = 168.0) -> int:
        """TTL/decay contract (AOEP mutability axis): retire pending mutations
        older than *ttl_hours* via bi-temporal soft-delete (valid_to=now,
        status=expired). Returns the number expired. History is preserved —
        is_valid_at() before expiry still returns True (time-travel intact).
        """
        from datetime import timedelta

        now = _now()
        cutoff = now - timedelta(hours=ttl_hours)
        expired = 0
        for m in self._mutations.values():
            if m.valid_to is None and m.status == "pending" and m.valid_from <= cutoff:
                m.valid_to = now
                m.status = "expired"
                expired += 1
                if self._persist:
                    self._update_surreal(m)
        return expired

    def refund(self, mutation_id: str) -> bool:
        """Reject a mutation bi-temporally: valid_to=now(), status=rejected.

        S5 harness invariant: after refund, is_valid_at() must return False.
        The mutation record is preserved (never deleted) so SurrealDB
        time-travel can recover the prior state.
        """
        m = self._mutations.get(mutation_id)
        if m is None:
            return False
        m.valid_to = _now()
        m.status = "rejected"
        logger.info("SkillMutation refunded: %s (valid_to=%s)", mutation_id[:8], m.valid_to)
        if self._persist:
            self._update_surreal(m)
        return True

    def get(self, mutation_id: str) -> SkillMutation | None:
        return self._mutations.get(mutation_id)

    def count_pending(self) -> int:
        return sum(1 for m in self._mutations.values() if m.status == "pending")

    def pending(self) -> list[SkillMutation]:
        return [m for m in self._mutations.values() if m.status == "pending"]

    def approved(self) -> list[SkillMutation]:
        return [m for m in self._mutations.values() if m.status == "approved"]

    def _run_async(self, coro) -> Any:
        """Run an async coroutine synchronously, handling running loop if present."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import threading
            from concurrent.futures import Future

            res_future: Future[Any] = Future()

            def run():
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    val = new_loop.run_until_complete(coro)
                    res_future.set_result(val)
                except Exception as e:
                    res_future.set_exception(e)
                finally:
                    new_loop.close()

            t = threading.Thread(target=run)
            t.start()
            t.join()
            return res_future.result()
        else:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)

    def _write_surreal(self, m: SkillMutation) -> None:
        try:
            from cohezion.core.persistence.surreal_client import get_surreal_client

            client = get_surreal_client()
            coro = client.create(
                f"pending_mutations:{m.mutation_id}",
                {
                    "id": f"pending_mutations:{m.mutation_id}",
                    "mutation_id": m.mutation_id,
                    "skill_name": m.skill_name,
                    "patch": m.patch[:10000],
                    "status": m.status,
                    "valid_from": m.valid_from.isoformat(),
                    "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                    "reason": m.reason,
                },
            )
            self._run_async(coro)
        except Exception as exc:
            logger.debug("SkillMutationQueue: SurrealDB persist skipped: %s", exc)

    def _update_surreal(self, m: SkillMutation) -> None:
        try:
            from cohezion.core.persistence.surreal_client import get_surreal_client

            client = get_surreal_client()
            sql = "UPDATE pending_mutations SET status = $status, valid_to = $valid_to WHERE mutation_id = $mutation_id"
            coro = client.query(
                sql,
                {
                    "status": m.status,
                    "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                    "mutation_id": m.mutation_id,
                },
            )
            self._run_async(coro)
        except Exception as exc:
            logger.debug("SkillMutationQueue: SurrealDB update skipped: %s", exc)
