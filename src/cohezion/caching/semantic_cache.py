
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any

from cohezion.db.admin import DBAdmin
from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Semantically aware cache using SurrealDB's vector search (HNSW).
    
    Pattern:
    1. Embed query -> Vector (768-dim)
    2. Search -> SELECT * FROM semantic_cache WHERE embedding <|4|> $vec AND dist < threshold
    3. Return cached response if hit.
    """
    def __init__(self, db_admin: Optional[DBAdmin] = None, threshold: float = 0.95):
        self.dba = db_admin or DBAdmin()
        self.threshold = threshold
        # Initialize encoder lazily to avoid heavy load on import if not used
        self._encoder = None

    @property
    def encoder(self):
        # We don't need the full FlumeEncoder (PyTorch) if we just want embeddings.
        # This prevents VRAM OOM by avoiding torch load.
        class LightweightEncoder:
            def get_semantic_vector(self, text: str):
                import requests
                try:
                    # Retry logic for robustness
                    for _ in range(3):
                        response = requests.post(
                            "http://localhost:11434/api/embeddings",
                            json={"model": "nomic-embed-text", "prompt": text},
                            timeout=30,
                        )
                        if response.status_code == 200:
                            embedding = response.json()["embedding"]
                            # Return as pseudo-tensor wrapper to match API if needed, 
                            # but consumer expects list or tensor.
                            import torch
                            return torch.tensor(embedding)
                        time.sleep(1)
                    logger.error(f"Ollama embedding failed: {response.text}")
                except Exception as e:
                    logger.error(f"Ollama connection failed: {e}")
                
                # Fallback zero vector if completely failed
                import torch
                return torch.zeros(768)

        if self._encoder is None:
            self._encoder = LightweightEncoder()
        return self._encoder
    
    async def connect(self):
        """Ensure DB connection."""
        try:
           # DBAdmin.connect() doesn't return bool, just raises or logs.
           # But we can check self.dba.client...
           # Actually DBAdmin manages its own client.
           await self.dba.connect()
        except Exception as e:
            logger.error(f"SemanticCache connection error: {e}")

    async def get(self, query_text: str) -> Optional[str]:
        """
        Retrieve semantically similar response from cache.
        """
        try:
            # 1. Embed
            # Note: get_semantic_vector returns a torch.Tensor
            vec_tensor = self.encoder.get_semantic_vector(query_text)
            vec_list = vec_tensor.tolist() # Convert to list for JSON serialization

            # 2. Search
            # Cosine similarity in SurrealDB: vector::similarity::cosine(v1, v2)
            # OR using the syntax <|4|> (KNN for Cosine Distance?? Wait.
            # SurrealDB documentation for HNSW:
            # <|KNN_DIST|>: 
            # <|1|> : Euclidean
            # <|2|> : Manhattan
            # <|3|> : Hammin
            # <|4|> : Cosine Distance (Returns distance output field 'dist') -- WAIT.
            
            # Since index is defined as DIST COSINE, the operator <|4|> performs KNN search.
            # However, typically we want to filter by proximity.
            
            # Syntax: 
            # SELECT *, vector::similarity::cosine(embedding, $vec) as sim 
            # FROM semantic_cache 
            # WHERE embedding <|4|> $vec 
            # ORDER BY sim DESC LIMIT 1;
            
            query = """
            SELECT query_text, response_content, vector::similarity::cosine(embedding, $vec) as sim
            FROM semantic_cache
            WHERE embedding <|4|> $vec
            ORDER BY embedding <|4|> $vec ASC
            LIMIT 1;
            """
            
            # Execute
            result = await self.dba.client.query(query, {"vec": vec_list})
            
            # Parse
            # result structure depends on client wrapper.
            # If using DBAdmin._parse_results logic:
            if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
                rows = result[0]['result']
            else:
                rows = result
            
            if not rows or len(rows) == 0:
                return None
            
            best_match = rows[0]
            sim = best_match.get('sim', 0.0)
            
            if sim >= self.threshold:
                logger.info(f"⚡ CACHE HIT: '{query_text}' matches '{best_match['query_text']}' (sim={sim:.4f})")
                return best_match['response_content']
            
            logger.info(f"💨 CACHE MISS: Best match sim={sim:.4f} < {self.threshold:.4f}")
            return None
            
        except Exception as e:
            logger.error(f"SemanticCache.get failed: {e}")
            return None

    async def set(self, query_text: str, response_content: str):
        """
        Cache a response.
        """
        try:
            vec_tensor = self.encoder.get_semantic_vector(query_text)
            logger.info(f"Generated Vector Dim: {vec_tensor.shape[0]}")
            vec_list = vec_tensor.tolist()
            
            record = {
                "query_text": query_text,
                "response_content": response_content,
                "embedding": vec_list,
                "created_at": datetime.now().isoformat()
            }
            
            # Insert
            await self.dba.client.create("semantic_cache", record)
            logger.info(f"💾 CACHED: {query_text[:50]}...")
            
        except Exception as e:
            logger.error(f"SemanticCache.set failed: {e}")

from datetime import datetime
