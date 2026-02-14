"""Tests for entire.io HTTP client."""

import pytest
import httpx
from unittest.mock import patch, Mock, AsyncMock
from src.mcp_server.entire_ops import (
    EntireOpsClient,
    Checkpoint,
    LineageNode,
    EntireOpsError,
    get_entire_ops,
    reset_entire_ops
)


class TestEntireOpsClient:
    """Test EntireOpsClient HTTP operations."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        reset_entire_ops()
        yield
        reset_entire_ops()

    @pytest.mark.asyncio
    async def test_create_checkpoint_success(self):
        """Test successful checkpoint creation."""
        client = EntireOpsClient(api_url="https://test.entire.io/v1")

        mock_response = {
            "id": "cp_123",
            "commit_hash": "abc123",
            "message": "Test commit",
            "timestamp": "2026-02-13T00:00:00Z",
            "author": "test_author",
            "files_changed": 5,
            "lines_added": 100,
            "lines_deleted": 50,
            "metadata": {}
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.post.return_value.json.return_value = mock_response
            mock_client.post.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            checkpoint = await client.create_checkpoint(
                commit_hash="abc123",
                message="Test commit",
                author="test_author",
                files_changed=5,
                lines_added=100,
                lines_deleted=50
            )

            assert checkpoint.id == "cp_123"
            assert checkpoint.commit_hash == "abc123"
            assert checkpoint.message == "Test commit"
            assert checkpoint.files_changed == 5

    @pytest.mark.asyncio
    async def test_create_checkpoint_http_error(self):
        """Test checkpoint creation with HTTP error."""
        client = EntireOpsClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=Mock(), response=Mock()
            )
            mock_get_client.return_value = mock_client

            with pytest.raises(EntireOpsError, match="Failed to create checkpoint"):
                await client.create_checkpoint(
                    commit_hash="abc",
                    message="test",
                    author="author",
                    files_changed=1,
                    lines_added=10,
                    lines_deleted=5
                )

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(self):
        """Test retrieving existing checkpoint."""
        client = EntireOpsClient()

        mock_response = {
            "id": "cp_456",
            "commit_hash": "def456",
            "message": "Existing commit",
            "timestamp": "2026-02-13T01:00:00Z",
            "author": "test_author",
            "files_changed": 3,
            "lines_added": 50,
            "lines_deleted": 25,
            "metadata": {"branch": "main"}
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.status_code = 200
            mock_client.get.return_value.json.return_value = mock_response
            mock_client.get.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            checkpoint = await client.get_checkpoint("cp_456")

            assert checkpoint is not None
            assert checkpoint.id == "cp_456"
            assert checkpoint.metadata["branch"] == "main"

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(self):
        """Test retrieving non-existent checkpoint returns None."""
        client = EntireOpsClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.status_code = 404
            mock_get_client.return_value = mock_client

            checkpoint = await client.get_checkpoint("nonexistent")

            assert checkpoint is None

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_pagination(self):
        """Test listing checkpoints with pagination."""
        client = EntireOpsClient()

        mock_response = {
            "checkpoints": [
                {
                    "id": "cp_1",
                    "commit_hash": "aaa111",
                    "message": "Commit 1",
                    "timestamp": "2026-02-13T00:00:00Z",
                    "author": "author1",
                    "files_changed": 2,
                    "lines_added": 20,
                    "lines_deleted": 10,
                    "metadata": {}
                },
                {
                    "id": "cp_2",
                    "commit_hash": "bbb222",
                    "message": "Commit 2",
                    "timestamp": "2026-02-13T01:00:00Z",
                    "author": "author2",
                    "files_changed": 3,
                    "lines_added": 30,
                    "lines_deleted": 15,
                    "metadata": {}
                }
            ]
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.json.return_value = mock_response
            mock_client.get.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            checkpoints = await client.list_checkpoints(limit=2, offset=0)

            assert len(checkpoints) == 2
            assert checkpoints[0].id == "cp_1"
            assert checkpoints[1].id == "cp_2"

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_since_filter(self):
        """Test listing checkpoints with since timestamp."""
        client = EntireOpsClient()

        mock_response = {"checkpoints": []}

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.json.return_value = mock_response
            mock_client.get.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            checkpoints = await client.list_checkpoints(
                since="2026-02-13T00:00:00Z"
            )

            assert len(checkpoints) == 0
            # Verify since parameter was passed
            call_args = mock_client.get.call_args
            assert call_args[1]["params"]["since"] == "2026-02-13T00:00:00Z"

    @pytest.mark.asyncio
    async def test_get_lineage(self):
        """Test retrieving checkpoint lineage."""
        client = EntireOpsClient()

        mock_response = {
            "checkpoint_id": "cp_main",
            "parent_ids": ["cp_parent1", "cp_parent2"],
            "children_ids": ["cp_child1"],
            "tags": ["release"]
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.json.return_value = mock_response
            mock_client.get.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            lineage = await client.get_lineage("cp_main")

            assert lineage.checkpoint_id == "cp_main"
            assert len(lineage.parent_ids) == 2
            assert len(lineage.children_ids) == 1
            assert "release" in lineage.tags

    @pytest.mark.asyncio
    async def test_tag_checkpoint(self):
        """Test adding tags to checkpoint."""
        client = EntireOpsClient()

        mock_response = {
            "id": "cp_tagged",
            "commit_hash": "tagged123",
            "message": "Tagged commit",
            "timestamp": "2026-02-13T02:00:00Z",
            "author": "tagger",
            "files_changed": 1,
            "lines_added": 10,
            "lines_deleted": 0,
            "metadata": {}
        }

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client.post.return_value.json.return_value = mock_response
            mock_client.post.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            checkpoint = await client.tag_checkpoint(
                "cp_tagged",
                ["feature", "tested"]
            )

            assert checkpoint.id == "cp_tagged"
            # Verify tags were sent
            call_args = mock_client.post.call_args
            assert call_args[1]["json"]["tags"] == ["feature", "tested"]

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check returns healthy status."""
        client = EntireOpsClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.return_value.raise_for_status = Mock()
            mock_get_client.return_value = mock_client

            health = await client.health_check()

            assert health["status"] == "healthy"
            assert "latency_ms" in health
            assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check handles errors gracefully."""
        client = EntireOpsClient()

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client

            health = await client.health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "Connection failed" in health["error"]

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test client close cleans up connections."""
        client = EntireOpsClient()

        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()

        client._client = mock_http_client

        await client.close()

        mock_http_client.aclose.assert_awaited_once()
        assert client._client is None

    def test_singleton_pattern(self):
        """Test get_entire_ops returns singleton instance."""
        client1 = get_entire_ops(api_url="https://test1.io")
        client2 = get_entire_ops(api_url="https://test2.io")  # Should return same instance

        assert client1 is client2
        assert client1.api_url == "https://test1.io"  # Uses first config

    def test_reset_singleton(self):
        """Test reset_entire_ops clears singleton."""
        client1 = get_entire_ops()
        reset_entire_ops()
        client2 = get_entire_ops()

        assert client1 is not client2
