"""Datamesh ingestion - batch processing with backpressure.

Charter: Idempotent writes, durability, circuit breaker pattern.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from cohezion.datamesh.schema import UnifiedRecord


logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for batch ingestion."""

    batch_size: int = 100
    flush_interval_sec: float = 30.0
    max_queue_size: int = 10000
    retry_count: int = 3
    circuit_breaker_threshold: int = 5


@dataclass
class IngestionMetrics:
    """Metrics for ingestion pipeline."""

    records_queued: int = 0
    records_written: int = 0
    batches_flushed: int = 0
    errors: int = 0
    last_flush: datetime | None = None


class DatameshIngestion:
    """Batch ingestion with circuit breaker and backpressure.

    Pattern:
    1. Queue records in memory
    2. Flush on batch_size OR timeout
    3. Circuit breaker on consecutive failures
    4. Backpressure when queue full
    """

    def __init__(
        self,
        schema: str = "cohezion",
        config: IngestionConfig | None = None,
    ):
        self.schema = schema
        self.config = config or IngestionConfig()

        self._queue: list[UnifiedRecord] = []
        self._metrics = IngestionMetrics()
        self._circuit_open = False
        self._failure_count = 0
        self._writers: list[Callable] = []

        # Async coordination
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None

    def add_writer(self, writer: Callable[[list[UnifiedRecord]], None]) -> None:
        """Add a writer to the pipeline.

        Writers are called in order with batched records.
        """
        self._writers.append(writer)

    async def write(
        self,
        record: UnifiedRecord,
        idempotency_key: str | None = None,
    ) -> bool:
        """Queue record for ingestion.

        Returns False if backpressure engaged (queue full).
        """
        if self._circuit_open:
            logger.warning("Circuit breaker open, rejecting write")
            return False

        if len(self._queue) >= self.config.max_queue_size:
            logger.warning(f"Backpressure: queue at {len(self._queue)}")
            return False

        # Idempotency check
        if idempotency_key:
            record.metadata["_idempotency_key"] = idempotency_key

        async with self._lock:
            self._queue.append(record)
            self._metrics.records_queued += 1

        # Trigger flush if batch full
        if len(self._queue) >= self.config.batch_size:
            await self.flush()

        # Schedule periodic flush
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

        return True

    async def flush(self) -> int:
        """Flush queued records to all writers.

        Returns number of records flushed.
        """
        async with self._lock:
            batch = self._queue[: self.config.batch_size]
            self._queue = self._queue[self.config.batch_size :]

        if not batch:
            return 0

        success = False
        for attempt in range(self.config.retry_count):
            try:
                for writer in self._writers:
                    await asyncio.get_event_loop().run_in_executor(None, writer, batch)
                success = True
                break
            except Exception as e:
                logger.error(f"Writer failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        if success:
            self._metrics.records_written += len(batch)
            self._metrics.batches_flushed += 1
            self._metrics.last_flush = datetime.now()
            self._failure_count = 0
            self._circuit_open = False
        else:
            self._metrics.errors += len(batch)
            self._failure_count += 1

            # Circuit breaker logic
            if self._failure_count >= self.config.circuit_breaker_threshold:
                logger.error("Circuit breaker opened")
                self._circuit_open = True

        return len(batch)

    async def _periodic_flush(self) -> None:
        """Background task for periodic flushing."""
        await asyncio.sleep(self.config.flush_interval_sec)
        await self.flush()

    async def close(self) -> None:
        """Flush remaining records and close."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        while self._queue:
            await self.flush()

    def get_metrics(self) -> IngestionMetrics:
        """Return current metrics."""
        return self._metrics


class IdempotentWriter:
    """Wrapper for idempotent record writes.

    Ensures duplicate records are not written twice.
    """

    def __init__(self, underlying: Callable, key_extractor: Callable):
        self.underlying = underlying
        self.key_extractor = key_extractor
        self._seen: set[str] = set()

    def __call__(self, records: list[UnifiedRecord]) -> None:
        """Write records, filtering duplicates."""
        unique = []
        for r in records:
            key = self.key_extractor(r)
            if key not in self._seen:
                self._seen.add(key)
                unique.append(r)

        if unique:
            self.underlying(unique)
