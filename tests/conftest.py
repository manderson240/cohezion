"""Shared test fixtures for the Cohezion test suite."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_ollama():
    """Patch httpx calls to Ollama, returning a canned JSON response."""
    canned = {"response": "mocked-ollama-response", "done": True}
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value=canned),
        raise_for_status=MagicMock(),
    )
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
    ) as mock_post:
        yield mock_post


@pytest.fixture
def mock_surreal():
    """Patch SurrealDB client methods to return empty results without a live connection."""
    with patch("cohezion.core.persistence.surreal_client.SurrealClient") as mock_cls:
        instance = mock_cls.return_value
        instance.connect = AsyncMock()
        instance.close = AsyncMock()
        instance.query = AsyncMock(return_value=[])
        instance.store_node = AsyncMock()
        instance.get_node = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
def tmp_workdir(tmp_path: Path):
    """Provide a temporary working directory that auto-cleans after the test."""
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return workdir
