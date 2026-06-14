"""Item 121: Batch fairness-cap planner — report-only (2026-06-08).

``batch_fairness_plan(batch_size, *, interactive_busy, npu_concurrency=3)``
returns the ``max_concurrent`` cap to pass to ``run_batch_local`` (item 119).

Closes the loop between:
  - Item 113 ``should_yield_to_interactive`` — the yield SIGNAL (is the bot hurting?)
  - Item 119 ``run_batch_local`` — the concurrency KNOB (how many parallel tasks?)

Without this planner, ``run_batch_local``'s ``max_concurrent`` is always ``None``
(unlimited), ignoring fleet fairness entirely.  With it, the driver calls
``batch_fairness_plan`` at task-submission time and passes the result as
``max_concurrent``.

Routing logic:
  interactive bot BUSY → cap 1   (sequential fallback — yields the fleet to the bot)
  bot IDLE, batch > npu_concurrency → cap npu_concurrency (optimal NPU throughput)
  bot IDLE, batch ≤ npu_concurrency → cap batch_size     (no wasted idle NPU slots)
  batch_size == 0 → cap 0        (nothing to schedule)

Report-only — proposes a concurrency cap; the driver decides whether to act.
Pure (injected flags; no live :13305 probe, no asyncio).
"""

from __future__ import annotations


# Default NPU concurrency: 3 concurrent tasks = best measured throughput per
# TieredOrchestrator.run_batch docs (3.44× vs sequential on XDNA2 NPU).
_DEFAULT_NPU_CONCURRENCY: int = 3


def batch_fairness_plan(
    batch_size: int,
    *,
    interactive_busy: bool,
    npu_concurrency: int = _DEFAULT_NPU_CONCURRENCY,
) -> int:
    """Return the max_concurrent cap for run_batch_local (item 121). Pure.

    Encodes the fleet-fairness concurrency policy:
    1. Nothing to batch → cap 0.
    2. Interactive bot BUSY → cap 1 (sequential, yield the fleet).
    3. Bot IDLE → cap = min(batch_size, npu_concurrency) (no overshooting, no waste).

    Args:
        batch_size:
            Total number of items in the batch.  0 → cap 0 (no work).
        interactive_busy:
            ``True`` when the interactive bot is experiencing elevated latency or
            active load (as reported by item-113 ``should_yield_to_interactive``).
            When ``True``, the batch must run sequentially (cap=1) to protect the bot.
        npu_concurrency:
            Maximum simultaneous tasks when the bot is idle.  Defaults to 3 — the
            empirically best NPU throughput knob from ``run_batch``'s docstring
            (``orchestrator.py:587``).

    Returns:
        An integer ≥ 0 representing the max_concurrent argument for
        ``run_batch_local``.  0 when batch_size == 0; 1 when interactive_busy.

    Pure — no live fleet probe, no asyncio, no writes.
    Report-only — proposes the cap; the batch driver decides whether to act.
    """
    if batch_size <= 0:
        return 0

    if interactive_busy:
        return 1

    # Bot idle: use the NPU throughput optimum, but never overshooting the batch.
    return min(batch_size, npu_concurrency)
