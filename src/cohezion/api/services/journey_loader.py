"""Journey data loader — fetch journey records by ID.

Thin shim so tests can monkeypatch ``load_journey`` without touching
the SurrealDB client.  Production callers should eventually connect
to the SurrealDB journey store; this stub returns an empty dict for
any unknown ID so call-sites degrade gracefully.
"""

from __future__ import annotations

from typing import Any


def load_journey(journey_id: str) -> dict[str, Any]:
    """Return journey data for *journey_id*, or an empty dict if not found."""
    return {}
