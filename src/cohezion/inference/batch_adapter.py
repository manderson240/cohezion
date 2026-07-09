"""Competent batch inference adapter (backlog item 119, 2026-06-06).

User lesson: "you need more competent local inference approaches." A naive SEQUENTIAL loop
(``scripts/research/distill_tutorials.py`` ran one model call per item in a for-loop)
bypassed the existing CONCURRENT multi-tier batcher ``TieredOrchestrator.run_batch``
(``orchestrator.py:547``, ``asyncio.gather``, measured 3.44x on XDNA2 NPU [exp_OOOO,
2026-05-20]). This thin adapter routes a WHOLE batch through ``run_batch`` in ONE
concurrent call so batch drivers stop reinventing the sequential anti-pattern.

The orchestrator is INJECTABLE (no live fleet under pytest). ``max_concurrent`` honors the
fleet-fairness cap (item 113): ``run_batch`` reads ``self._max_concurrent``
(``orchestrator.py:585``, defensive ``getattr`` with ``None`` default), so the adapter
SETS that attribute — the real, documented interface (``run_batch`` exposes no
``max_concurrent`` parameter; mirroring the production interface keeps the adapter faithful
rather than a parallel fiction). Pure given the injected orchestrator — no writes, no
network; ``asyncio.gather`` over live ports happens only inside the real orchestrator.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol


class BatchOrchestrator(Protocol):
    """The minimal surface the adapter needs — ``TieredOrchestrator`` satisfies it."""

    async def run_batch(
        self, prompts: list[str], *, budget_usd: float | None = ...
    ) -> list[Any]: ...


async def run_batch_local(
    prompts: Iterable[str],
    *,
    orchestrator: BatchOrchestrator,
    budget_usd: float | None = None,
    max_concurrent: int | None = None,
) -> list[Any]:
    """Delegate a batch to ``orchestrator.run_batch`` in ONE concurrent call.

    The competent path: a single ``run_batch`` (``asyncio.gather``, 3.44x XDNA2) instead of
    N sequential ``run()`` calls. ``max_concurrent`` caps parallelism (fleet-fairness, item
    113) by setting ``orchestrator._max_concurrent`` — the attribute ``run_batch`` reads (it
    exposes no such parameter). An empty input returns ``[]`` with NO orchestrator call.
    Results are returned in prompt order. Pure given the injected orchestrator.
    """
    items: list[str] = list(prompts)
    if not items:
        return []
    if max_concurrent is not None:
        # The interface run_batch actually reads (orchestrator.py:585) — not a param.
        setattr(orchestrator, "_max_concurrent", max_concurrent)  # noqa: B010
    return await orchestrator.run_batch(items, budget_usd=budget_usd)
