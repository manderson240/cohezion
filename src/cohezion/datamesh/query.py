"""Datamesh query federation - unified query across all domains.

Charter: Parallel dispatch, result aggregation, full lineage.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import torch

from cohezion.datamesh.schema import (
    DataLineage,
    Embedding256D,
    Physics12D,
    RecordType,
    RelationType,
    UnifiedRecord,
)


logger = logging.getLogger(__name__)


@dataclass
class DatameshFilter:
    """Filter criteria for unified queries."""
    
    record_types: list[RecordType] = field(default_factory=list)
    relations: list[RelationType] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # "wiki", "flume", "surreal", "mirix"
    
    # Temporal
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    
    # Content
    content_contains: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    # Physics
    min_coherence: float = 0.0
    max_coherence: float = 1.0
    
    # Embedding
    embedding_similar_to: Optional[torch.Tensor] = None
    embedding_threshold: float = 0.7


@dataclass
class DatameshResult:
    """Result from federated query."""
    
    records: list[UnifiedRecord] = field(default_factory=list)
    total_found: int = 0
    sources_queried: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    lineage_map: dict[str, DataLineage] = field(default_factory=dict)
    
    # Performance
    query_time_ms: float = 0.0
    cache_hits: int = 0
    
    def by_type(self, record_type: RecordType) -> list[UnifiedRecord]:
        """Filter results by record type."""
        return [r for r in self.records if r.type == record_type]
    
    def by_source(self, source: str) -> list[UnifiedRecord]:
        """Filter results by origin."""
        return [r for r in self.records if r.lineage.origin == source]
    
    def trace_lineage(self, record_id: str, depth: int = 3) -> list[DataLineage]:
        """Trace data lineage for a record."""
        if record_id not in self.lineage_map:
            return []
        
        lineage = []
        current = self.lineage_map[record_id]
        lineage.append(current)
        
        # Trace upstream
        for parent_id in current.upstream[:depth]:
            if parent_id in self.lineage_map:
                lineage.append(self.lineage_map[parent_id])
        
        return lineage


class DatameshQuery:
    """Federated query across all datamesh sources.
    
    Parallel dispatch to:
    - Wiki (file-based, markdown)
    - FLUME (vector embeddings)
    - SurrealDB (graph + document)
    - MIRIX (6 memory agents)
    """
    
    def __init__(
        self,
        wiki=None,
        surreal_client=None,
        mirix_client=None,
        flume_bridge=None,
    ):
        self.wiki = wiki
        self.surreal = surreal_client
        self.mirix = mirix_client
        self.flume = flume_bridge
        
        # Metrics
        self._query_count = 0
        self._cache_hits = 0
    
    async def execute(
        self,
        filter: DatameshFilter,
        limit: int = 100,
        include_lineage: bool = True,
    ) -> DatameshResult:
        """Execute federated query across all sources.
        
        Strategy:
        1. Fan out to all relevant sources in parallel
        2. Collect and deduplicate results
        3. Enrich with lineage if requested
        4. Return unified result
        """
        import time
        start_time = time.perf_counter()
        
        result = DatameshResult()
        tasks = []
        
        # Determine which sources to query
        sources = filter.sources or ["wiki", "flume", "surreal", "mirix"]
        
        # Create async tasks for each source
        if "wiki" in sources and self.wiki:
            tasks.append(("wiki", self._query_wiki(filter, limit)))
        
        if "surreal" in sources and self.surreal:
            tasks.append(("surreal", self._query_surreal(filter, limit)))
        
        if "flume" in sources and self.flume:
            tasks.append(("flume", self._query_flume(filter, limit)))
        
        # Execute all queries in parallel
        if tasks:
            results = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True
            )
            
            for (source, _), records in zip(tasks, results):
                result.sources_queried.append(source)
                
                if isinstance(records, Exception):
                    logger.error(f"Query failed for {source}: {records}")
                    result.errors.append(f"{source}: {str(records)}")
                    continue
                
                result.records.extend(records)
        
        # Deduplicate by ID
        seen = set()
        unique = []
        for r in result.records:
            if str(r.id) not in seen:
                seen.add(str(r.id))
                unique.append(r)
        result.records = unique
        result.total_found = len(result.records)
        
        # Collect lineage
        if include_lineage:
            for r in result.records:
                result.lineage_map[str(r.id)] = r.lineage
        
        result.query_time_ms = (time.perf_counter() - start_time) * 1000
        
        return result
    
    async def _query_wiki(self, filter: DatameshFilter, limit: int) -> list[UnifiedRecord]:
        """Query wiki source."""
        if not self.wiki:
            return []
        
        records = []
        
        # Keyword search
        if filter.content_contains:
            pages = await self.wiki.query_pages(filter.content_contains, limit=limit)
            for page in pages:
                record = UnifiedRecord(
                    type=RecordType.WIKI_PAGE,
                    content=page.content,
                    metadata={
                        "title": page.title,
                        "category": page.category,
                        "tags": page.tags,
                        "path": str(page.path),
                    }
                )
                records.append(record)
        
        # Tag filter
        if filter.tags:
            # Search by tags
            for tag in filter.tags:
                pages = await self.wiki.query_pages(tag, limit=limit // len(filter.tags))
                for page in pages:
                    if tag in page.tags:
                        record = UnifiedRecord(
                            type=RecordType.WIKI_PAGE,
                            content=page.content,
                            metadata={
                                "title": page.title,
                                "category": page.category,
                                "tags": page.tags,
                            }
                        )
                        records.append(record)
        
        return records
    
    async def _query_surreal(self, filter: DatameshFilter, limit: int) -> list[UnifiedRecord]:
        """Query SurrealDB source."""
        if not self.surreal:
            return []
        
        records = []
        
        # Build SurrealQL query
        where_clauses = []
        if filter.content_contains:
            where_clauses.append(f"content CONTAINS '{filter.content_contains}'")
        if filter.record_types:
            types = " OR ".join([f"type = '{t.name}'" for t in filter.record_types])
            where_clauses.append(f"({types})")
        
        query = f"SELECT * FROM unified"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += f" LIMIT {limit}"
        
        try:
            results = await self.surreal.query(query)
            for row in results[0]["result"] if results else []:
                record = UnifiedRecord(
                    id=row.get("id"),
                    type=RecordType[row.get("type")],
                    content=row.get("content", ""),
                    metadata=row.get("metadata", {}),
                )
                records.append(record)
        except Exception as e:
            logger.error(f"SurrealDB query failed: {e}")
        
        return records
    
    async def _query_flume(self, filter: DatameshFilter, limit: int) -> list[UnifiedRecord]:
        """Query FLUME embeddings via similarity."""
        if not self.flume or not filter.embedding_similar_to:
            return []
        
        # Get similar pages
        similar = await self.flume.search_by_embedding(
            query=filter.content_contains or "",
            limit=limit
        )
        
        records = []
        for path, similarity in similar:
            if similarity < filter.embedding_threshold:
                continue
            
            page = self.flume.wiki._parse_page(path)
            record = UnifiedRecord(
                type=RecordType.EMBEDDING,
                content=page.content,
                metadata={
                    "title": page.title,
                    "similarity": similarity,
                    "path": str(path),
                }
            )
            records.append(record)
        
        return records
    
    async def semantic_search(
        self,
        query_text: str,
        limit: int = 10,
    ) -> DatameshResult:
        """Semantic search using FLUME embeddings.
        
        1. Embed query text
        2. Find similar records across all sources
        3. Return ranked results
        """
        if not self.flume:
            return DatameshResult(errors=["FLUME bridge not available"])
        
        # Embed query
        embedding = await self.flume.embedding_bridge.get_flume_input(query_text)
        
        filter = DatameshFilter(
            content_contains=query_text,
            embedding_similar_to=embedding,
            embedding_threshold=0.7,
        )
        
        return await self.execute(filter, limit=limit)
    
    async def traverse_graph(
        self,
        start_id: str,
        relation_types: list[RelationType],
        max_depth: int = 3,
    ) -> DatameshResult:
        """Graph traversal from starting record.
        
        Uses SurrealDB for efficient graph queries.
        """
        if not self.surreal:
            return DatameshResult(errors=["SurrealDB not available"])
        
        records = []
        visited = set()
        queue = [(start_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth >= max_depth:
                continue
            
            visited.add(current_id)
            
            # Query relations
            for rel in relation_types:
                query = f"SELECT * FROM {rel.name.lower()} WHERE out = {current_id}"
                try:
                    results = await self.surreal.query(query)
                    for row in results[0]["result"] if results else []:
                        record = UnifiedRecord(
                            id=row.get("in"),
                            type=RecordType.RELATED,
                            metadata={"relation": rel.name, "depth": depth},
                        )
                        records.append(record)
                        queue.append((row.get("in"), depth + 1))
                except Exception as e:
                    logger.error(f"Graph traverse failed: {e}")
        
        return DatameshResult(
            records=records,
            total_found=len(records),
            sources_queried=["surreal"],
        )
