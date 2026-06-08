"""Item 121: batch_fairness_plan — TDD red→green (2026-06-08).

``batch_fairness_plan(batch_size, *, interactive_busy, npu_concurrency=3)`` returns
the ``max_concurrent`` cap for ``run_batch_local``:

- interactive bot BUSY  → cap == 1  (sequential fallback; yields fleet to bot)
- bot IDLE, large batch → cap == npu_concurrency (optimal NPU throughput)
- bot IDLE, small batch → cap == batch_size (no idle slots, cap at batch)
- batch_size == 0       → cap == 0  (nothing to schedule)

Composes item-113 ``should_yield_to_interactive`` (yield signal) + item-119
``run_batch_local`` (the concurrency knob).  Pure — no live fleet probe.

Discriminating tests — each kills a plausible wrong implementation:

  1. Busy bot → cap == 1                     (MAIN DISC.: kills "always use npu_concurrency")
  2. Idle + large batch → cap == npu_concurrency (kills "always cap at 1")
  3. Idle + small batch → cap == batch_size  (kills "ignore batch_size, always npu_concurrency")
  4. batch_size == 0 → cap == 0             (kills an impl that returns min(0, npu) = error)
  5. Busy + large batch still cap == 1       (kills "only apply if batch < concurrency")
  6. npu_concurrency is respected            (kills "hardcode npu_concurrency=3")
"""

from __future__ import annotations

from cohezion.compound.batch_fairness import batch_fairness_plan


def test_busy_bot_cap_is_one() -> None:
    """Interactive bot BUSY → max_concurrent == 1 (sequential fallback).

    PRIMARY DISCRIMINATOR: kills an impl that always returns npu_concurrency.
    """
    cap = batch_fairness_plan(10, interactive_busy=True)
    assert cap == 1, f"busy bot must → cap 1 (yield); got {cap}"


def test_idle_large_batch_cap_is_npu_concurrency() -> None:
    """Bot IDLE, batch_size > npu_concurrency → cap == npu_concurrency.

    Kills an impl that always returns 1 (never uses full concurrency).
    """
    cap = batch_fairness_plan(10, interactive_busy=False)
    assert cap == 3, f"idle + large batch must → cap 3 (npu_concurrency); got {cap}"


def test_idle_small_batch_cap_at_batch_size() -> None:
    """Bot IDLE, batch_size < npu_concurrency → cap == batch_size (no idle slots).

    Kills an impl that always returns npu_concurrency regardless of batch_size.
    """
    cap = batch_fairness_plan(2, interactive_busy=False, npu_concurrency=3)
    assert cap == 2, f"idle + small batch (2 < 3) must → cap 2; got {cap}"


def test_empty_batch_cap_zero() -> None:
    """batch_size == 0 → cap == 0 (no work to schedule).

    Kills an impl that returns min(0, npu_concurrency) with a DivisionError,
    or one that returns 1.
    """
    cap = batch_fairness_plan(0, interactive_busy=False)
    assert cap == 0, f"empty batch must → cap 0; got {cap}"


def test_busy_large_batch_still_cap_one() -> None:
    """Even a very large batch → cap == 1 when bot is busy.

    Kills an impl that only yields when batch is larger than concurrency.
    """
    cap = batch_fairness_plan(100, interactive_busy=True)
    assert cap == 1, f"busy bot + 100 items must still → cap 1; got {cap}"


def test_npu_concurrency_param_respected() -> None:
    """npu_concurrency=5 → cap == 5 for a large idle batch.

    Kills an impl that hardcodes npu_concurrency=3 and ignores the parameter.
    """
    cap = batch_fairness_plan(20, interactive_busy=False, npu_concurrency=5)
    assert cap == 5, f"npu_concurrency=5 + idle + batch=20 must → cap 5; got {cap}"
