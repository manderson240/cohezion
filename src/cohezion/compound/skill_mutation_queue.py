"""SkillMutationQueue — HITL batching layer for the compound loop.

SkillRefiner writes proposed skill changes here instead of directly to disk.
SemanticCache L3 checks human_approval_cache before surfacing a mutation to
the human, reusing prior decisions on semantically identical diffs.
Batches flush at session boundary.

Schema: src/cohezion/persistence/skill_mutation_queue.surql
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


logger = logging.getLogger(__name__)

# SurrealDB connection defaults (matches existing surreal_logger.py pattern)
_DEFAULT_URL = "ws://localhost:8001/rpc"
_DEFAULT_NS = "cohezion"
_DEFAULT_DB = "compound"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ChangeType(StrEnum):
    HYPERPARAMETER = "hyperparameter"
    ARCHITECTURE = "architecture"
    CORPUS = "corpus"
    ROUTING = "routing"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class BatchStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    FLUSHED = "flushed"


class MutationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PendingMutation:
    """A proposed skill change awaiting human review."""

    id: str
    skill_path: str
    change_type: ChangeType
    diff_text: str
    semantic_hash: str
    proposed_by_agent: str
    created_at: datetime
    valid_from: datetime
    valid_to: datetime | None = None
    status: MutationStatus = MutationStatus.PENDING
    batch_id: str | None = None

    def is_valid_at(self, when: datetime | None = None) -> bool:
        """Return True if this mutation is temporally valid at `when` (default: now)."""
        t = when or datetime.now(UTC)
        if t < self.valid_from:
            return False
        if self.valid_to is not None and t >= self.valid_to:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "skill_path": self.skill_path,
            "change_type": str(self.change_type),
            "diff_text": self.diff_text,
            "semantic_hash": self.semantic_hash,
            "proposed_by_agent": self.proposed_by_agent,
            "created_at": self.created_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "status": str(self.status),
            "batch_id": self.batch_id,
        }


@dataclass
class ApprovalCacheEntry:
    """Memoised human decision keyed on semantic_hash."""

    semantic_hash: str
    decision: ApprovalDecision
    approved_by: str
    cached_at: datetime
    applies_to_pattern: str
    ttl_seconds: int | None = None
    hit_count: int = 0
    last_hit_at: datetime | None = None

    def is_expired(self) -> bool:
        """Return True if this cache entry has exceeded its TTL."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now(UTC) - self.cached_at).total_seconds()
        return age > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_hash": self.semantic_hash,
            "decision": str(self.decision),
            "approved_by": self.approved_by,
            "cached_at": self.cached_at.isoformat(),
            "applies_to_pattern": self.applies_to_pattern,
            "ttl_seconds": self.ttl_seconds,
            "hit_count": self.hit_count,
            "last_hit_at": self.last_hit_at.isoformat() if self.last_hit_at else None,
        }


@dataclass
class BatchCheckpoint:
    """A set of pending mutations collected for a single human review session."""

    batch_id: str
    session_id: str
    mutations: list[str]  # list of PendingMutation.id values
    status: BatchStatus
    mutation_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    presented_at: datetime | None = None
    flushed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "session_id": self.session_id,
            "mutations": self.mutations,
            "status": str(self.status),
            "mutation_count": self.mutation_count,
            "created_at": self.created_at.isoformat(),
            "presented_at": self.presented_at.isoformat() if self.presented_at else None,
            "flushed_at": self.flushed_at.isoformat() if self.flushed_at else None,
        }


# ---------------------------------------------------------------------------
# Hash utility
# ---------------------------------------------------------------------------


def compute_semantic_hash(diff_text: str, change_type: ChangeType) -> str:
    """Deterministic hash of semantically-normalised diff content.

    Normalisation strips leading/trailing whitespace and sorts diff lines so
    that reorderings of independent hunks hash identically. change_type is
    included so the same textual diff with different intent doesn't collapse.
    """
    lines = sorted(line.strip() for line in diff_text.splitlines() if line.strip())
    normalised = f"{change_type}::{chr(10).join(lines)}"
    return hashlib.sha256(normalised.encode()).hexdigest()


# ---------------------------------------------------------------------------
# SkillMutationQueue
# ---------------------------------------------------------------------------


class SkillMutationQueue:
    """HITL batching layer between SkillRefiner and skill files on disk.

    Usage (SkillRefiner side)::

        queue = SkillMutationQueue()
        mut = await queue.propose_mutation(
            skill_path="src/cohezion/skills/CODE_REVIEW_PRIME.md",
            change_type=ChangeType.HYPERPARAMETER,
            diff_text=diff,
            proposed_by_agent="SkillRefiner-v3",
        )

    Usage (SemanticCache L3 side)::

        cached = await queue.check_approval_cache(semantic_hash)
        if cached and not cached.is_expired():
            apply_decision(cached.decision)
        else:
            decision = await present_to_human(mut)
            await queue.cache_approval(semantic_hash, decision, approved_by="human")

    Session boundary flush::

        batch = await queue.create_batch(session_id, pending_ids)
        # ... human reviews ...
        n_flushed = await queue.flush_batch(batch.batch_id)
    """

    def __init__(
        self,
        url: str = _DEFAULT_URL,
        namespace: str = _DEFAULT_NS,
        database: str = _DEFAULT_DB,
        enable_persistence: bool = True,
    ) -> None:
        self._url = url
        self._namespace = namespace
        self._database = database
        self._enable_persistence = enable_persistence

        # In-process queues (used when persistence=False or as write-through cache)
        self._pending: dict[str, PendingMutation] = {}
        self._approval_cache: dict[str, ApprovalCacheEntry] = {}
        self._batches: dict[str, BatchCheckpoint] = {}

    # ------------------------------------------------------------------
    # Mutation proposals
    # ------------------------------------------------------------------

    async def propose_mutation(
        self,
        skill_path: str,
        change_type: ChangeType,
        diff_text: str,
        proposed_by_agent: str,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
    ) -> PendingMutation:
        """Enqueue a proposed skill change.

        Computes semantic_hash for dedup. If an identical mutation is already
        pending, returns the existing record rather than creating a duplicate.

        Returns the new (or existing) PendingMutation.
        """
        semantic_hash = compute_semantic_hash(diff_text, change_type)
        now = datetime.now(UTC)

        # Dedup: if identical hash already pending, return existing
        for existing in self._pending.values():
            if (
                existing.semantic_hash == semantic_hash
                and existing.skill_path == skill_path
                and existing.status == MutationStatus.PENDING
            ):
                logger.debug("Dedup: returning existing mutation %s", existing.id)
                return existing

        mutation = PendingMutation(
            id=str(uuid.uuid4()),
            skill_path=skill_path,
            change_type=change_type,
            diff_text=diff_text,
            semantic_hash=semantic_hash,
            proposed_by_agent=proposed_by_agent,
            created_at=now,
            valid_from=valid_from or now,
            valid_to=valid_to,
        )
        self._pending[mutation.id] = mutation

        if self._enable_persistence:
            await self._db_upsert("pending_mutations", mutation.id, mutation.to_dict())

        logger.info(
            "Mutation proposed: %s [%s] by %s (hash=%s…)",
            skill_path,
            change_type,
            proposed_by_agent,
            semantic_hash[:12],
        )
        return mutation

    async def get_pending_mutations(
        self,
        skill_path: str | None = None,
        change_type: ChangeType | None = None,
    ) -> list[PendingMutation]:
        """Return pending mutations, optionally filtered by skill_path or change_type."""
        results = [m for m in self._pending.values() if m.status == MutationStatus.PENDING]
        if skill_path:
            results = [m for m in results if m.skill_path == skill_path]
        if change_type:
            results = [m for m in results if m.change_type == change_type]
        return sorted(results, key=lambda m: m.created_at)

    async def update_mutation_status(self, mutation_id: str, status: MutationStatus) -> bool:
        """Update the status of a pending mutation. Returns True if found."""
        if mutation_id not in self._pending:
            return False
        mut = self._pending[mutation_id]
        # Dataclass is not frozen — rebuild with updated status
        updated = PendingMutation(
            id=mut.id,
            skill_path=mut.skill_path,
            change_type=mut.change_type,
            diff_text=mut.diff_text,
            semantic_hash=mut.semantic_hash,
            proposed_by_agent=mut.proposed_by_agent,
            created_at=mut.created_at,
            valid_from=mut.valid_from,
            valid_to=mut.valid_to,
            status=status,
            batch_id=mut.batch_id,
        )
        self._pending[mutation_id] = updated
        if self._enable_persistence:
            await self._db_patch("pending_mutations", mutation_id, {"status": str(status)})
        return True

    # ------------------------------------------------------------------
    # Approval cache (SemanticCache L3 integration point)
    # ------------------------------------------------------------------

    async def check_approval_cache(self, semantic_hash: str) -> ApprovalCacheEntry | None:
        """Check whether a prior human decision exists for this semantic_hash.

        Called by SemanticCache L3 before surfacing a mutation to the human.
        Returns None on cache miss or expired entry.
        """
        entry = self._approval_cache.get(semantic_hash)
        if entry is None:
            return None
        if entry.is_expired():
            logger.debug("Approval cache expired for hash %s…", semantic_hash[:12])
            return None

        # Bump hit counter (fire-and-forget)
        entry.hit_count += 1
        entry.last_hit_at = datetime.now(UTC)
        if self._enable_persistence:
            await self._db_patch(
                "human_approval_cache",
                semantic_hash,
                {"hit_count": entry.hit_count, "last_hit_at": entry.last_hit_at.isoformat()},
            )
        return entry

    async def cache_approval(
        self,
        semantic_hash: str,
        decision: ApprovalDecision,
        approved_by: str,
        applies_to_pattern: str = "*",
        ttl_seconds: int | None = None,
    ) -> ApprovalCacheEntry:
        """Record a human decision in the approval cache.

        applies_to_pattern is a glob that widens the decision to a family
        of skill_paths (e.g. "src/cohezion/skills/CODE_REVIEW*").
        """
        entry = ApprovalCacheEntry(
            semantic_hash=semantic_hash,
            decision=decision,
            approved_by=approved_by,
            cached_at=datetime.now(UTC),
            applies_to_pattern=applies_to_pattern,
            ttl_seconds=ttl_seconds,
        )
        self._approval_cache[semantic_hash] = entry

        if self._enable_persistence:
            await self._db_upsert("human_approval_cache", semantic_hash, entry.to_dict())

        logger.info(
            "Approval cached: %s → %s (pattern=%s)",
            semantic_hash[:12],
            decision,
            applies_to_pattern,
        )
        return entry

    # ------------------------------------------------------------------
    # Batch checkpoints (session-boundary flush)
    # ------------------------------------------------------------------

    async def create_batch(self, session_id: str, mutation_ids: list[str]) -> BatchCheckpoint:
        """Bundle mutations into a batch for a single human review session.

        Each mutation_id must exist in pending_mutations. Creates a
        BatchCheckpoint with status=PENDING.
        """
        # Validate all IDs exist
        unknown = [mid for mid in mutation_ids if mid not in self._pending]
        if unknown:
            raise ValueError(f"Unknown mutation IDs: {unknown}")

        batch_id = str(uuid.uuid4())
        batch = BatchCheckpoint(
            batch_id=batch_id,
            session_id=session_id,
            mutations=list(mutation_ids),
            status=BatchStatus.PENDING,
            mutation_count=len(mutation_ids),
        )
        self._batches[batch_id] = batch

        # Tag each mutation with this batch_id
        for mid in mutation_ids:
            await self._set_batch_id(mid, batch_id)

        if self._enable_persistence:
            await self._db_upsert("batch_checkpoint", batch_id, batch.to_dict())

        logger.info(
            "Batch %s created: %d mutations for session %s",
            batch_id[:8],
            len(mutation_ids),
            session_id,
        )
        return batch

    async def mark_reviewed(self, batch_id: str) -> BatchCheckpoint:
        """Mark batch as reviewed (human has seen it). Status: pending → reviewed."""
        batch = self._batches.get(batch_id)
        if batch is None:
            raise KeyError(f"Batch not found: {batch_id}")
        batch.status = BatchStatus.REVIEWED
        batch.presented_at = datetime.now(UTC)
        if self._enable_persistence:
            await self._db_patch(
                "batch_checkpoint",
                batch_id,
                {"status": "reviewed", "presented_at": batch.presented_at.isoformat()},
            )
        return batch

    async def flush_batch(self, batch_id: str) -> int:
        """Flush a reviewed batch — apply approved mutations to disk.

        Status transitions: reviewed → flushed.
        Approved mutations: status → approved (caller applies to skill files).
        Rejected mutations: status → rejected.

        Returns count of approved mutations in the batch.
        """
        batch = self._batches.get(batch_id)
        if batch is None:
            raise KeyError(f"Batch not found: {batch_id}")
        if batch.status != BatchStatus.REVIEWED:
            raise ValueError(f"Batch {batch_id} must be in REVIEWED state to flush, current state: {batch.status}")

        approved_count = 0
        for mid in batch.mutations:
            mut = self._pending.get(mid)
            if mut is None:
                continue
            cache_entry = await self.check_approval_cache(mut.semantic_hash)
            if cache_entry and cache_entry.decision == ApprovalDecision.APPROVED:
                await self.update_mutation_status(mid, MutationStatus.APPROVED)
                approved_count += 1
            elif cache_entry and cache_entry.decision == ApprovalDecision.REJECTED:
                await self.update_mutation_status(mid, MutationStatus.REJECTED)

        batch.status = BatchStatus.FLUSHED
        batch.flushed_at = datetime.now(UTC)
        if self._enable_persistence:
            await self._db_patch(
                "batch_checkpoint",
                batch_id,
                {"status": "flushed", "flushed_at": batch.flushed_at.isoformat()},
            )

        logger.info(
            "Batch %s flushed: %d/%d mutations approved",
            batch_id[:8],
            approved_count,
            batch.mutation_count,
        )
        return approved_count

    def get_batch(self, batch_id: str) -> BatchCheckpoint | None:
        return self._batches.get(batch_id)

    def get_metrics(self) -> dict[str, Any]:
        """In-process queue metrics snapshot."""
        pending = sum(1 for m in self._pending.values() if m.status == MutationStatus.PENDING)
        approved = sum(1 for m in self._pending.values() if m.status == MutationStatus.APPROVED)
        rejected = sum(1 for m in self._pending.values() if m.status == MutationStatus.REJECTED)
        return {
            "total_mutations": len(self._pending),
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "approval_cache_size": len(self._approval_cache),
            "total_batches": len(self._batches),
            "flushed_batches": sum(1 for b in self._batches.values() if b.status == BatchStatus.FLUSHED),
        }

    # ------------------------------------------------------------------
    # Private DB helpers (no-ops when persistence disabled)
    # ------------------------------------------------------------------

    async def _db_upsert(self, table: str, record_id: str, data: dict) -> None:
        if not self._enable_persistence:
            return
        try:
            from surrealdb import AsyncSurreal  # lazy import — not required for tests

            async with AsyncSurreal(self._url) as db:
                await db.use(self._namespace, self._database)
                await db.upsert(f"{table}:{record_id}", data)
        except Exception as e:
            logger.warning("DB upsert failed (%s:%s): %s", table, record_id, e)

    async def _db_patch(self, table: str, record_id: str, patch: dict) -> None:
        if not self._enable_persistence:
            return
        try:
            from surrealdb import AsyncSurreal

            async with AsyncSurreal(self._url) as db:
                await db.use(self._namespace, self._database)
                await db.patch(f"{table}:{record_id}", patch)
        except Exception as e:
            logger.warning("DB patch failed (%s:%s): %s", table, record_id, e)

    async def _set_batch_id(self, mutation_id: str, batch_id: str) -> None:
        if mutation_id in self._pending:
            mut = self._pending[mutation_id]
            self._pending[mutation_id] = PendingMutation(
                id=mut.id,
                skill_path=mut.skill_path,
                change_type=mut.change_type,
                diff_text=mut.diff_text,
                semantic_hash=mut.semantic_hash,
                proposed_by_agent=mut.proposed_by_agent,
                created_at=mut.created_at,
                valid_from=mut.valid_from,
                valid_to=mut.valid_to,
                status=mut.status,
                batch_id=batch_id,
            )
