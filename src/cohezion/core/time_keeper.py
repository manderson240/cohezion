"""
TimeKeeper Core Service.

Responsible for:
1. Providing a unified, high-precision clock source (ISO-8601 UTC).
2. Logging operational events to SurrealDB for velocity tracking.
3. Calculating current velocity metrics.

Part of Gateway 11 (Temporal Mastery) foundation.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from cohezion.db.surreal_client import SurrealClient

logger = logging.getLogger(__name__)

class TimeKeeper:
    def __init__(self, db_client: Optional[SurrealClient] = None):
        self.db = db_client or SurrealClient()
        self._session_start = time.perf_counter()
        
    @property
    def now_iso(self) -> str:
        """Return current time in ISO-8601 format with UTC timezone."""
        return datetime.now(timezone.utc).isoformat()
    
    @property
    def session_uptime(self) -> float:
        """Return seconds since session start."""
        return time.perf_counter() - self._session_start
        
    async def log_event(self, 
                        agent_name: str, 
                        event_type: str, 
                        details: Dict[str, Any],
                        duration_ms: float = 0.0) -> None:
        """
        Log an operational event to the 'velocity_events' table in SurrealDB.
        
        Args:
            agent_name: Name of the agent performed the action (e.g. 'AnalystAgent')
            event_type: Type of event (e.g. 'TASK_COMPLETE', 'TOOL_USE')
            details: JSON-serializable dictionary of event details
            duration_ms: Execution time in milliseconds
        """
        timestamp = self.now_iso
        
        record = {
            "timestamp": timestamp,
            "agent": agent_name,
            "type": event_type,
            "details": details,
            "duration_ms": duration_ms,
            "session_id": "current_session" # In future, inject real session ID
        }
        
        try:
            # Fire and forget logging to avoid blocking critical path
            # In a real async loop we might want to batch these
            # For now, we await to ensure it's written
            await self.db.query(
                "CREATE velocity_events CONTENT $data",
                {"data": record}
            )
            logger.debug(f"Logged event: {event_type} by {agent_name}")
            
        except Exception as e:
            # Never crash due to logging failure
            logger.warning(f"Failed to log velocity event: {e}")

    async def calculate_velocity(self, window_minutes: int = 60) -> float:
        """
        Calculate velocity (Tasks/Hour) over the last window_minutes.
        """
        query = """
        SELECT count() as count 
        FROM velocity_events 
        WHERE type = 'TASK_COMPLETE' 
        AND <datetime>timestamp > time::now() - <duration>$window
        GROUP ALL
        """
        
        try:
            result = await self.db.query(query, {"window": f"{window_minutes}m"})
            # Result is like [{'count': N}]
            if result and len(result) > 0 and 'count' in result[0]:
                return float(result[0]['count'])
            return 0.0
        except Exception as e:
            logger.error(f"Failed to calculate velocity: {e}")
            return 0.0

# Singleton instance
_INSTANCE = None

def get_time_keeper() -> TimeKeeper:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = TimeKeeper()
    return _INSTANCE
