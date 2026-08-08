"""Delegation Logger for Cohezion Proactive Hybrid Router.

Logs all model routing and escalation events (EVI calculations, quality gaps, costs)
to SurrealDB `delegation_log` table and local fallback store.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import urllib.request
import threading


logger = logging.getLogger(__name__)

FALLBACK_LOG_PATH = Path.home() / ".cohezion" / "delegation_log.jsonl"


@dataclass
class DelegationEvent:
    """Record of an escalation or routing delegation decision."""

    task_name: str
    task_importance: float  # Scale 0.0 - 1.0
    quality_gap: float  # Scale 0.0 - 1.0
    escalation_cost: float  # Relative cost unit (> 0)
    evi_score: float  # Computed EVI score
    source_tier: int  # 1 (Local), 2 (Ollama Cloud), 3 (Premium API)
    target_tier: int  # 1, 2, or 3
    escalated: bool  # True if tier increased
    model_selected: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return asdict(self)


class DelegationLogger:
    """Non-blocking logger for hybrid delegation and escalation events."""

    def __init__(self, surreal_url: str = "http://localhost:8001", db_ns: str = "cohezion", db_name: str = "main") -> None:
        self.surreal_url = surreal_url.rstrip("/")
        self.db_ns = db_ns
        self.db_name = db_name
        self.fallback_path = FALLBACK_LOG_PATH
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_delegation(self, event: DelegationEvent) -> None:
        """Log delegation event asynchronously without blocking caller."""
        event_dict = event.to_dict()
        
        # Local JSONL file fallback (thread-safe, persistent)
        try:
            with self._lock:
                with open(self.fallback_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event_dict) + "\n")
                    f.flush()
        except Exception as exc:
            logger.warning("Failed to write local delegation log: %s", exc)

        # Asynchronous SurrealDB push
        def _surreal_push() -> None:
            sql = f"CREATE delegation_log CONTENT {json.dumps(event_dict)};"
            req = urllib.request.Request(
                f"{self.surreal_url}/sql",
                data=sql.encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "surreal-ns": self.db_ns,
                    "surreal-db": self.db_name,
                    "Authorization": "Basic " + __import__("base64").b64encode(b"root:root").decode(),
                },
                method="POST",
            )
            try:
                urllib.request.urlopen(req, timeout=2)
            except Exception as exc:
                logger.debug("SurrealDB delegation_log push offline: %s", exc)

        threading.Thread(target=_surreal_push, daemon=True).start()

    def get_recent_events(self, limit: int = 20) -> list[Dict[str, Any]]:
        """Read recent local delegation events."""
        if not self.fallback_path.exists():
            return []
        events = []
        try:
            with open(self.fallback_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as exc:
            logger.error("Error reading delegation logs: %s", exc)
        return events
