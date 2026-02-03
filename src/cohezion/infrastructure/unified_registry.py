"""
Unified registry for COHEZION agents and capabilities with vector search.

Provides a centralized system for agent registration, capability management,
and discovery across the distributed agent ecosystem with FAISS vector search.
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import umap
from sklearn.neighbors import NearestNeighbors

# Try to import FAISS, fallback to scikit-learn if unavailable
try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("FAISS not available, falling back to scikit-learn for vector search")

from ..swarm.agents.base import Agent
from ..infrastructure.cache_manager import CacheManager
from ..infrastructure.connection_pool import ConnectionPool


class RegistryOperation(Enum):
    """Types of registry operations."""

    REGISTER = "register"
    UNREGISTER = "unregister"
    UPDATE = "update"
    QUERY = "query"


@dataclass
class RegistryConfig:
    """Configuration for the unified registry."""

    cache_ttl: int = 300  # 5 minutes
    max_concurrent_queries: int = 100
    persistence_enabled: bool = True
    backup_interval_minutes: int = 60
    max_registry_size: int = 10000
    vector_search_enabled: bool = True
    vector_dimension: int = 128
    faiss_index_type: str = "Flat"
    umap_neighbors: int = 15
    umap_min_dist: float = 0.1
    umap_n_components: int = 2


@dataclass
class RegistryEntry:
    """Entry in the unified registry."""

    agent_id: str
    agent_name: str
    capabilities: Dict[str, Any]
    resource_profile: Dict[str, Any]
    last_seen: datetime
    node_id: str
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[np.ndarray] = None
    vector: Optional[np.ndarray] = None


@dataclass
class RegistryStats:
    """Statistics about the registry."""

    total_entries: int
    active_entries: int
    capability_distribution: Dict[str, int]
    resource_summary: Dict[str, Any]
    avg_agent_age_minutes: float
    vector_index_size: int
    avg_vector_similarity: float


@dataclass
class VectorSearchResult:
    """Result of a vector search query."""

    agent_id: str
    agent_name: str
    similarity: float
    capabilities: Dict[str, Any]
    resource_profile: Dict[str, Any]


class VectorSearchIndex:
    """Vector search index for agent embeddings."""

    def __init__(self, config: RegistryConfig):
        self.config = config
        self.index = None
        self.agent_ids = []
        self.embeddings = []
        self.umap_model = None
        self._init_index()

    def _init_index(self):
        """Initialize the vector search index."""
        if FAISS_AVAILABLE and self.config.vector_search_enabled:
            # Create FAISS index
            if self.config.faiss_index_type == "Flat":
                self.index = faiss.IndexFlatL2(self.config.vector_dimension)
            elif self.config.faiss_index_type == "IVFFlat":
                quantizer = faiss.IndexFlatL2(self.config.vector_dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer, self.config.vector_dimension, 100
                )
                self.index.train(
                    np.random.random((1000, self.config.vector_dimension)).astype(
                        "float32"
                    )
                )
            else:
                self.index = faiss.IndexFlatL2(self.config.vector_dimension)
        else:
            # Fallback to scikit-learn NearestNeighbors
            self.index = NearestNeighbors(
                n_neighbors=10, algorithm="brute", metric="euclidean"
            )

    def add_vectors(self, embeddings: np.ndarray, agent_ids: List[str]):
        """Add vectors to the index."""
        if len(embeddings) == 0:
            return

        # Store embeddings and agent IDs
        self.embeddings.extend(embeddings)
        self.agent_ids.extend(agent_ids)

        # Update FAISS index
        if FAISS_AVAILABLE and self.config.vector_search_enabled:
            embeddings_float32 = np.array(embeddings, dtype=np.float32)
            self.index.add(embeddings_float32)
        else:
            # Update scikit-learn index
            if len(self.embeddings) > 1:
                self.index.fit(self.embeddings)

    def search(
        self, query_vector: np.ndarray, k: int = 10, return_similarity: bool = True
    ) -> List[VectorSearchResult]:
        """Search for similar agents."""
        if len(self.agent_ids) == 0:
            return []

        results = []

        if FAISS_AVAILABLE and self.config.vector_search_enabled:
            # Use FAISS for fast approximate search
            query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
            distances, indices = self.index.search(query_vector, k)

            for i, idx in enumerate(indices[0]):
                if idx < len(self.agent_ids):
                    agent_id = self.agent_ids[idx]
                    similarity = 1.0 - (
                        distances[0][i] / np.sqrt(self.config.vector_dimension)
                    )
                    results.append(
                        VectorSearchResult(
                            agent_id=agent_id,
                            agent_name="unknown",
                            similarity=similarity,
                            capabilities={},
                            resource_profile={},
                        )
                    )
        else:
            # Fallback to scikit-learn exact search
            if len(self.embeddings) > 0:
                distances, indices = self.index.kneighbors(
                    [query_vector],
                    n_neighbors=min(k, len(self.embeddings)),
                    return_distance=True,
                )

                for i, idx in enumerate(indices[0]):
                    if idx < len(self.agent_ids):
                        agent_id = self.agent_ids[idx]
                        similarity = 1.0 - (
                            distances[0][i] / np.sqrt(self.config.vector_dimension)
                        )
                        results.append(
                            VectorSearchResult(
                                agent_id=agent_id,
                                agent_name="unknown",
                                similarity=similarity,
                                capabilities={},
                                resource_profile={},
                            )
                        )

        return results

    def get_umap_projection(self) -> Tuple[np.ndarray, List[str]]:
        """Get UMAP 2D projection of the vector space."""
        if self.umap_model is None and len(self.embeddings) > 0:
            # Train UMAP model
            self.umap_model = umap.UMAP(
                n_neighbors=self.config.umap_neighbors,
                min_dist=self.config.umap_min_dist,
                n_components=self.config.umap_n_components,
                random_state=42,
            )

            # Convert embeddings to float64 for UMAP
            embeddings_float64 = np.array(self.embeddings, dtype=np.float64)
            self.umap_projection = self.umap_model.fit_transform(embeddings_float64)

        if hasattr(self, "umap_projection"):
            return self.umap_projection, self.agent_ids

        return np.zeros((0, 2)), []

    def get_similarities_matrix(self) -> Optional[np.ndarray]:
        """Get similarity matrix between all agents."""
        if len(self.embeddings) == 0:
            return None

        # Calculate pairwise cosine similarities
        embeddings = np.array(self.embeddings)
        norms = np.linalg.norm(embeddings, axis=1)
        norms[norms == 0] = 1e-10  # Avoid division by zero
        normalized = embeddings / norms[:, np.newaxis]

        similarity_matrix = np.dot(normalized, normalized.T)
        return similarity_matrix


class UnifiedRegistry:
    """Unified registry for agent discovery and capability management with vector search."""

    def __init__(self, config: Optional[RegistryConfig] = None):
        self.config = config or RegistryConfig()
        self.cache_manager = CacheManager()
        self.connection_pool = ConnectionPool()
        self.registry: Dict[str, RegistryEntry] = {}
        self.capability_index: Dict[str, Set[str]] = {}
        self.node_registry: Dict[str, Set[str]] = {}
        self.vector_index = VectorSearchIndex(self.config)
        self._init_registry()

    def _init_registry(self):
        """Initialize the registry from cache or create new."""
        # Try to load from cache
        cached_registry = self.cache_manager.get("unified_registry")
        if cached_registry:
            self.registry = {k: RegistryEntry(**v) for k, v in cached_registry.items()}
            print(f"Loaded {len(self.registry)} entries from cache")
            # Rebuild vector index
            self._rebuild_vector_index()
        else:
            print("Initialized new registry")

        # Rebuild indices
        self._rebuild_indices()

    def _rebuild_vector_index(self):
        """Rebuild vector search index from registry data."""
        if self.config.vector_search_enabled:
            embeddings = []
            agent_ids = []

            for entry in self.registry.values():
                if entry.vector is not None:
                    embeddings.append(entry.vector)
                    agent_ids.append(entry.agent_id)

            if embeddings:
                self.vector_index.add_vectors(embeddings, agent_ids)

    def _rebuild_indices(self):
        """Rebuild search indices from registry data."""
        self.capability_index = {}
        self.node_registry = {}

        for entry in self.registry.values():
            # Build capability index
            for capability in entry.capabilities.keys():
                if capability not in self.capability_index:
                    self.capability_index[capability] = set()
                self.capability_index[capability].add(entry.agent_id)

            # Build node index
            if entry.node_id not in self.node_registry:
                self.node_registry[entry.node_id] = set()
            self.node_registry[entry.node_id].add(entry.agent_id)

    async def register_agent(self, agent: Agent) -> str:
        """
        Register an agent with the unified registry.

        Returns the agent ID.
        """
        agent_id = agent.id

        # Create registry entry
        entry = RegistryEntry(
            agent_id=agent_id,
            agent_name=agent.name,
            capabilities=agent.get_capabilities(),
            resource_profile=agent.get_resource_profile(),
            last_seen=datetime.now(),
            node_id=agent.node_id,
            version=agent.version,
            metadata=agent.get_metadata(),
            embeddings=agent.get_embeddings()
            if hasattr(agent, "get_embeddings")
            else None,
            vector=agent.get_vector() if hasattr(agent, "get_vector") else None,
        )

        # Add to registry
        self.registry[agent_id] = entry

        # Update indices
        self._update_indices(entry)

        # Update vector index
        if entry.vector is not None and self.config.vector_search_enabled:
            self.vector_index.add_vectors([entry.vector], [agent_id])

        # Cache the registry
        self._cache_registry()

        # Notify connection pool
        await self.connection_pool.register_agent(
            agent_id,
            {
                "registry_registered": True,
                "capabilities": entry.capabilities,
                "resource_profile": entry.resource_profile,
            },
        )

        return agent_id

    def _update_indices(self, entry: RegistryEntry):
        """Update search indices for a registry entry."""
        # Update capability index
        for capability in entry.capabilities.keys():
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(entry.agent_id)

        # Update node index
        if entry.node_id not in self.node_registry:
            self.node_registry[entry.node_id] = set()
        self.node_registry[entry.node_id].add(entry.agent_id)

    def _cache_registry(self):
        """Cache the registry state."""
        registry_data = {
            agent_id: {
                k: v if k != "last_seen" else v.isoformat()
                for k, v in entry.__dict__.items()
            }
            for agent_id, entry in self.registry.items()
        }
        self.cache_manager.set(
            "unified_registry", registry_data, ttl=self.config.cache_ttl
        )

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry."""
        if agent_id in self.registry:
            # Remove from registry
            del self.registry[agent_id]

            # Update indices
            self._remove_from_indices(agent_id)

            # Update vector index
            if self.config.vector_search_enabled:
                self.vector_index.agent_ids = [
                    aid for aid in self.vector_index.agent_ids if aid != agent_id
                ]
                # Rebuild vector index (simplified for now)
                self._rebuild_vector_index()

            # Cache updated registry
            self._cache_registry()

            # Notify connection pool
            await self.connection_pool.unregister_agent(agent_id)

            return True

        return False

    def _remove_from_indices(self, agent_id: str):
        """Remove agent from search indices."""
        if agent_id in self.registry:
            entry = self.registry[agent_id]

            # Remove from capability index
            for capability in entry.capabilities.keys():
                if capability in self.capability_index:
                    self.capability_index[capability].discard(agent_id)
                    if not self.capability_index[capability]:
                        del self.capability_index[capability]

            # Remove from node index
            if entry.node_id in self.node_registry:
                self.node_registry[entry.node_id].discard(agent_id)
                if not self.node_registry[entry.node_id]:
                    del self.node_registry[entry.node_id]

    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Update an agent's registry information."""
        if agent_id in self.registry:
            entry = self.registry[agent_id]

            # Update fields
            if "capabilities" in updates:
                # Rebuild capability index if capabilities changed
                old_capabilities = set(entry.capabilities.keys())
                new_capabilities = set(updates["capabilities"].keys())

                # Remove old capabilities
                for capability in old_capabilities - new_capabilities:
                    if capability in self.capability_index:
                        self.capability_index[capability].discard(agent_id)
                        if not self.capability_index[capability]:
                            del self.capability_index[capability]

                # Add new capabilities
                for capability in new_capabilities - old_capabilities:
                    if capability not in self.capability_index:
                        self.capability_index[capability] = set()
                    self.capability_index[capability].add(agent_id)

            # Update entry fields
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)

            entry.last_seen = datetime.now()

            # Cache updated registry
            self._cache_registry()

            return True

        return False

    def get_agent(self, agent_id: str) -> Optional[RegistryEntry]:
        """Get registry entry for an agent."""
        return self.registry.get(agent_id)

    def find_agents_by_capability(
        self, capability: str, min_score: float = 0.0
    ) -> List[RegistryEntry]:
        """Find agents by capability with optional score filtering."""
        agent_ids = self.capability_index.get(capability, set())

        results = []
        for agent_id in agent_ids:
            entry = self.registry.get(agent_id)
            if entry:
                # Check if capability score meets threshold
                capability_score = entry.capabilities.get(capability, {}).get(
                    "score", 0.0
                )
                if capability_score >= min_score:
                    results.append(entry)

        # Sort by capability score (descending)
        results.sort(
            key=lambda e: e.capabilities.get(capability, {}).get("score", 0.0),
            reverse=True,
        )
        return results

    def find_agents_by_node(self, node_id: str) -> List[RegistryEntry]:
        """Find all agents on a specific node."""
        agent_ids = self.node_registry.get(node_id, set())
        return [
            self.registry[agent_id]
            for agent_id in agent_ids
            if agent_id in self.registry
        ]

    def search_agents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 50,
    ) -> List[RegistryEntry]:
        """
        Search for agents using natural language query.

        Supports filtering by capabilities, resources, and other attributes.
        """
        # Simple keyword-based search for now
        query_lower = query.lower()

        results = []
        for entry in self.registry.values():
            # Check if query matches agent name or capabilities
            if query_lower in entry.agent_name.lower() or any(
                query_lower in cap_name.lower()
                for cap_name in entry.capabilities.keys()
            ):
                results.append(entry)

        # Apply filters
        if filters:
            results = self._apply_filters(results, filters)

        # Sort by relevance (simple: name match > capability match)
        results.sort(
            key=lambda e: (
                query_lower in e.agent_name.lower(),
                any(
                    query_lower in cap_name.lower()
                    for cap_name in e.capabilities.keys()
                ),
            ),
            reverse=True,
        )

        return results[:max_results]

    def _apply_filters(
        self, entries: List[RegistryEntry], filters: Dict[str, Any]
    ) -> List[RegistryEntry]:
        """Apply filters to search results."""
        filtered = entries

        for key, value in filters.items():
            if key == "capability":
                filtered = [e for e in filtered if value in e.capabilities]
            elif key == "min_score":
                filtered = [
                    e
                    for e in filtered
                    if any(
                        cap.get("score", 0) >= value for cap in e.capabilities.values()
                    )
                ]
            elif key == "node_id":
                filtered = [e for e in filtered if e.node_id == value]
            elif key == "resource":
                # Filter by resource requirements
                filtered = [
                    e
                    for e in filtered
                    if all(e.resource_profile.get(k, 0) >= v for k, v in value.items())
                ]

        return filtered

    def vector_search(
        self, query_vector: np.ndarray, k: int = 10, min_similarity: float = 0.5
    ) -> List[VectorSearchResult]:
        """Perform vector similarity search."""
        if not self.config.vector_search_enabled:
            return []

        # Get vector search results
        results = self.vector_index.search(query_vector, k=k)

        # Filter by minimum similarity
        results = [r for r in results if r.similarity >= min_similarity]

        # Add agent details
        final_results = []
        for result in results:
            entry = self.registry.get(result.agent_id)
            if entry:
                final_results.append(
                    VectorSearchResult(
                        agent_id=entry.agent_id,
                        agent_name=entry.agent_name,
                        similarity=result.similarity,
                        capabilities=entry.capabilities,
                        resource_profile=entry.resource_profile,
                    )
                )

        return final_results

    def get_registry_stats(self) -> RegistryStats:
        """Get statistics about the registry."""
        if not self.registry:
            return RegistryStats(
                total_entries=0,
                active_entries=0,
                capability_distribution={},
                resource_summary={},
                avg_agent_age_minutes=0.0,
                vector_index_size=0,
                avg_vector_similarity=0.0,
            )

        total_entries = len(self.registry)
        active_entries = sum(
            1
            for e in self.registry.values()
            if (datetime.now() - e.last_seen).total_seconds() < 300
        )

        # Calculate capability distribution
        capability_distribution = {}
        for entry in self.registry.values():
            for capability in entry.capabilities.keys():
                capability_distribution[capability] = (
                    capability_distribution.get(capability, 0) + 1
                )

        # Calculate resource summary
        resource_summary = {
            "total_memory_mb": sum(
                e.resource_profile.get("memory_mb", 0) for e in self.registry.values()
            ),
            "total_cpu_cores": sum(
                e.resource_profile.get("cpu_cores", 0) for e in self.registry.values()
            ),
            "avg_memory_per_agent_mb": sum(
                e.resource_profile.get("memory_mb", 0) for e in self.registry.values()
            )
            / total_entries,
            "avg_cpu_per_agent": sum(
                e.resource_profile.get("cpu_cores", 0) for e in self.registry.values()
            )
            / total_entries,
        }

        # Calculate average agent age
        current_time = datetime.now()
        agent_ages = [
            (current_time - e.last_seen).total_seconds() / 60.0
            for e in self.registry.values()
        ]
        avg_agent_age_minutes = np.mean(agent_ages) if agent_ages else 0.0

        # Calculate vector index stats
        vector_index_size = len(self.vector_index.agent_ids)

        # Calculate average vector similarity
        similarity_matrix = self.vector_index.get_similarities_matrix()
        if similarity_matrix is not None:
            avg_vector_similarity = np.mean(similarity_matrix)
        else:
            avg_vector_similarity = 0.0

        return RegistryStats(
            total_entries=total_entries,
            active_entries=active_entries,
            capability_distribution=capability_distribution,
            resource_summary=resource_summary,
            avg_agent_age_minutes=avg_agent_age_minutes,
            vector_index_size=vector_index_size,
            avg_vector_similarity=avg_vector_similarity,
        )

    async def cleanup_registry(self) -> int:
        """Remove stale entries from registry."""
        current_time = datetime.now()
        stale_threshold = timedelta(minutes=30)

        stale_entries = []
        for agent_id, entry in self.registry.items():
            if current_time - entry.last_seen > stale_threshold:
                stale_entries.append(agent_id)

        for agent_id in stale_entries:
            await self.unregister_agent(agent_id)

        return len(stale_entries)

    def get_embeddings_matrix(self) -> Optional[np.ndarray]:
        """Get matrix of all agent embeddings for vector search."""
        embeddings = []
        agent_ids = []

        for agent_id, entry in self.registry.items():
            if entry.embeddings is not None:
                embeddings.append(entry.embeddings)
                agent_ids.append(agent_id)

        if embeddings:
            return np.array(embeddings), agent_ids
        return None, []

    def get_umap_projection(self) -> Tuple[np.ndarray, List[str]]:
        """Get UMAP 2D projection of the agent capability space."""
        return self.vector_index.get_umap_projection()


# Global registry instance
REGISTRY = UnifiedRegistry()


def get_registry() -> UnifiedRegistry:
    """Get the global unified registry."""
    return REGISTRY
