"""Tests for SurrealUniverseRepository."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.core.persistence.repositories.surreal_universe_repository import (
    SurrealUniverseRepository,
)
from cohezion.core.persistence.repositories.universe_repository import (
    UniverseRepositoryFilter,
)
from cohezion.core.persistence.surreal_client import UniverseNode


@pytest.fixture
def mock_surreal_client():
    """Create a mock SurrealClient."""
    with patch("cohezion.core.persistence.surreal_client.SurrealClient") as mock_cls:
        instance = mock_cls.return_value
        instance.query = AsyncMock()
        yield instance


@pytest.fixture
def universe_repo(mock_surreal_client):
    """Create a SurrealUniverseRepository instance."""
    return SurrealUniverseRepository(mock_surreal_client)


@pytest.fixture
def sample_universe_node():
    """Create a sample universe node for testing."""
    return UniverseNode(
        id="test_node_1",
        content="Test node content",
        embedding=[0.1, 0.2, 0.3],
        node_type="document",
    )


class TestSurrealUniverseRepository:
    """Tests for SurrealUniverseRepository."""

    @pytest.mark.asyncio
    async def test_create_universe_node(
        self, universe_repo, mock_surreal_client, sample_universe_node
    ):
        """Test creating a universe node."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "universe_nodes:test_node_1",
                        "content": "Test node content",
                        "embedding": [0.1, 0.2, 0.3],
                        "node_type": "document",
                        "created_at": "2023-01-01T00:00:00",
                    }
                ]
            }
        ]

        # Execute
        result = await universe_repo.create(sample_universe_node)

        # Verify
        assert result == "test_node_1"
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "CREATE universe_nodes CONTENT" in call_args[0][0]
        assert call_args[0][1]["data"]["content"] == "Test node content"

    @pytest.mark.asyncio
    async def test_get_universe_node_found(
        self, universe_repo, mock_surreal_client, sample_universe_node
    ):
        """Test getting a universe node that exists."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "universe_nodes:test_node_1",
                        "content": "Test node content",
                        "embedding": [0.1, 0.2, 0.3],
                        "physics_state": {
                            "dim_1_x": 0.0,
                            "dim_2_y": 0.0,
                            "dim_3_z": 0.0,
                            "dim_4_time": 0.0,
                            "dim_5_physics": 0.0,
                            "dim_6_biology": 0.0,
                            "dim_7_logic": 0.0,
                            "dim_8_quantum": 0.0,
                            "dim_9_field": 0.0,
                            "dim_10_control": 0.0,
                            "dim_11_novelty": 0.0,
                            "dim_12_precipitation": 0.0,
                        },
                        "node_type": "document",
                        "created_at": "2023-01-01T00:00:00",
                        "metadata": {},
                        "compressed": False,
                        "packed_physics": "AAAAAAAAAAAAAAAAAAAAAA==",
                    }
                ]
            }
        ]

        # Execute
        result = await universe_repo.get("test_node_1")

        # Verify
        assert result is not None
        assert result.id == "test_node_1"
        assert result.content == "Test node content"
        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.node_type == "document"

    @pytest.mark.asyncio
    async def test_get_universe_node_not_found(self, universe_repo, mock_surreal_client):
        """Test getting a universe node that doesn't exist."""
        # Setup
        mock_surreal_client.query.return_value = [{"result": []}]

        # Execute
        result = await universe_repo.get("nonexistent_node")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_universe_nodes(self, universe_repo, mock_surreal_client):
        """Test getting all universe nodes."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "universe_nodes:node1",
                        "content": "First node",
                        "embedding": [0.1, 0.2, 0.3],
                        "physics_state": {
                            "dim_1_x": 0.0,
                            "dim_2_y": 0.0,
                            "dim_3_z": 0.0,
                            "dim_4_time": 0.0,
                            "dim_5_physics": 0.0,
                            "dim_6_biology": 0.0,
                            "dim_7_logic": 0.0,
                            "dim_8_quantum": 0.0,
                            "dim_9_field": 0.0,
                            "dim_10_control": 0.0,
                            "dim_11_novelty": 0.0,
                            "dim_12_precipitation": 0.0,
                        },
                        "node_type": "document",
                        "created_at": "2023-01-01T00:00:00",
                        "metadata": {},
                        "compressed": False,
                        "packed_physics": "AAAAAAAAAAAAAAAAAAAAAA==",
                    },
                    {
                        "id": "universe_nodes:node2",
                        "content": "Second node",
                        "embedding": [0.4, 0.5, 0.6],
                        "physics_state": {
                            "dim_1_x": 0.0,
                            "dim_2_y": 0.0,
                            "dim_3_z": 0.0,
                            "dim_4_time": 0.0,
                            "dim_5_physics": 0.0,
                            "dim_6_biology": 0.0,
                            "dim_7_logic": 0.0,
                            "dim_8_quantum": 0.0,
                            "dim_9_field": 0.0,
                            "dim_10_control": 0.0,
                            "dim_11_novelty": 0.0,
                            "dim_12_precipitation": 0.0,
                        },
                        "node_type": "energy_snapshot",
                        "created_at": "2023-01-02T00:00:00",
                        "metadata": {},
                        "compressed": False,
                        "packed_physics": "AAAAAAAAAAAAAAAAAAAAAA==",
                    },
                ]
            }
        ]

        # Execute
        from cohezion.core.persistence.repositories.universe_repository import (
            UniverseRepositoryFilter,
        )

        filter_params = UniverseRepositoryFilter(limit=10)
        result = await universe_repo.get_all(filter_params)

        # Verify
        assert len(result) == 2
        assert result[0].id == "node1"
        assert result[1].id == "node2"
        assert result[0].content == "First node"
        assert result[1].content == "Second node"
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        # Verify parameterized query (SQL injection prevention)
        assert "SELECT * FROM universe_nodes LIMIT $limit" in call_args[0][0]
        assert call_args[0][1]["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_all_universe_nodes_with_filter(self, universe_repo, mock_surreal_client):
        """Test getting all universe nodes with node_type filter."""
        # Setup
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "universe_nodes:node1",
                        "content": "Energy node",
                        "embedding": [0.1, 0.2, 0.3],
                        "physics_state": {
                            "dim_1_x": 0.0,
                            "dim_2_y": 0.0,
                            "dim_3_z": 0.0,
                            "dim_4_time": 0.0,
                            "dim_5_physics": 0.0,
                            "dim_6_biology": 0.0,
                            "dim_7_logic": 0.0,
                            "dim_8_quantum": 0.0,
                            "dim_9_field": 0.0,
                            "dim_10_control": 0.0,
                            "dim_11_novelty": 0.0,
                            "dim_12_precipitation": 0.0,
                        },
                        "node_type": "energy_snapshot",
                        "created_at": "2023-01-01T00:00:00",
                        "metadata": {},
                        "compressed": False,
                        "packed_physics": "AAAAAAAAAAAAAAAAAAAAAA==",
                    }
                ]
            }
        ]

        # Execute
        filter_params = UniverseRepositoryFilter(node_type="energy_snapshot", limit=10)
        result = await universe_repo.get_all(filter_params)

        # Verify
        assert len(result) == 1
        assert result[0].id == "node1"
        assert result[0].node_type == "energy_snapshot"
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        # Verify parameterized query with filter
        assert (
            "SELECT * FROM universe_nodes WHERE node_type = $node_type LIMIT $limit"
            in call_args[0][0]
        )
        assert call_args[0][1]["node_type"] == "energy_snapshot"
        assert call_args[0][1]["limit"] == 10

    @pytest.mark.asyncio
    async def test_update_universe_node(
        self, universe_repo, mock_surreal_client, sample_universe_node
    ):
        """Test updating a universe node."""
        # Setup
        updated_node = UniverseNode(
            id="test_node_1",
            content="Updated test node content",
            embedding=[0.4, 0.5, 0.6],
            node_type="energy_snapshot",
        )

        # Execute
        result = await universe_repo.update(updated_node)

        # Verify
        assert result is True
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "UPDATE universe_nodes:" in call_args[0][0]
        assert "MERGE" in call_args[0][0]
        assert call_args[0][1]["data"]["content"] == "Updated test node content"
        assert call_args[0][1]["data"]["node_type"] == "energy_snapshot"

    @pytest.mark.asyncio
    async def test_delete_universe_node(self, universe_repo, mock_surreal_client):
        """Test deleting a universe node."""
        # Execute
        result = await universe_repo.delete("test_node_1")

        # Verify
        assert result is True
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        assert "DELETE universe_nodes:test_node_1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_search_by_embedding(
        self, universe_repo, mock_surreal_client, sample_universe_node
    ):
        """Test searching for nodes by embedding similarity."""
        # Setup
        query_embedding = [0.1, 0.2, 0.3]
        mock_surreal_client.query.return_value = [
            {
                "result": [
                    {
                        "id": "universe_nodes:test_node_1",
                        "content": "Test node content",
                        "embedding": [0.1, 0.2, 0.3],
                        "physics_state": {
                            "dim_1_x": 0.0,
                            "dim_2_y": 0.0,
                            "dim_3_z": 0.0,
                            "dim_4_time": 0.0,
                            "dim_5_physics": 0.0,
                            "dim_6_biology": 0.0,
                            "dim_7_logic": 0.0,
                            "dim_8_quantum": 0.0,
                            "dim_9_field": 0.0,
                            "dim_10_control": 0.0,
                            "dim_11_novelty": 0.0,
                            "dim_12_precipitation": 0.0,
                        },
                        "node_type": "document",
                        "created_at": "2023-01-01T00:00:00",
                        "metadata": {},
                        "compressed": False,
                        "packed_physics": "AAAAAAAAAAAAAAAAAAAAAA==",
                        "score": 1.0,  # Perfect match
                    }
                ]
            }
        ]

        # Execute
        result = await universe_repo.search_by_embedding(query_embedding, limit=5)

        # Verify
        assert len(result) == 1
        assert result[0].id == "test_node_1"
        assert result[0].content == "Test node content"
        assert result[0].embedding == [0.1, 0.2, 0.3]
        mock_surreal_client.query.assert_called_once()
        call_args = mock_surreal_client.query.call_args
        # Verify vector similarity query with parameterized variables
        assert (
            "SELECT *, vector::similarity::cosine(embedding, $embedding) AS score"
            in call_args[0][0]
        )
        assert call_args[0][1]["table"] == "universe_nodes"
        assert call_args[0][1]["embedding"] == [0.1, 0.2, 0.3]
        assert call_args[0][1]["limit"] == 5
