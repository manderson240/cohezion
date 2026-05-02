"""Tests for ResilientOllamaClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.token_client import ResilientOllamaClient


class TestResilientOllamaClient:
    """Tests for ResilientOllamaClient."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful generation."""
        client = ResilientOllamaClient(base_url="http://localhost:11434")

        # Mock httpx.AsyncClient properly
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Hello, world!"},
            "eval_count": 50,
            "prompt_eval_count": 0,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("cohezion.swarm.token_client.httpx.AsyncClient", return_value=mock_client):
            response, tokens = await client.generate(
                prompt="Hello",
                model="phi3:mini",
            )

            assert response == "Hello, world!"
            assert tokens == 50

    @pytest.mark.asyncio
    async def test_generate_retry_success(self):
        """Test retry on failure then success."""
        client = ResilientOllamaClient(
            base_url="http://localhost:11434",
            max_retries=3,
        )

        # First call fails, second succeeds
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            "message": {"content": "Success"},
            "eval_count": 100,
            "prompt_eval_count": 0,
        }
        mock_response_success.raise_for_status = MagicMock()

        mock_client_fail = AsyncMock()
        mock_client_fail.post.side_effect = Exception("Connection failed")
        mock_client_fail.__aenter__ = AsyncMock(return_value=mock_client_fail)
        mock_client_fail.__aexit__ = AsyncMock(return_value=None)

        mock_client_success = AsyncMock()
        mock_client_success.post.return_value = mock_response_success
        mock_client_success.__aenter__ = AsyncMock(return_value=mock_client_success)
        mock_client_success.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "cohezion.swarm.token_client.httpx.AsyncClient",
            side_effect=[mock_client_fail, mock_client_success],
        ):
            response, tokens = await client.generate(
                prompt="Test",
                model="phi3:mini",
            )

            assert response == "Success"
            assert tokens == 100

    @pytest.mark.asyncio
    async def test_generate_max_retries_exceeded(self):
        """Test failure after max retries."""
        client = ResilientOllamaClient(
            base_url="http://localhost:11434",
            max_retries=2,
        )

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("cohezion.swarm.token_client.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError) as exc_info:
                await client.generate(
                    prompt="Test",
                    model="phi3:mini",
                )

            assert "failed after 2 retries" in str(exc_info.value)
