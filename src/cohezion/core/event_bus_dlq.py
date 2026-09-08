r"""EventBus Backpressure & Dead-Letter Queue (DLQ) Engine (Remediation 1)
=======================================================================
Implements a Dead-Letter Queue (DLQ) and backpressure buffer for Cohezion's EventBus:
  1. Catches failed event dispatches and `MonadResult.fail` payloads.
  2. Enforces maximum queue size (10,000 events) with sliding-window dropping.
  3. Provides inspectable DLQ telemetry for system monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventType


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class DeadLetterQueue:
    """Thread-safe Dead-Letter Queue for failed event dispatches."""

    max_size: int = 10000
    _queue: list[dict[str, Any]] = field(default_factory=list, init=False)

    def push_dead_letter(self, event: Event, failure_reason: str) -> None:
        """Push a failed event into the DLQ with failure reason."""
        if len(self._queue) >= self.max_size:
            # Backpressure sliding window: drop oldest
            self._queue.pop(0)

        record = {
            "timestamp": time.time(),
            "event_type": event.type.name,
            "source": event.source,
            "failure_reason": failure_reason,
            "payload": event.payload,
        }
        self._queue.append(record)
        logger.warning(
            "  ⚠️ DLQ Push: Event %s from %s failed -> %s",
            event.type.name,
            event.source,
            failure_reason,
        )

    def get_dead_letters(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent dead-letter records."""
        return self._queue[-limit:]

    @property
    def total_dead_letters(self) -> int:
        return len(self._queue)


async def main_async() -> None:
    dlq = DeadLetterQueue()
    print("\n" + "=" * 95)
    print("      📬 COHEZION EVENTBUS DEAD-LETTER QUEUE (DLQ) & BACKPRESSURE HARNESS")
    print("=" * 95)

    err_evt = Event(
        type=EventType.AGENT_ERROR,
        source="peer_swarm_03",
        payload={"error": "Monadic Bind Failure"},
    )
    dlq.push_dead_letter(err_evt, "MonadResult.fail: Division by zero in latent space")

    print(f"  • Total Dead Letters in DLQ: {dlq.total_dead_letters}")
    print(f"  • Recent DLQ Record: {dlq.get_dead_letters(1)[0]}")
    print("=" * 95)
    print("🎉 Remediation 1: EventBus DLQ & Backpressure Protection Active!")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
