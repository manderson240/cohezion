"""Async semaphore gate enforcing global Ollama concurrency limit of 4."""

from __future__ import annotations

import asyncio
import logging
import threading


logger = logging.getLogger(__name__)


class OllamaGate:
    """Async context manager wrapping asyncio.Semaphore(4).

    Parameters
    ----------
    max_concurrent : int
        Maximum number of concurrent Ollama calls allowed.
    """

    def __init__(self, max_concurrent: int = 4) -> None:
        self._max = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._lock = threading.Lock()

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore (one per event loop)."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max)
        return self._semaphore

    async def __aenter__(self) -> OllamaGate:
        sem = self._get_semaphore()
        logger.debug(
            "OllamaGate: acquiring (available: %s/%s)",
            sem._value,
            self._max,
        )
        await sem.acquire()
        logger.debug(
            "OllamaGate: acquired (available: %s/%s)",
            sem._value,
            self._max,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        sem = self._get_semaphore()
        sem.release()
        logger.debug(
            "OllamaGate: released (available: %s/%s)",
            sem._value,
            self._max,
        )

    @property
    def available(self) -> int:
        """Number of available slots."""
        sem = self._get_semaphore()
        return sem._value


_gate: OllamaGate | None = None
_gate_lock = threading.Lock()


def get_gate(max_concurrent: int = 4) -> OllamaGate:
    """Return the singleton OllamaGate."""
    global _gate
    if _gate is None:
        with _gate_lock:
            if _gate is None:
                _gate = OllamaGate(max_concurrent)
    return _gate


def reset_gate() -> None:
    """Reset the singleton (for testing)."""
    global _gate
    _gate = None
