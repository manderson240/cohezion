"""HarnessPool 3-concurrent slot tests — subprocess invocations mocked."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from cohezion.inference.harnesses import Harness, HarnessPool


@pytest.mark.asyncio
async def test_pool_detects_installed_harnesses():
    """When all three binaries exist, pool has three slots."""

    def fake_which(name):
        return f"/fake/bin/{name}" if name in {"pi", "opencode", "hermes"} else None

    with patch("cohezion.inference.harnesses.shutil.which", side_effect=fake_which):
        pool = HarnessPool()

    assert pool.size == 3
    assert pool.available == 3
    assert {s.harness for s in pool._slots} == {
        Harness.PI,
        Harness.OPENCODE,
        Harness.HERMES,
    }


@pytest.mark.asyncio
async def test_pool_skips_missing_harnesses():
    with patch(
        "cohezion.inference.harnesses.shutil.which",
        side_effect=lambda name: "/bin/pi" if name == "pi" else None,
    ):
        pool = HarnessPool()
    assert pool.size == 1
    assert pool._slots[0].harness == Harness.PI


@pytest.mark.asyncio
async def test_acquire_marks_slot_busy_and_release_frees_it():
    with patch(
        "cohezion.inference.harnesses.shutil.which",
        side_effect=lambda n: "/bin/pi" if n == "pi" else None,
    ):
        pool = HarnessPool()

    slot = await pool.acquire(timeout=1.0)
    assert slot.busy is True
    assert pool.available == 0

    await pool.release(slot)
    assert pool.available == 1


@pytest.mark.asyncio
async def test_acquire_blocks_until_release():
    """Second acquire waits for first to release (confirms single-slot concurrency)."""

    with patch(
        "cohezion.inference.harnesses.shutil.which",
        side_effect=lambda n: "/bin/pi" if n == "pi" else None,
    ):
        pool = HarnessPool()

    slot1 = await pool.acquire(timeout=1.0)

    async def grab_second():
        return await pool.acquire(timeout=2.0)

    task = asyncio.create_task(grab_second())
    await asyncio.sleep(0.05)  # Confirm task is waiting
    assert not task.done()

    await pool.release(slot1)
    slot2 = await task
    assert slot2 is slot1  # only one slot in pool — same object
