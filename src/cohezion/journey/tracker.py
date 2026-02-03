
import logging
import datetime
from cohezion.core.persistence.surreal_client import UniverseNode, SurrealClient

logger = logging.getLogger(__name__)

class JourneyTracker:
    """
    Captures the Agentic Journeys of the Swarm.
    Logs significant events (Consensus, Discoveries, Mutations) to SurrealDB.
    """
    
    def __init__(self, db_client: SurrealClient):
        self._db = db_client

    async def log_event(self, event_type: str, agent_id: str, content: str, metadata: dict = None):
        """
        Logs a journey event.
        """
        try:
            # Phase 86: Sanitize ID to avoid SurrealDB parse errors (no dots)
            ts = int(datetime.datetime.now().timestamp() * 1000)
            event_id = f"journey_{ts}_{agent_id}"
            
            node = UniverseNode(
                id=event_id,
                node_type="journey_event",
                content=content,
                metadata={
                    "event_type": event_type,
                    "agent_id": agent_id,
                    "timestamp": datetime.datetime.now().isoformat(),
                    **(metadata or {})
                }
            )
            
            await self._db.store_node(node)
            logger.info(f"📜 Journey Logged: [{event_type}] {content}")
            
        except Exception as e:
            logger.error(f"Failed to log journey: {e}")
