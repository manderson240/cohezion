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
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Optional


logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


# ── HITL Batch API enums ──────────────────────────────────────────────────────


class ChangeType(str, Enum):
    HYPERPARAMETER = "hyperparameter"
    ARCHITECTURE = "architecture"
    CORPUS = "corpus"
    ROUTING = "routing"


class MutationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BatchStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    FLUSHED = "flushed"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


def compute_semantic_hash(diff_text: str, change_type: ChangeType) -> str:
    """64-char hex hash of diff content, order-invariant over lines."""
    lines = sorted(diff_text.strip().splitlines())
    canonical = "\n".join(lines) + f"\n{change_type.value}"
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class PendingMutation:
    id: str
    skill_path: str
    change_type: ChangeType
    diff_text: str
    semantic_hash: str
    proposed_by_agent: str
    created_at: datetime
    valid_from: datetime
    valid_to: Optional[datetime] = None
    status: MutationStatus = MutationStatus.PENDING
    batch_id: Optional[str] = None

    def is_valid_at(self, ts: datetime) -> bool:
        if self.status == MutationStatus.REJECTED:
            return False
        if ts < self.valid_from:
            return False
        return self.valid_to is None or ts < self.valid_to

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_path": self.skill_path,
            "change_type": self.change_type.value,
            "diff_text": self.diff_text,
            "semantic_hash": self.semantic_hash,
            "proposed_by_agent": self.proposed_by_agent,
            "created_at": self.created_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "status": self.status.value,
            "batch_id": self.batch_id,
        }


@dataclass
class ApprovalCacheEntry:
    semantic_hash: str
    decision: ApprovalDecision
    approved_by: str
    cached_at: datetime
    applies_to_pattern: str
    ttl_seconds: Optional[int] = None
    hit_count: int = 0

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if self.ttl_seconds is None:
            return False
        elapsed = ((now or _now()) - self.cached_at).total_seconds()
        return elapsed > self.ttl_seconds


@dataclass
class BatchCheckpoint:
    batch_id: str
    session_id: str
    mutations: list
    mutation_count: int
    status: BatchStatus = BatchStatus.PENDING
    presented_at: Optional[datetime] = None
    flushed_at: Optional[datetime] = None


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

    def __init__(self, persist: bool = False, enable_persistence: bool = False) -> None:
        self._mutations: dict[str, SkillMutation] = {}
        self._persist = persist or enable_persistence
        # HITL batch API stores (separate from legacy sync _mutations)
        self._pending: dict[str, PendingMutation] = {}
        self._approval_cache: dict[str, ApprovalCacheEntry] = {}
        self._batches: dict[str, BatchCheckpoint] = {}

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

    # ── HITL Batch API (async) ────────────────────────────────────────────────

    async def propose_mutation(
        self,
        skill_path: str,
        change_type: ChangeType,
        diff_text: str,
        proposed_by_agent: str,
        valid_from: Optional[datetime] = None,
    ) -> PendingMutation:
        """Propose a skill mutation; deduplicates by (skill_path, semantic_hash)."""
        semantic_hash = compute_semantic_hash(diff_text, change_type)
        for existing in self._pending.values():
            if existing.skill_path == skill_path and existing.semantic_hash == semantic_hash:
                return existing
        now = _now()
        mut = PendingMutation(
            id=str(uuid.uuid4()),
            skill_path=skill_path,
            change_type=change_type,
            diff_text=diff_text,
            semantic_hash=semantic_hash,
            proposed_by_agent=proposed_by_agent,
            created_at=now,
            valid_from=valid_from or now,
        )
        self._pending[mut.id] = mut
        logger.info("PendingMutation proposed: %s skill=%s", mut.id[:8], skill_path)
        return mut

    async def get_pending_mutations(
        self,
        skill_path: Optional[str] = None,
        change_type: Optional[ChangeType] = None,
    ) -> list[PendingMutation]:
        """Return pending mutations, optionally filtered by skill_path or change_type."""
        result = [m for m in self._pending.values() if m.status == MutationStatus.PENDING]
        if skill_path is not None:
            result = [m for m in result if m.skill_path == skill_path]
        if change_type is not None:
            result = [m for m in result if m.change_type == change_type]
        return result

    async def check_approval_cache(self, semantic_hash: str) -> Optional[ApprovalCacheEntry]:
        """Look up a cached approval decision; returns None on miss or expiry."""
        entry = self._approval_cache.get(semantic_hash)
        if entry is None:
            return None
        if entry.is_expired():
            return None
        entry.hit_count += 1
        return entry

    async def cache_approval(
        self,
        semantic_hash: str,
        decision: ApprovalDecision,
        approved_by: str,
        ttl_seconds: Optional[int] = None,
        applies_to_pattern: str = "*",
    ) -> ApprovalCacheEntry:
        """Cache an approval decision for a semantic hash."""
        entry = ApprovalCacheEntry(
            semantic_hash=semantic_hash,
            decision=decision,
            approved_by=approved_by,
            cached_at=_now(),
            applies_to_pattern=applies_to_pattern,
            ttl_seconds=ttl_seconds,
        )
        self._approval_cache[semantic_hash] = entry
        return entry

    async def create_batch(self, session_id: str, mutation_ids: list[str]) -> BatchCheckpoint:
        """Group mutations into a batch checkpoint for human review."""
        unknown = [mid for mid in mutation_ids if mid not in self._pending]
        if unknown:
            raise ValueError(f"Unknown mutation IDs: {unknown}")
        batch_id = str(uuid.uuid4())
        batch = BatchCheckpoint(
            batch_id=batch_id,
            session_id=session_id,
            mutations=list(mutation_ids),
            mutation_count=len(mutation_ids),
        )
        self._batches[batch_id] = batch
        for mid in mutation_ids:
            self._pending[mid].batch_id = batch_id
        logger.info("BatchCheckpoint created: %s (%d mutations)", batch_id[:8], len(mutation_ids))
        return batch

    async def mark_reviewed(self, batch_id: str) -> BatchCheckpoint:
        """Transition batch PENDING→REVIEWED; sets presented_at timestamp."""
        batch = self._batches[batch_id]
        batch.status = BatchStatus.REVIEWED
        batch.presented_at = _now()
        return batch

    async def flush_batch(self, batch_id: str) -> int:
        """Apply cached approval decisions to mutations in the batch.

        Requires REVIEWED state. Returns count of approved mutations.
        Sets batch status to FLUSHED with flushed_at timestamp.
        """
        batch = self._batches[batch_id]
        if batch.status != BatchStatus.REVIEWED:
            raise ValueError(
                f"Batch {batch_id} must be in REVIEWED state to flush (current: {batch.status})"
            )
        approved_count = 0
        for mid in batch.mutations:
            mut = self._pending.get(mid)
            if mut is None:
                continue
            cached = self._approval_cache.get(mut.semantic_hash)
            if cached is not None and not cached.is_expired():
                if cached.decision == ApprovalDecision.APPROVED:
                    mut.status = MutationStatus.APPROVED
                    approved_count += 1
                elif cached.decision == ApprovalDecision.REJECTED:
                    mut.status = MutationStatus.REJECTED
        batch.status = BatchStatus.FLUSHED
        batch.flushed_at = _now()
        logger.info("BatchCheckpoint flushed: %s (approved=%d)", batch_id[:8], approved_count)
        return approved_count

    def get_batch(self, batch_id: str) -> Optional[BatchCheckpoint]:
        """Sync accessor for a batch checkpoint."""
        return self._batches.get(batch_id)

    def get_metrics(self) -> dict:
        """Return summary metrics for the HITL batch queue."""
        return {
            "total_mutations": len(self._pending),
            "pending": sum(1 for m in self._pending.values() if m.status == MutationStatus.PENDING),
            "approved": sum(
                1 for m in self._pending.values() if m.status == MutationStatus.APPROVED
            ),
            "approval_cache_size": len(self._approval_cache),
            "flushed_batches": sum(
                1 for b in self._batches.values() if b.status == BatchStatus.FLUSHED
            ),
        }

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
