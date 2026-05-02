import asyncio
import contextlib
import logging
from typing import Any

from cohezion.compound.exp_persistence.journey import get_journey_persistence
from cohezion.compound.exp_persistence.vault import get_vault_logger
from cohezion.reliability.monitor import get_resource_monitor


logger = logging.getLogger(__name__)


class PersistenceAccumulator:
    """
    Non-blocking buffer for swarm experience persistence.

    Implements the 'Accumulator' pattern:
    - Buffers mission data in an asyncio.Queue.
    - Flushes to SurrealDB and Vault based on system dilation.
    - Discards low-value logs during high-pressure scenarios.
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, flush_interval: float = 5.0, batch_size: int = 10):
        if self._initialized:
            return
        self.queue: asyncio.Queue = asyncio.Queue()
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.monitor = get_resource_monitor()
        self.journey_db = get_journey_persistence()
        self.vault_logger = get_vault_logger()
        self._running = True
        self._initialized = True

        # Start worker as background task
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._worker_task = loop.create_task(self._flush_loop())
        except RuntimeError:
            pass

    async def add_experience(self, data: dict[str, Any]):
        """Add mission experience to the buffer."""
        dilation = self.monitor.get_dilation_factor()

        # HW-Aware Drop: No persistence if system is severely dilated
        if dilation < 0.3:
            logger.warning(f"Persistence skipped due to severe dilation ({dilation:.2f})")
            return

        # Importance Sampling: Reject low-novelty logs if queue is getting full
        if self.queue.qsize() > 100 and data.get("novelty", 1.0) < 0.5:
            logger.info("Dropping low-novelty log to preserve system stability")
            return

        await self.queue.put(data)

    async def _flush_loop(self):
        """Background loop to flush the accumulator to targets."""
        while self._running:
            try:
                if self.queue.empty():
                    await asyncio.sleep(self.flush_interval)
                    continue

                batch = []
                while not self.queue.empty() and len(batch) < self.batch_size:
                    batch.append(await self.queue.get())
                    self.queue.task_done()

                if batch:
                    await self._execute_flush(batch)

                await asyncio.sleep(self.flush_interval)
            except Exception as e:
                logger.error(f"Persistence flush failed: {e}")
                await asyncio.sleep(self.flush_interval)

    async def _execute_flush(self, batch: list[dict[str, Any]]):
        """Coordinate flushes to SurrealDB and Vault."""
        logger.info(f"Flushing {len(batch)} experiences to persistence layer...")

        # SurrealDB Flush (High-freq trajectories)
        try:
            await self.journey_db.persist_batch(batch)
        except Exception as e:
            logger.error(f"SurrealDB batch flush failed: {e}")

        # Vault Flush (High-value architectural insights)
        try:
            await self.vault_logger.log_batch(batch)
        except Exception as e:
            logger.error(f"Vault batch flush failed: {e}")

    async def stop(self):
        """Stop the background worker."""
        self._running = False
        if hasattr(self, "_worker_task"):
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task


def get_accumulator() -> PersistenceAccumulator:
    """Get the global PersistenceAccumulator instance."""
    return PersistenceAccumulator()
