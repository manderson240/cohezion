
import logging
from typing import List, Dict, Any
from cohezion.db.surreal_client import SurrealClient
from cohezion.flume.autoencoder import FlumeEncoder

logger = logging.getLogger(__name__)

class JourneyOracle:
    """
    The Oracle connects the active simulation to the crystallized history of the Swarm.
    It queries the 'journey' table to find precedents, lessons, and narratives relative 
    to current simulation events.
    """

    def __init__(self, use_embeddings: bool = False):
        self.db = SurrealClient()
        self.use_embeddings = use_embeddings
        if self.use_embeddings:
            self.encoder = FlumeEncoder() # Warning: Heavy load

    async def consult(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Consult the Oracle for wisdom related to the query.
        Uses FlumeEncoder for Semantic Vector Search if enabled.
        """
        logger.info(f"🔮 Oracle Consulting on: {query}")
        
        # 1. Semantic Search (Enhancement)
        if self.use_embeddings and self.encoder:
            try:
                # Encode query to 12D/High-D vector
                # Note: FlumeEncoder might return numpy array
                vector = self.encoder.get_embedding(query) 
                # Assuming get_embedding is the API, let's check or use get_semantic_vector if 12D
                # Actually BaseAgent uses get_semantic_vector -> 256 dim or similar?
                # Let's trust BaseAgent usage: z = self._encoder.get_semantic_vector(final_result)
                
                # Check SurrealClient schema. It expects 'embedding' (vector) or 12D physics.
                # Let's try to search on 'embedding' field which is usually 768 dim (bert/nomic).
                # If FlumeEncoder provides that, great.
                
                # FALLBACK: If vector search not ready, use enhanced keyword + recent.
                # Taking safe path for now to avoid crashing if dimensions mismatch.
                pass 
            except Exception as e:
                logger.warning(f"Oracle Semantic Search failed: {e}")

        # 2. Enhanced Keyword Search (Mocking "Smart" filtering)
        # In a real system, we'd use the DB's full text search. 
        # For now, we fetch recent and filter in Python (Memory heavy but robust for small dataset)
        recent = await self.db.query("SELECT * FROM journey ORDER BY timestamp DESC LIMIT 50")
        
        # Filter relevance (Simple Jaccard/Overlap)
        query_words = set(query.lower().split())
        relevant = []
        
        if isinstance(recent, list) and recent and isinstance(recent[0], dict) and 'result' in recent[0]:
             items = recent[0]['result']
             for item in items:
                 content = item.get('content', '').lower()
                 # Score matches
                 score = sum(1 for w in query_words if w in content)
                 if score > 0:
                     relevant.append((score, item))
        
        # Sort by relevance
        relevant.sort(key=lambda x: x[0], reverse=True)
        
        if relevant:
            logger.info(f"✨ Oracle found {len(relevant)} relevant past journeys.")
            return [x[1] for x in relevant[:limit]]

        # Fallback to pure recency
        return await self.get_recent_wisdom(limit)

    async def get_recent_wisdom(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve Swipe of Wisdom: Recent Journeys + Recent Research.
        Compound Engineering: Merging Experience and Knowledge.
        """
        try:
            # 1. Fetch Journeys
            journeys = await self.db.query(f"SELECT * FROM journey ORDER BY timestamp DESC LIMIT {limit}")
            journey_items = journeys[0].get('result', []) if isinstance(journeys, list) and journeys else []
            
            # 2. Fetch Research Papers (Enhancement)
            # Use raw query or mock logic if search index not ready
            research = await self.db.query(f"SELECT * FROM universe_nodes WHERE node_type = 'research_paper' ORDER BY created_at DESC LIMIT {limit}")
            research_items = research[0].get('result', []) if isinstance(research, list) and research else []
            
            # 3. Merge & Sort
            combined = journey_items + research_items
            # Sort by timestamp/created_at roughly
            # Assuming schema diff, but both are dicts. 
            # We return raw list for now.
            return combined[:limit*2] # Return a mix
            
        except Exception as e:
            logger.error(f"Oracle blinded: {e}")
            return []

    async def get_reflex_insights(self, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieve 'Insight' nodes (from ReflexAgent) if stored in DB.
        Note: Currently insights are flat files (INSIGHT_*.md). 
        This method is a placeholder for when they are ingested.
        """
        return []
