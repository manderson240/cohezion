#!/usr/bin/env python3
"""Guardian Reporter - Feeds guardian events into the Cohezion healing system.

Reads guardian_events.jsonl and registers events with the healing system's
DriftDetector. Designed to be run periodically or on-demand.

This keeps the guardian itself dependency-free (pure bash) while still
feeding the compound engineering loop.

Usage:
    uv run python scripts/guardian_reporter.py
    uv run python scripts/guardian_reporter.py --tail 10  # Last 10 events
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

EVENTS_FILE = Path(__file__).parent.parent / "data" / "guardian_events.jsonl"

# Map guardian events to healing system severity
EVENT_SEVERITY = {
    "crash_loop": "failing",
    "high_restarts": "degraded",
    "disk_alert": "degraded",
    "health_check": "healthy",
}


def read_events(tail: int = 0) -> list[dict]:
    """Read guardian events from JSONL file."""
    if not EVENTS_FILE.exists():
        logger.info("No guardian events file found at %s", EVENTS_FILE)
        return []

    events = []
    with open(EVENTS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("Skipping malformed line: %s", e)

    if tail > 0:
        events = events[-tail:]

    return events


def report_to_healing(events: list[dict]) -> None:
    """Register guardian events with the healing system."""
    try:
        from cohezion.healing import DriftDetector, HealthStatus
    except ImportError:
        logger.warning("Could not import cohezion.healing — reporting to stdout only")
        for event in events:
            status = EVENT_SEVERITY.get(event.get("event", ""), "degraded")
            logger.info(
                "  [%s] %s: %s — %s",
                status.upper(),
                event.get("service", "unknown"),
                event.get("event", "unknown"),
                event.get("details", ""),
            )
        return

    detector = DriftDetector()

    for event in events:
        service = event.get("service", "unknown")
        event_type = event.get("event", "unknown")
        restarts = event.get("restarts", 0)
        status_str = EVENT_SEVERITY.get(event_type, "degraded")

        # Set baseline for restart count (0 = healthy)
        detector.set_baseline(service, "restarts", 0)

        # Report current state
        health = detector.check(
            component=service,
            metric="restarts",
            current=float(restarts),
            threshold_pct=0.5,
        )

        logger.info(
            "  [%s] %s: %s (restarts=%d) — %s",
            status_str.upper(),
            service,
            event_type,
            restarts,
            event.get("details", ""),
        )


def main() -> None:
    """Main entry point."""
    tail = 0
    if "--tail" in sys.argv:
        idx = sys.argv.index("--tail")
        if idx + 1 < len(sys.argv):
            tail = int(sys.argv[idx + 1])

    events = read_events(tail=tail)

    if not events:
        logger.info("No guardian events to report.")
        return

    logger.info("Guardian Report (%d events):", len(events))
    report_to_healing(events)
    logger.info("Done.")


if __name__ == "__main__":
    main()
