"""Discriminating tests for run_batch_local (backlog item 119, 2026-06-06).

The lesson under test (user: "you need more competent local inference approaches"): the
adapter must route a whole batch through the CONCURRENT batcher
``TieredOrchestrator.run_batch`` in ONE call with all prompts — NOT a sequential loop
calling ``run()`` once per prompt (the anti-pattern the bespoke distill_tutorials.py used).

Each test fails a plausible wrong impl:
  - a sequential ``run()``-per-prompt impl → test_delegates_once_not_sequential,
  - an impl that ignores the fleet-fairness cap → test_max_concurrent_forwarded,
  - an impl that calls the orchestrator on an empty batch → test_empty_returns_empty_no_call,
  - an impl that sorts/reorders → test_order_preserved.
"""

from __future__ import annotations

import asyncio

from cohezion.inference.batch_adapter import run_batch_local


class _FakeOrchestrator:
    """Records run_batch vs run calls — no live fleet (pure)."""

    def __init__(self) -> None:
        self.run_batch_calls: list[list[str]] = []
        self.run_calls: list[str] = []

    async def run_batch(self, prompts: list[str], *, budget_usd: float | None = None) -> list[str]:
        self.run_batch_calls.append(list(prompts))
        return [f"result:{p}" for p in prompts]

    async def run(self, prompt: str, *, budget_usd: float | None = None) -> str:
        self.run_calls.append(prompt)
        return f"result:{prompt}"


def test_delegates_once_not_sequential() -> None:
    orch = _FakeOrchestrator()
    out = asyncio.run(run_batch_local(["a", "b", "c"], orchestrator=orch))
    # ONE concurrent run_batch with ALL prompts — a sequential impl (run() x3) FAILS this.
    assert orch.run_batch_calls == [["a", "b", "c"]]
    assert orch.run_calls == []
    assert out == ["result:a", "result:b", "result:c"]


def test_max_concurrent_forwarded() -> None:
    orch = _FakeOrchestrator()
    asyncio.run(run_batch_local(["a", "b"], orchestrator=orch, max_concurrent=3))
    # run_batch reads self._max_concurrent (orchestrator.py:585) — the adapter must set it.
    assert getattr(orch, "_max_concurrent", None) == 3


def test_empty_returns_empty_no_call() -> None:
    orch = _FakeOrchestrator()
    out = asyncio.run(run_batch_local([], orchestrator=orch))
    assert out == []
    assert orch.run_batch_calls == []  # NO orchestrator call on an empty batch


def test_order_preserved() -> None:
    orch = _FakeOrchestrator()
    out = asyncio.run(run_batch_local(["z", "y", "x"], orchestrator=orch))
    assert out == ["result:z", "result:y", "result:x"]  # prompt order, not sorted
