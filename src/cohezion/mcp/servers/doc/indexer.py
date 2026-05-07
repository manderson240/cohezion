# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
"""BMAD Doc Retriever - Token-efficient document retrieval with compound session management.

Elegant simplicity: Minimal code, maximum context awareness.

Features:
- Smart chunking (semantic + token-based)
- Local Ollama embeddings (free, fast)
- SurrealDB vector search
- Context7-compatible interface
- Compound session checkpointing
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocChunk:
    """Token-efficient document chunk."""

    chunk_id: str
    library_id: str
    content: str
    token_count: int
    embedding: list[float] | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "library_id": self.library_id,
            "content": self.content,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


class TokenCounter:
    """Simple token counter using approximate word-based counting."""

    # Approximate: 1 token ≈ 0.75 words for English
    TOKENS_PER_WORD = 0.75

    @classmethod
    def count(cls, text: str) -> int:
        """Estimate token count."""
        words = len(text.split())
        return int(words / cls.TOKENS_PER_WORD)


class SmartChunker:
    """Hybrid chunking: semantic boundaries + token limits."""

    DEFAULT_MAX_TOKENS = 512
    DEFAULT_OVERLAP = 128

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS, overlap: int = DEFAULT_OVERLAP):
        self.max_tokens = max_tokens
        self.overlap = overlap

    def chunk(self, content: str, library_id: str, source_path: str) -> list[DocChunk]:
        """Chunk document intelligently."""
        chunks = []

        # Split by semantic boundaries (headers)
        sections = self._split_by_headers(content)

        for section in sections:
            section_tokens = TokenCounter.count(section)

            if section_tokens <= self.max_tokens:
                # Section fits in one chunk
                chunk_id = self._hash_chunk(section, library_id)
                chunks.append(
                    DocChunk(
                        chunk_id=chunk_id,
                        library_id=library_id,
                        content=section,
                        token_count=section_tokens,
                        metadata={"source": source_path, "strategy": "semantic"},
                    )
                )
            else:
                # Need to split further by token limit
                sub_chunks = self._chunk_by_tokens(section, library_id, source_path)
                chunks.extend(sub_chunks)

        return chunks

    def _split_by_headers(self, content: str) -> list[str]:
        """Split content by markdown headers."""
        # Match headers (# ## ###)
        pattern = r"(?=\n#{1,6}\s)"
        parts = re.split(pattern, content)

        # Clean up
        sections = [p.strip() for p in parts if p.strip()]

        if not sections:
            # No headers, treat as single section
            sections = [content]

        return sections

    def _chunk_by_tokens(self, content: str, library_id: str, source_path: str) -> list[DocChunk]:
        """Chunk by token limit with overlap."""
        chunks = []
        words = content.split()

        # Convert token limits to word limits
        max_words = int(self.max_tokens * TokenCounter.TOKENS_PER_WORD)
        overlap_words = int(self.overlap * TokenCounter.TOKENS_PER_WORD)

        start = 0
        chunk_idx = 0

        while start < len(words):
            end = min(start + max_words, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunk_id = self._hash_chunk(chunk_text, library_id, str(chunk_idx))
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    library_id=library_id,
                    content=chunk_text,
                    token_count=TokenCounter.count(chunk_text),
                    metadata={"source": source_path, "strategy": "token", "index": chunk_idx},
                )
            )

            # Move with overlap
            start += max_words - overlap_words
            chunk_idx += 1

        return chunks

    @staticmethod
    def _hash_chunk(content: str, library_id: str, suffix: str = "") -> str:
        """Generate unique chunk ID."""
        hash_input = f"{library_id}:{content[:100]}:{suffix}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


class OllamaEmbedder:
    """Local embedding using Ollama (no API costs)."""

    DEFAULT_MODEL = "nomic-embed-text"  # 768 dims, fast
    DIMENSIONS = 768

    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._available: bool | None = None

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        if self._available is not None:
            return self._available

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=2.0)
                self._available = resp.status_code == 200
        except Exception:
            self._available = False

        return self._available

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        if not await self.is_available():
            raise RuntimeError("Ollama not available. Run: ollama pull nomic-embed-text")

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed (sequential for simplicity)."""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings


class SimpleSurrealStore:
    """Minimal SurrealDB wrapper for document chunks."""

    def __init__(
        self, url: str = "ws://localhost:8001/rpc", namespace: str = "bmad", database: str = "docs"
    ):
        self.url = url
        self.namespace = namespace
        self.database = database
        self._client = None

    async def connect(self):
        """Connect to SurrealDB."""
        from surrealdb import AsyncSurreal

        self._client = AsyncSurreal(self.url)
        await self._client.connect()
        await self._client.use(self.namespace, self.database)
        logger.info(f"Connected to SurrealDB: {self.url}")

    async def store_chunk(self, chunk: DocChunk) -> bool:
        """Store a document chunk with embedding."""
        if not self._client:
            await self.connect()

        data = {
            "id": f"doc_chunks:{chunk.chunk_id}",
            "library_id": chunk.library_id,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "embedding": chunk.embedding or [],
            "metadata": chunk.metadata,
            "created_at": "time::now()",
        }

        try:
            await self._client.create(f"doc_chunks:{chunk.chunk_id}", data)
            return True
        except Exception as e:
            logger.warning(f"Failed to store chunk: {e}")
            return False

    async def search_similar(
        self,
        query_embedding: list[float],
        library_id: str | None = None,
        limit: int = 5,
        max_tokens: int = 2000,
    ) -> list[DocChunk]:
        """Search for similar chunks using vector similarity."""
        if not self._client:
            await self.connect()

        # Build query
        if library_id:
            sql = """
            SELECT *, vector::similarity::cosine(embedding, $embedding) as score
            FROM doc_chunks
            WHERE library_id = $library_id
            ORDER BY score DESC
            LIMIT $limit
            """
            params = {"embedding": query_embedding, "library_id": library_id, "limit": limit}
        else:
            sql = """
            SELECT *, vector::similarity::cosine(embedding, $embedding) as score
            FROM doc_chunks
            ORDER BY score DESC
            LIMIT $limit
            """
            params = {"embedding": query_embedding, "limit": limit}

        try:
            results = await self._client.query(sql, params)

            chunks = []
            total_tokens = 0

            for row in results[0]["result"]:
                chunk = DocChunk(
                    chunk_id=row["id"].split(":")[1],
                    library_id=row["library_id"],
                    content=row["content"],
                    token_count=row["token_count"],
                    metadata={**row.get("metadata", {}), "score": row.get("score", 0)},
                )

                # Respect token limit
                if total_tokens + chunk.token_count <= max_tokens:
                    chunks.append(chunk)
                    total_tokens += chunk.token_count
                else:
                    break

            return chunks
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_library_stats(self, library_id: str) -> dict:
        """Get statistics for a library."""
        if not self._client:
            await self.connect()

        try:
            result = await self._client.query(
                "SELECT count() as total_chunks, sum(token_count) as total_tokens FROM doc_chunks WHERE library_id = $library_id",
                {"library_id": library_id},
            )
            return result[0]["result"][0] if result[0]["result"] else {}
        except Exception as e:
            logger.error(f"Stats query failed: {e}")
            return {}


class DocumentIndexer:
    """Main indexer: Parse → Chunk → Embed → Store."""

    def __init__(
        self,
        store: SimpleSurrealStore,
        embedder: OllamaEmbedder,
        chunker: SmartChunker | None = None,
    ):
        self.store = store
        self.embedder = embedder
        self.chunker = chunker or SmartChunker()

    async def index_library(self, library_id: str, source_path: Path) -> dict:
        """Index an entire library directory."""
        from cohezion.mcp.servers.safe_input import sanitize_path

        try:
            safe_source = sanitize_path(str(source_path), base_dir=Path.cwd())
        except ValueError:
            return {"error": f"Path escapes allowed directory: {source_path}"}

        logger.info(f"Indexing library: {library_id} from {safe_source}")

        md_files = list(safe_source.rglob("*.md"))
        total_chunks = 0
        total_tokens = 0

        for md_file in md_files:
            try:
                content = md_file.read_text()
                chunks = self.chunker.chunk(content, library_id, str(md_file))

                # Generate embeddings
                for chunk in chunks:
                    try:
                        embedding = await self.embedder.embed(chunk.content)
                        chunk = DocChunk(
                            chunk_id=chunk.chunk_id,
                            library_id=chunk.library_id,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            embedding=embedding,
                            metadata=chunk.metadata,
                        )

                        if await self.store.store_chunk(chunk):
                            total_chunks += 1
                            total_tokens += chunk.token_count
                    except Exception as e:
                        logger.warning(f"Failed to embed chunk: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Failed to index {md_file}: {e}")
                continue

        return {
            "library_id": library_id,
            "files_indexed": len(md_files),
            "chunks_created": total_chunks,
            "total_tokens": total_tokens,
        }

    async def retrieve(
        self, query: str, library_id: str | None = None, max_tokens: int = 2000
    ) -> dict:
        """Retrieve relevant chunks for a query."""
        logger.info(f"Retrieving docs for: '{query}' from {library_id or 'all'}")

        # Embed query
        query_embedding = await self.embedder.embed(query)

        # Search
        chunks = await self.store.search_similar(
            query_embedding, library_id, limit=10, max_tokens=max_tokens
        )

        total_tokens = sum(c.token_count for c in chunks)

        return {
            "query": query,
            "library_id": library_id,
            "chunks": [c.to_dict() for c in chunks],
            "chunk_count": len(chunks),
            "total_tokens": total_tokens,
            "source": "local",
        }


# Compound session integration
class DocRetrieverSession:
    """Compound session-aware doc retriever."""

    def __init__(self, indexer: DocumentIndexer, session_id: str):
        self.indexer = indexer
        self.session_id = session_id
        self.query_history: list[dict] = []

    async def retrieve_with_context(self, query: str, max_tokens: int = 2000) -> dict:
        """Retrieve with session context awareness."""
        # Use session history to enhance retrieval
        context = self._build_context()

        # Enhance query with context
        enhanced_query = f"{context} {query}".strip() if context else query

        result = await self.indexer.retrieve(enhanced_query, max_tokens=max_tokens)

        # Track for checkpointing
        self.query_history.append(
            {
                "query": query,
                "enhanced": enhanced_query,
                "tokens_used": result["total_tokens"],
                "timestamp": "time::now()",
            }
        )

        return result

    def _build_context(self) -> str:
        """Build context from recent queries."""
        if not self.query_history:
            return ""

        # Take last 3 queries as context
        recent = self.query_history[-3:]
        keywords = []

        for q in recent:
            # Extract key terms (simple approach)
            words = q["query"].split()[:5]
            keywords.extend(words)

        return " ".join(set(keywords))[:200]  # Limit context size


# Convenience functions
async def create_indexer() -> DocumentIndexer:
    """Factory: Create configured indexer."""
    store = SimpleSurrealStore()
    embedder = OllamaEmbedder()

    await store.connect()

    return DocumentIndexer(store, embedder)


async def index_bmad_docs() -> dict:
    """Index all BMAD documentation."""
    indexer = await create_indexer()

    bmad_path = Path("_bmad")

    # Index each module
    results = {}
    for module_dir in bmad_path.iterdir():
        if module_dir.is_dir() and not module_dir.name.startswith("_"):
            library_id = f"bmad/{module_dir.name}"
            result = await indexer.index_library(library_id, module_dir)
            results[library_id] = result

    return results


__all__ = [
    "DocChunk",
    "DocRetrieverSession",
    "DocumentIndexer",
    "OllamaEmbedder",
    "SimpleSurrealStore",
    "SmartChunker",
    "TokenCounter",
    "create_indexer",
    "index_bmad_docs",
]
