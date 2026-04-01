"""Tests for api/services/anima.py.

Covers Anima 3-tier intelligence service.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.api.services.anima import (
    AnimaService,
)


@pytest.fixture
def mock_httpx_get():
    with patch("httpx.get") as mock:
        mock.return_value.status_code = 200
        yield mock

@pytest.fixture
def anima_service(mock_httpx_get):
    return AnimaService()

def test_get_status(anima_service):
    """[P0] Should return service status."""
    status = anima_service.get_status()
    assert status.online is True
    assert status.tier in ["voice", "mcp", "template"]

@pytest.mark.asyncio
async def test_ask_template_fallback(anima_service):
    """[P0] Should fallback to template for unknown questions."""
    # Force MCP unavailable for this test
    anima_service._mcp_available = False
    
    result = await anima_service.ask("what is hiho?")
    assert result.tier == "template"
    assert "HIHO" in result.answer

@pytest.mark.asyncio
async def test_ask_mcp_success(anima_service):
    """[P0] Should use MCP when available."""
    anima_service._mcp_available = True
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"content": "Grounded answer", "source": "test-vault"}]
    
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        result = await anima_service.ask("test question")
        assert result.tier == "mcp"
        assert "Grounded answer" in result.answer
        assert "test-vault" in result.sources

@pytest.mark.asyncio
async def test_speak_fallback(anima_service):
    """[P0] Should fallback when voice is unavailable."""
    anima_service._voice_available = False
    result = await anima_service.speak("hello")
    assert result.tier == "template"
    assert result.audio_base64 is None
    assert result.fallback_text == "hello"
