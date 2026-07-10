"""Discriminating tests for the AOEP-v0 P1 gap fills (2026-07-09).

Each test exercises the BEHAVIOR the axis contract requires — not just the
structural probe the scorecard uses.
"""

from datetime import timedelta

import numpy as np
import pytest

from cohezion.cache.semantic_cache import CacheEntry, SemanticCache
from cohezion.compound.journey_tracker import classify_state_category
from cohezion.compound.skill_mutation_queue import SkillMutationQueue, _now


# ── Scope axis ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scoped_entry_hidden_from_other_scopes():
    cache = SemanticCache(similarity_threshold=0.99)
    await cache.put("agent-a private fact", "secret", scope="agent-a")
    hit = await cache.get("agent-a private fact", scope_filter=["agent-b"])
    assert hit is None


@pytest.mark.asyncio
async def test_scoped_entry_visible_in_own_scope():
    cache = SemanticCache(similarity_threshold=0.99)
    await cache.put("agent-a private fact", "secret", scope="agent-a")
    assert await cache.get("agent-a private fact", scope_filter=["agent-a"]) == "secret"


@pytest.mark.asyncio
async def test_unscoped_entry_is_global():
    cache = SemanticCache(similarity_threshold=0.99)
    await cache.put("public fact", "answer")
    assert await cache.get("public fact", scope_filter=["agent-b"]) == "answer"


@pytest.mark.asyncio
async def test_no_filter_preserves_old_behavior():
    cache = SemanticCache(similarity_threshold=0.99)
    await cache.put("anything", "resp", scope="agent-a")
    assert await cache.get("anything") == "resp"


def test_cache_entry_scope_default_backcompat():
    e = CacheEntry(key="k", prompt="p", response="r", embedding=np.zeros(4))
    assert e.scope == ""


# ── Mutability axis (TTL/decay) ──────────────────────────────────────────────


def test_expire_stale_retires_old_pending():
    q = SkillMutationQueue()
    mid = q.enqueue(skill_name="s", patch="p", reason="r")
    # age the mutation past the TTL
    q._mutations[mid].valid_from = _now() - timedelta(hours=200)
    expired = q.expire_stale(ttl_hours=168.0)
    assert expired == 1
    m = q._mutations[mid]
    assert m.status == "expired"
    assert m.valid_to is not None
    assert not m.is_valid_at()


def test_expire_stale_spares_fresh_and_nonpending():
    q = SkillMutationQueue()
    fresh = q.enqueue(skill_name="s", patch="p", reason="r")
    approved = q.enqueue(skill_name="s2", patch="p2", reason="r2")
    q.approve(approved)
    q._mutations[approved].valid_from = _now() - timedelta(hours=200)
    assert q.expire_stale(ttl_hours=168.0) == 0
    assert q._mutations[fresh].status == "pending"
    assert q._mutations[approved].status == "approved"


def test_expiry_preserves_bitemporal_history():
    q = SkillMutationQueue()
    mid = q.enqueue(skill_name="s", patch="p", reason="r")
    q._mutations[mid].valid_from = _now() - timedelta(hours=200)
    before_expiry = _now() - timedelta(hours=100)
    q.expire_stale(ttl_hours=168.0)
    # Time-travel: the mutation WAS valid before it expired
    assert q._mutations[mid].is_valid_at(before_expiry)


# ── Actionability axis (semantic state categories) ───────────────────────────


def test_classify_skill_operations():
    assert classify_state_category("skill_refinement") == "skill"
    assert classify_state_category("SKILL_UPDATE") == "skill"


def test_classify_commitment_operations():
    assert classify_state_category("checkpoint") == "commitment"
    assert classify_state_category("rollback") == "commitment"


def test_classify_defaults_to_evidence():
    assert classify_state_category("generate") == "evidence"
    assert classify_state_category("") == "evidence"
    assert classify_state_category(None) == "evidence"
