"""Tests for CohezionMemory — the workflow-facing memory service.

These run ALWAYS (no mem0 dependency): a fake Memory is injected so the API
normalization and graceful-degradation contracts are tested without the extra or
any live node. The two key assertions encode bugs found by dogfooding:
  - recall() must pass user_id via filters= (mem0 2.0.4 rejects top-level user_id)
  - any mem0 failure (offline node, missing extra) must degrade to [], never raise.
"""

from __future__ import annotations

from cohezion.memory.service import CohezionMemory


class _FakeMemory:
    """Records add/search calls and returns canned mem0-shaped responses."""

    def __init__(self):
        self.add_calls: list[dict] = []
        self.search_calls: list[dict] = []

    def add(self, messages, **kwargs):
        self.add_calls.append({"messages": messages, "kwargs": kwargs})
        return {"results": [{"id": "1", "memory": "user prefers worktree commits", "event": "ADD"}]}

    def search(self, query, **kwargs):
        self.search_calls.append({"query": query, "kwargs": kwargs})
        return {"results": [{"memory": "user prefers worktree commits", "score": 0.42}]}


class _BrokenMemory:
    def add(self, *a, **k):
        raise RuntimeError("lemonade node offline")

    def search(self, *a, **k):
        raise RuntimeError("lemonade node offline")


def test_remember_passes_user_id_top_level():
    """add() takes user_id as a top-level kwarg (mem0 2.0.4)."""
    fake = _FakeMemory()
    mem = CohezionMemory(memory=fake)
    facts = mem.remember([{"role": "user", "content": "I commit in worktrees"}], agent_id="dev")
    assert fake.add_calls[0]["kwargs"] == {"user_id": "dev"}
    assert facts and facts[0]["event"] == "ADD"


def test_recall_passes_user_id_via_filters():
    """recall() MUST route user_id through filters= — top-level raises in mem0 2.0.4."""
    fake = _FakeMemory()
    mem = CohezionMemory(memory=fake)
    out = mem.recall("how do commits work?", agent_id="dev", limit=3)
    call = fake.search_calls[0]
    assert call["kwargs"]["filters"] == {"user_id": "dev"}, "user_id must be in filters="
    assert "user_id" not in call["kwargs"], "user_id must NOT be a top-level search kwarg"
    assert call["kwargs"]["limit"] == 3
    assert out == ["user prefers worktree commits"]


def test_degrades_to_empty_when_disabled():
    """A disabled service no-ops without touching any backend."""
    mem = CohezionMemory(enabled=False)
    assert mem.available is False
    assert mem.remember("anything", agent_id="dev") == []
    assert mem.recall("anything", agent_id="dev") == []


def test_remember_degrades_on_backend_error():
    """An offline-node failure during add must return [] and never raise."""
    mem = CohezionMemory(memory=_BrokenMemory())
    assert mem.remember("x", agent_id="dev") == []


def test_recall_degrades_on_backend_error():
    """An offline-node failure during search must return [] and never raise."""
    mem = CohezionMemory(memory=_BrokenMemory())
    assert mem.recall("x", agent_id="dev") == []


def test_disabled_when_extra_missing(monkeypatch):
    """If mem0 is not importable, the service disables itself at construction."""
    monkeypatch.setattr("cohezion.memory.service.mem0_available", lambda: False)
    mem = CohezionMemory()  # no injected memory
    assert mem.available is False
    assert mem.remember("x", agent_id="dev") == []


def test_lazy_build_failure_disables(monkeypatch):
    """If build_local_mem0 raises, the service disables itself gracefully."""
    monkeypatch.setattr("cohezion.memory.service.mem0_available", lambda: True)

    def _boom(_cfg):
        raise RuntimeError("qdrant path unwritable")

    monkeypatch.setattr("cohezion.memory.service.build_local_mem0", _boom)
    mem = CohezionMemory()
    assert mem.recall("x", agent_id="dev") == []
    assert mem.available is False


def test_get_instance_is_singleton():
    a = CohezionMemory.get_instance()
    b = CohezionMemory.get_instance()
    assert a is b
