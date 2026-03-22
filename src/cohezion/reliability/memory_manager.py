"""
Sovereign Memory Manager for Cohezion.
100% local, high-performance semantic memory using Ollama and Qdrant.
Reduces dependency on brittle third-party config loaders.
"""

import json
import logging
import os
from typing import Any

from ollama import Client
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages local persistent memory using Ollama and Qdrant."""

    COLLECTION_NAME = "cohezion_memories"

    def __init__(
        self,
        qdrant_path: str = "/home/mike-anderson/dev/cohezion/storage/memory/qdrant_sovereign",
        ollama_url: str = "http://localhost:11434",
        embed_model: str = "nomic-embed-text:latest",
    ):
        self.ollama = Client(host=ollama_url)
        self.embed_model = embed_model

        # Ensure path exists
        os.makedirs(qdrant_path, exist_ok=True)

        # Initialize Qdrant
        self.qdrant = QdrantClient(path=qdrant_path)

        # Ensure collection exists with correct dimensions (nomic-embed-text is 768)
        try:
            self.qdrant.get_collection(self.COLLECTION_NAME)
        except Exception:
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {self.COLLECTION_NAME}")

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding from local Ollama."""
        res = self.ollama.embeddings(model=self.embed_model, prompt=text)
        return res["embedding"]

    def add(self, data: str, metadata: dict[str, Any] | None = None):
        """Add information to long-term memory."""
        import uuid

        vector = self._get_embedding(data)
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"text": data, **(metadata or {})},
                )
            ],
        )
        return {"id": point_id, "status": "stored"}

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for relevant memories."""
        vector = self._get_embedding(query)
        results = self.qdrant.query_points(collection_name=self.COLLECTION_NAME, query=vector, limit=limit).points

        memories = []
        for res in results:
            memories.append(
                {
                    "id": res.id,
                    # "score": res.score, # query_points might not return score the same way
                    "text": res.payload.get("text"),
                    "metadata": {k: v for k, v in res.payload.items() if k != "text"},
                }
            )
        return memories

    def delete_all(self):
        """Clear the memory manifold."""
        self.qdrant.delete_collection(self.COLLECTION_NAME)
        self.qdrant.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )


if __name__ == "__main__":
    mgr = MemoryManager()
    mgr.add("The Cohezion system is running on a high-density Strix Halo substrate.")
    results = mgr.search("What is the system substrate?")
    print(json.dumps(results, indent=2))
