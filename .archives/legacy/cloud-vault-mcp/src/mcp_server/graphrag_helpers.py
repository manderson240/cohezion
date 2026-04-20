"""
GraphRAG helper functions for safe graph operations

Handles edge cases:
- Non-existent document references
- Circular reference detection
- Retry logic for transient failures
- Bounded traversal
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class GraphRAGError(Exception):
    """Base exception for GraphRAG operations"""

    pass


class CircularReferenceError(GraphRAGError):
    """Raised when circular reference detected"""

    pass


def slugify(text: str) -> str:
    """Convert text to valid SurrealDB ID"""
    # Remove special chars (keep hyphens), lowercase, replace spaces/hyphens with underscores
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")


def escape_sql(text: str) -> str:
    """Escape text for safe SQL insertion"""
    # Escape single quotes and backslashes
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    # Truncate to reasonable length
    return text[:2000]


async def execute_surreal_async(
    query: str,
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
    auth: tuple = ("root", "root"),
    max_retries: int = 3,
    url: str = "http://localhost:8001/sql",
) -> list[dict[str, Any]]:
    """Execute SurrealQL query with retry logic"""

    # Prepend USE statement
    full_query = f"USE NS {namespace} DB {database};\n{query}"

    for attempt in range(max_retries):
        try:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "text/plain",
                    "Accept": "application/json",
                },
                auth=auth,
                content=full_query,
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json()

            # Skip USE statement result, return actual query results
            return results[1:] if len(results) > 1 else results

        except httpx.HTTPStatusError as e:
            # Log response body for debugging
            error_detail = getattr(e.response, "text", str(e))
            logger.error(f"SurrealDB HTTP {e.response.status_code}: {error_detail}")
            if attempt == max_retries - 1:
                raise GraphRAGError(
                    f"Query failed after {max_retries} attempts: {error_detail}"
                )
            await asyncio.sleep(2**attempt)  # Exponential backoff
        except httpx.HTTPError as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"SurrealDB query failed after {max_retries} attempts: {e}"
                )
                raise GraphRAGError(f"Query failed: {e}")

            # Exponential backoff
            await asyncio.sleep(0.1 * (2**attempt))
            logger.warning(f"Retry {attempt + 1}/{max_retries} for query")

    raise GraphRAGError("Max retries exceeded")


async def check_document_exists(
    doc_id: str,
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
) -> bool:
    """Check if document exists in vault_memory"""
    try:
        query = f"SELECT id FROM {doc_id} LIMIT 1;"
        results = await execute_surreal_async(query, client, namespace, database)

        if results and results[0].get("status") == "OK":
            result = results[0].get("result", [])
            return len(result) > 0

        return False
    except Exception as e:
        logger.warning(f"Existence check failed for {doc_id}: {e}")
        return False


async def safe_create_edge(
    source_id: str,
    edge_type: str,
    target_id: str,
    metadata: dict[str, Any] | None,
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
    skip_missing: bool = True,
) -> str | None:
    """
    Create graph edge with existence checks

    Args:
        source_id: Source document ID
        edge_type: Edge type (informed_by, led_to, used_in, extracted_from)
        target_id: Target document ID
        metadata: Additional edge metadata
        client: Async HTTP client
        namespace: SurrealDB namespace
        database: SurrealDB database
        skip_missing: If True, skip edge if target missing; if False, create placeholder

    Returns:
        Edge ID if created, None if skipped
    """
    # Check if target exists
    target_exists = await check_document_exists(target_id, client, namespace, database)

    if not target_exists:
        if skip_missing:
            logger.info(f"Target {target_id} doesn't exist, skipping edge")
            return None
        else:
            # Create placeholder node
            logger.info(f"Creating placeholder for {target_id}")
            placeholder_query = f"""
            CREATE {target_id} SET
                type = 'placeholder',
                title = 'Referenced Document (Not Yet Created)',
                path = 'pending',
                created_at = time::now();
            """
            await execute_surreal_async(placeholder_query, client, namespace, database)

    # Build metadata SET clause
    metadata_clause = ""
    if metadata:
        metadata_items = [f"{k} = '{v}'" for k, v in metadata.items()]
        metadata_clause = f"SET {', '.join(metadata_items)}, created_at = time::now()"
    else:
        metadata_clause = "SET created_at = time::now()"

    # Create edge
    edge_query = f"""
    RELATE {source_id}->{edge_type}->{target_id}
    {metadata_clause};
    """

    try:
        results = await execute_surreal_async(edge_query, client, namespace, database)
        if results and results[0].get("status") == "OK":
            edge_id = results[0]["result"][0]["id"]
            logger.info(f"Created edge: {source_id}->{edge_type}->{target_id}")
            return edge_id
        else:
            logger.error(f"Edge creation failed: {results}")
            return None
    except Exception as e:
        logger.error(f"Failed to create edge: {e}")
        return None


async def detect_circular_reference(
    source_id: str,
    target_id: str,
    edge_type: str,
    client: httpx.AsyncClient,
    max_depth: int = 5,
    namespace: str = "cohezion",
    database: str = "vault",
) -> bool:
    """
    Detect if creating edge would cause circular reference

    Returns:
        True if circular reference detected, False if safe
    """
    # Query: Does target already connect back to source?
    query = f"""
    SELECT id FROM {target_id}
    WHERE id IN (
        SELECT out FROM (
            SELECT ->{edge_type}[..{max_depth}]->vault_memory.id AS out
            FROM {source_id}
        )
    );
    """

    try:
        results = await execute_surreal_async(query, client, namespace, database)
        if results and results[0].get("status") == "OK":
            result = results[0].get("result", [])
            return len(result) > 0
        return False
    except Exception as e:
        logger.warning(f"Circular reference check failed: {e}")
        return False  # Assume safe on error


async def batch_create_edges(
    edges: list[dict[str, str]],
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
    max_concurrent: int = 10,
) -> int:
    """
    Create multiple edges in parallel with bounded concurrency

    Args:
        edges: List of {"source": "id", "type": "edge_type", "target": "id", "metadata": {...}}
        client: Async HTTP client
        namespace: SurrealDB namespace
        database: SurrealDB database
        max_concurrent: Max parallel operations

    Returns:
        Count of successfully created edges
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def create_with_limit(edge_data):
        async with semaphore:
            return await safe_create_edge(
                source_id=edge_data["source"],
                edge_type=edge_data["type"],
                target_id=edge_data["target"],
                metadata=edge_data.get("metadata"),
                client=client,
                namespace=namespace,
                database=database,
            )

    # Execute all edge creations in parallel with limit
    tasks = [create_with_limit(edge) for edge in edges]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Count successes (non-None, non-exception)
    success_count = sum(1 for r in results if r and not isinstance(r, Exception))
    logger.info(f"Created {success_count}/{len(edges)} edges")

    return success_count


def parse_wiki_links(content: str) -> list[str]:
    """Extract wiki-style links from markdown content"""
    # Pattern: [[link-text]] or [[link-text|display-text]]
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    matches = re.findall(pattern, content)
    return [match.strip() for match in matches]


def detect_document_type(file_path: Path, vault_path: Path) -> str:
    """Detect document type from file path"""
    rel_path = file_path.relative_to(vault_path)

    if rel_path.parts[0] == "decisions":
        return "decision"
    elif rel_path.parts[0] == "patterns":
        return "pattern"
    elif rel_path.parts[0] == "experiments":
        return "experiment"
    else:
        return "document"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown"""
    if not content.startswith("---"):
        return {}, content

    try:
        # Split on closing ---
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        import yaml

        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()

        return frontmatter or {}, body
    except Exception as e:
        logger.warning(f"Frontmatter parsing failed: {e}")
        return {}, content
