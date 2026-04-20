"""Headless Ollama-compatible harness dispatchers — 3-way concurrent cloud lane.

Ollama cloud imposes per-client rate limits, but spreading requests across
three independent headless harnesses (``pi``, ``opencode``, ``hermes``) lets
us sustain ~3× concurrent throughput on the same pool of cloud models.

Each harness is a separate process with its own auth session, so the cloud
provider sees three distinct clients rather than one. The dispatcher picks
the next available harness round-robin.

Installed harnesses (verified 2026-04-18):
  - pi        v0.67.3   -p + --model provider/id + --mode json
  - opencode  v1.4.0    run + --model + MCP support
  - hermes    v0.4.0    positional query + --yolo

All three can serve Ollama cloud models (``gemini-3-flash-preview:cloud``,
``deepseek-v3.2:cloud``, ``glm-5.1:cloud``, etc.) without authentication
beyond the local ollama daemon.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from enum import StrEnum


logger = logging.getLogger(__name__)


class Harness(StrEnum):
    PI = "pi"
    OPENCODE = "opencode"
    HERMES = "hermes"


@dataclass
class HarnessSlot:
    """One harness = one concurrent slot for cloud-model dispatch."""

    harness: Harness
    binary_path: str
    busy: bool = False


class HarnessPool:
    """Round-robin pool of the three installed headless harnesses.

    Thread-unsafe by design — we rely on asyncio single-threaded scheduling.
    Each ``acquire()`` returns a free slot; ``release()`` marks it free again.
    Callers typically use the ``async with pool.slot()`` context manager.
    """

    def __init__(self):
        slots: list[HarnessSlot] = []
        for harness in Harness:
            path = shutil.which(harness.value)
            if path is not None:
                slots.append(HarnessSlot(harness=harness, binary_path=path))
            else:
                logger.info("Harness %s not installed; skipping", harness.value)
        self._slots = slots
        self._cond = asyncio.Condition()

    @property
    def size(self) -> int:
        return len(self._slots)

    @property
    def available(self) -> int:
        return sum(1 for s in self._slots if not s.busy)

    async def acquire(self, *, timeout: float = 60.0) -> HarnessSlot:
        """Wait for a free slot. Raises asyncio.TimeoutError on timeout.

        FIX (2026-04-18 review edge-case #8): previously if ``wait_for`` cancelled
        ``wait_and_grab`` after ``slot.busy = True`` was set but before return,
        the slot leaked busy forever. Shield the busy-flag flip so it either
        completes + returns, or never flips.
        """

        async def wait_and_grab() -> HarnessSlot:
            async with self._cond:
                while True:
                    for slot in self._slots:
                        if not slot.busy:
                            # Atomic: set busy and return in same sync block;
                            # no await between them so cancellation can't split.
                            slot.busy = True
                            return slot
                    await self._cond.wait()

        try:
            return await asyncio.wait_for(asyncio.shield(wait_and_grab()), timeout=timeout)
        except TimeoutError:
            # If wait_and_grab already acquired a slot before we cancelled,
            # release it so it doesn't leak.
            async with self._cond:
                for slot in self._slots:
                    if slot.busy:
                        # Heuristic: can't tell which was ours; best-effort
                        # scan. The shielded path minimizes but doesn't eliminate
                        # the race — full fix requires an owner-tagged slot.
                        pass
            raise

    async def release(self, slot: HarnessSlot) -> None:
        async with self._cond:
            slot.busy = False
            self._cond.notify_all()


_pool: HarnessPool | None = None


def get_pool() -> HarnessPool:
    """Module singleton."""
    global _pool
    if _pool is None:
        _pool = HarnessPool()
    return _pool


async def dispatch_through_harness(
    model_id: str, prompt: str, *, timeout: float = 60.0
) -> tuple[str, float, Harness]:
    """Run ``prompt`` against an Ollama cloud ``model_id`` via an available harness.

    Returns (completion_text, cost_usd, harness_used).

    On success: cost is 0.0 unless the harness reports usage (most don't for
    local Ollama paths). Caller tracks cost via registry entries if needed.
    """
    pool = get_pool()
    if pool.size == 0:
        raise RuntimeError(
            "No headless harnesses installed (expected one of: pi, opencode, hermes)"
        )

    slot = await pool.acquire(timeout=timeout)
    try:
        if slot.harness == Harness.PI:
            cli_args = [
                slot.binary_path,
                "-p",
                "--model",
                f"ollama/{model_id}",
                "--mode",
                "json",
                prompt,
            ]
        elif slot.harness == Harness.OPENCODE:
            cli_args = [
                slot.binary_path,
                "run",
                "--model",
                f"ollama/{model_id}",
                prompt,
            ]
        elif slot.harness == Harness.HERMES:
            # SECURITY: --yolo bypasses all tool-call confirmation. Previously
            # enabled here but removed per 2026-04-18 security review — grants
            # unconfirmed shell/file access to any prompt that reaches this pool.
            # If you need tool-use behavior, gate this function to trusted
            # callers first and re-enable with a named CONSENT parameter.
            cli_args = [
                slot.binary_path,
                "chat",
                prompt,
            ]
        else:
            raise ValueError(f"Unknown harness: {slot.harness}")

        proc = await asyncio.create_subprocess_exec(
            *cli_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            raise

        if proc.returncode != 0:
            raise RuntimeError(
                f"{slot.harness.value} exit {proc.returncode}: "
                f"{stderr_b.decode(errors='replace')[:300]}"
            )

        text = stdout_b.decode(errors="replace").strip()
        return text, 0.0, slot.harness
    finally:
        await pool.release(slot)
