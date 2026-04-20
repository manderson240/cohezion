"""
GraphRAG Import: Vault documents → SurrealDB with embeddings + graph edges

Handles bulk import with:
- Ollama embeddings (nomic-embed-text)
- Wiki-link parsing → graph edges
- Batch operations for performance
- Error handling for edge cases
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from .graphrag_helpers import (
    GraphRAGError,
    batch_create_edges,
    detect_document_type,
    escape_sql,
    execute_surreal_async,
    parse_frontmatter,
    parse_wiki_links,
    slugify,
)


logger = logging.getLogger(__name__)


class GraphRAGImporter:
    """Import vault documents to SurrealDB with GraphRAG"""

    def __init__(
        self,
        vault_path: Path,
        ollama_url: str = "http://localhost:11434",
        surrealdb_url: str = "http://localhost:8001",
        namespace: str = "cohezion",
        database: str = "vault",
        embedding_model: str = "nomic-embed-text:latest",
        max_concurrent: int = 10,
    ):
        self.vault_path = Path(vault_path).resolve()
        self.ollama_url = ollama_url.rstrip("/")
        self.surrealdb_url = surrealdb_url
        self.namespace = namespace
        self.database = database
        self.embedding_model = embedding_model
        self.max_concurrent = max_concurrent

        self.http_client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding via Ollama"""
        if not self.http_client:
            raise GraphRAGError(
                "HTTP client not initialized (use async context manager)"
            )

        try:
            # Truncate to reasonable length (2K chars ~500 tokens)
            text = text[:2000]

            response = await self.http_client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get("embedding", [])
            if not embedding:
                raise GraphRAGError("No embedding returned from Ollama")

            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return None to allow import without embedding
            return None

    async def import_document(
        self, file_path: Path, create_edges: bool = True
    ) -> str | None:
        """
        Import single document to SurrealDB

        Args:
            file_path: Path to markdown file
            create_edges: If True, parse wiki-links and create edges

        Returns:
            Document ID if successful, None if failed
        """
        if not self.http_client:
            raise GraphRAGError("HTTP client not initialized")

        try:
            # Read file
            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter
            frontmatter, body = parse_frontmatter(content)

            # Detect document type
            doc_type = detect_document_type(file_path, self.vault_path)

            # Generate embedding
            embedding = await self.generate_embedding(body)

            # Create document ID
            doc_id = f"vault_memory:{slugify(file_path.stem)}"

            # Build UPSERT query (DELETE + CREATE for true upsert)
            embedding_json = (
                f"[{','.join(map(str, embedding))}]" if embedding else "NONE"
            )

            query = f"""
            DELETE {doc_id};
            CREATE {doc_id} SET
                type = '{doc_type}',
                path = '{file_path.relative_to(self.vault_path)}',
                title = '{escape_sql(frontmatter.get("title", file_path.stem))}',
                content = '{escape_sql(body[:1000])}',
                embedding = {embedding_json},
                embedding_model = '{self.embedding_model}',
                embedding_dim = {len(embedding) if embedding else 0},
                tags = {frontmatter.get("tags", [])},
                created_at = time::now();
            """

            # Execute query (returns [DELETE result, CREATE result])
            results = await execute_surreal_async(
                query,
                self.http_client,
                self.namespace,
                self.database,
                url=self.surrealdb_url.rstrip("/") + "/sql",
            )

            # Check CREATE result (index 1, after DELETE)
            if not results or len(results) < 2 or results[1].get("status") != "OK":
                logger.error(f"Failed to create document {doc_id}: {results}")
                return None

            logger.info(f"Imported {doc_id} ({doc_type})")

            # Create graph edges from wiki-links
            if create_edges:
                await self._create_edges_for_document(doc_id, body)

            return doc_id

        except Exception as e:
            logger.error(f"Failed to import {file_path}: {e}")
            return None

    async def _create_edges_for_document(self, source_id: str, content: str):
        """Parse wiki-links and create graph edges"""
        if not self.http_client:
            return

        # Parse wiki-links
        links = parse_wiki_links(content)
        if not links:
            return

        # Create edges in batch
        edges = []
        for link in links:
            target_id = f"vault_memory:{slugify(link)}"
            edges.append(
                {
                    "source": source_id,
                    "type": "informed_by",
                    "target": target_id,
                    "metadata": {"how": "Referenced in document body"},
                }
            )

        if edges:
            count = await batch_create_edges(
                edges,
                self.http_client,
                self.namespace,
                self.database,
                self.max_concurrent,
            )
            logger.info(f"Created {count}/{len(edges)} edges for {source_id}")

    async def import_directory(
        self, directory: str, pattern: str = "*.md", recursive: bool = True
    ) -> dict[str, int]:
        """
        Import all documents from directory

        Args:
            directory: Directory name (decisions, patterns, experiments)
            pattern: File pattern to match
            recursive: Search recursively

        Returns:
            Stats dict with counts
        """
        dir_path = self.vault_path / directory

        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return {"total": 0, "success": 0, "failed": 0}

        # Find all markdown files
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))

        # Filter out templates
        files = [f for f in files if "_template" not in f.stem]

        logger.info(f"Found {len(files)} files in {directory}")

        # Import with bounded concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def import_with_limit(file_path):
            async with semaphore:
                return await self.import_document(file_path, create_edges=False)

        # Phase 1: Import all documents (no edges yet)
        logger.info("Phase 1: Importing documents...")
        results = await asyncio.gather(
            *[import_with_limit(f) for f in files], return_exceptions=True
        )

        success_count = sum(1 for r in results if r and not isinstance(r, Exception))

        # Phase 2: Create edges (now all targets exist)
        logger.info("Phase 2: Creating graph edges...")
        edge_count = 0
        for file_path in files:
            try:
                content = file_path.read_text()
                doc_id = f"vault_memory:{slugify(file_path.stem)}"
                await self._create_edges_for_document(doc_id, content)
                edge_count += 1
            except Exception as e:
                logger.warning(f"Edge creation failed for {file_path}: {e}")

        return {
            "total": len(files),
            "success": success_count,
            "failed": len(files) - success_count,
            "edges_processed": edge_count,
        }

    async def import_all_vault(self) -> dict[str, Any]:
        """
        Import entire vault (decisions, patterns, experiments)

        Returns:
            Stats for each directory
        """
        results = {}

        for directory in ["decisions", "patterns", "experiments"]:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Importing {directory}...")
            logger.info(f"{'=' * 60}")

            stats = await self.import_directory(directory)
            results[directory] = stats

            logger.info(f"{directory}: {stats['success']}/{stats['total']} imported")

        return results


async def import_vault_to_graphrag(
    vault_path: Path,
    ollama_url: str = "http://localhost:11434",
    surrealdb_url: str = "http://localhost:8001",
) -> dict[str, Any]:
    """
    Convenience function for full vault import

    Usage:
        results = await import_vault_to_graphrag(Path("~/vaults/cohezion-vault"))
    """
    async with GraphRAGImporter(vault_path, ollama_url, surrealdb_url) as importer:
        return await importer.import_all_vault()
