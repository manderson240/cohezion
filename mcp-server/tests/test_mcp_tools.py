"""Tests for MCP tools."""

import pytest
import asyncio
from pathlib import Path

# These tests are placeholders for Phase 1 MVP
# Full tests will be added in Phase 3 with proper fixtures


@pytest.mark.asyncio
async def test_list_models():
    """Test list_models tool."""
    # Placeholder test
    # In real implementation, will call MCP server and verify model list
    assert True


@pytest.mark.asyncio
async def test_speak_text_validation():
    """Test speak_text input validation."""
    # Placeholder test
    # Will verify that oversized text is rejected
    assert True


@pytest.mark.asyncio
async def test_get_model_status():
    """Test get_model_status tool."""
    # Placeholder test
    # Will verify health check endpoint
    assert True


def test_config_loading():
    """Test configuration loading."""
    from src.kyutai_mcp.config import KyutaiMCPConfig

    config = KyutaiMCPConfig.load_or_create()
    assert config.host == "127.0.0.1"
    assert config.port == 8361
    assert config.pocket_tts_enabled is True


def test_service_config():
    """Test service configuration."""
    from src.kyutai_mcp.config import ServiceConfig

    config = ServiceConfig(
        enabled=True,
        default_model="pocket-tts",
    )
    assert config.enabled is True
    assert config.default_model == "pocket-tts"
