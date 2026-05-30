"""Tests for CohezionMemory wired into CompoundExecutor.

The executor remembers each successful turn (best-effort) so executions compound
into the project's memory. Memory is opt-in (``enable_memory=True``); recall is
intentionally not wired yet (no execute_fn consumes it). These tests use a fake
memory (no mem0/SurrealDB) and live in tests/memory/ (clean conftest) rather than
the syntax-broken tests/compound/.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.executor_factory import ExecutorFactory


class _FakeMemory:
    """Records recall/remember calls; returns canned data."""

    def __init__(self, *, broken: bool = False):
        self.recall_calls: list[tuple] = []
        self.remember_calls: list[tuple] = []
        self._broken = broken

    def recall(self, query, agent_id, limit=5):
        if self._broken:
            raise RuntimeError("nodes offline")
        self.recall_calls.append((query, agent_id))
        return ["prior: user prefers worktree commits"]

    def remember(self, messages, agent_id):
        if self._broken:
            raise RuntimeError("nodes offline")
        self.remember_calls.append((messages, agent_id))
        return [{"id": "1", "memory": "x", "event": "ADD"}]


def _executor(memory=None, enable_memory=True):
    return CompoundExecutor(
        MagicMock(),  # mcp_client
        enable_guardrails=False,
        enable_skill_refinement=False,
        memory_service=memory,
        enable_memory=enable_memory,
    )


def _isolate(monkeypatch, ex):
    """Stub the vault/external seams so execute_task runs offline."""
    monkeypatch.setattr(ex, "get_experience_guidance", lambda *a, **k: {})
    monkeypatch.setattr(ex, "_try_template_match", lambda *a, **k: None)
    monkeypatch.setattr(ex.logger, "log_execution_start", lambda ctx: "exp_path")
    monkeypatch.setattr(ex.logger, "log_execution_result", lambda **k: None)
    monkeypatch.setattr(ex.logger, "log_execution_trace", lambda **k: None)


# ── structural (mirrors the harness CB-pattern guard) ──────────────────────────
def test_init_accepts_memory_params():
    import inspect

    params = inspect.signature(CompoundExecutor.__init__).parameters
    assert "memory_service" in params
    assert "enable_memory" in params


def test_factory_accepts_and_passes_memory():
    import inspect

    assert "memory_service" in inspect.signature(ExecutorFactory.create).parameters
    fake = _FakeMemory()
    ex = ExecutorFactory.create(
        MagicMock(),
        enable_guardrails=False,
        enable_skill_refinement=False,
        memory_service=fake,
        enable_memory=True,
    )
    assert ex.memory_service is fake


# ── property behavior ──────────────────────────────────────────────────────────
def test_memory_service_returns_injected():
    fake = _FakeMemory()
    assert _executor(memory=fake).memory_service is fake


def test_memory_service_none_when_disabled():
    assert _executor(memory=_FakeMemory(), enable_memory=False).memory_service is None


# ── integration: remember fires after success; recall stays unwired ─────────────
def test_execute_task_remembers_after_success(monkeypatch):
    fake = _FakeMemory()
    ex = _executor(memory=fake)
    _isolate(monkeypatch, ex)

    captured: dict = {}

    def execute_fn(guidance):
        captured["guidance"] = guidance
        return ("the output", {})

    result = ex.execute_task("write the tests", "myskill", "generate", execute_fn, project="proj")

    assert result.success
    # recall is intentionally NOT wired — no search() latency, no guidance injection
    assert fake.recall_calls == []
    assert "recalled_memories" not in captured["guidance"]
    # remember ran after success, scoped to the project, with the task+output turn
    assert fake.remember_calls and fake.remember_calls[0][1] == "proj"
    msgs = fake.remember_calls[0][0]
    assert msgs[0]["content"] == "write the tests" and msgs[1]["content"] == "the output"


def test_execute_task_unaffected_when_memory_broken(monkeypatch):
    """recall/remember failures must never break execution."""
    ex = _executor(memory=_FakeMemory(broken=True))
    _isolate(monkeypatch, ex)
    result = ex.execute_task("x", "s", "generate", lambda g: ("ok", {}), project="proj")
    assert result.success and result.output == "ok"


def test_execute_task_no_memory_when_disabled(monkeypatch):
    fake = _FakeMemory()
    ex = _executor(memory=fake, enable_memory=False)
    _isolate(monkeypatch, ex)
    ex.execute_task("x", "s", "generate", lambda g: ("ok", {}), project="proj")
    assert fake.recall_calls == [] and fake.remember_calls == []
