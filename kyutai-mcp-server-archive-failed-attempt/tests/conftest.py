"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.fixtures.mock_kyutai import (
    MockKyutaiTTSAPI,
    MockKyutaiSTTAPI,
    MockKyutaiHealthAPI,
    MockConfigFile,
    MockAudioFile,
)
from tests.fixtures.test_data import (
    get_sample_text,
    get_voice_config,
    get_model_list,
    get_health_response,
    AUDIO_CONFIGS,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy for asyncio tests."""
    import asyncio

    return asyncio.get_event_loop_policy()


@pytest.fixture
async def mock_tts_service():
    """Provide a mock TTS service instance."""
    api = MockKyutaiTTSAPI()
    return api


@pytest.fixture
async def mock_stt_service():
    """Provide a mock STT service instance."""
    api = MockKyutaiSTTAPI()
    return api


@pytest.fixture
async def mock_health_service(request):
    """Provide a mock health check service."""
    is_healthy = getattr(request, "param", True)
    api = MockKyutaiHealthAPI(is_healthy=is_healthy)
    return api


@pytest.fixture
def sample_config():
    """Provide sample configuration data."""
    config = MockConfigFile()
    config_path = config.create_temp_config()
    yield config_path
    config.cleanup()


@pytest.fixture
def sample_config_advanced():
    """Provide advanced sample configuration."""
    from tests.fixtures.test_data import CONFIG_DATA

    config = MockConfigFile(CONFIG_DATA["advanced"])
    config_path = config.create_temp_config()
    yield config_path
    config.cleanup()


@pytest.fixture
def temp_audio_file_wav():
    """Provide temporary WAV audio file."""
    audio_path = MockAudioFile.create_temp_wav(duration_ms=100)
    yield audio_path
    MockAudioFile.cleanup(audio_path)


@pytest.fixture
def temp_audio_file_mp3():
    """Provide temporary MP3 audio file."""
    audio_path = MockAudioFile.create_temp_mp3(duration_ms=100)
    yield audio_path
    MockAudioFile.cleanup(audio_path)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Provide temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return str(output_dir)


@pytest.fixture
def sample_texts():
    """Provide sample texts for testing."""
    return {
        "short": get_sample_text("short"),
        "medium": get_sample_text("medium"),
        "long": get_sample_text("long"),
    }


@pytest.fixture
def sample_voices():
    """Provide sample voice configurations."""
    return {
        "default": get_voice_config("default"),
        "character_1": get_voice_config("character_1"),
        "character_2": get_voice_config("character_2"),
    }


@pytest.fixture
def sample_models():
    """Provide sample model configurations."""
    return {
        "tts": get_model_list("tts"),
        "stt": get_model_list("stt"),
        "dialogue": get_model_list("dialogue"),
    }


@pytest.fixture
def health_responses():
    """Provide health check responses."""
    return {
        "healthy": get_health_response("healthy"),
        "degraded": get_health_response("degraded"),
        "unhealthy": get_health_response("unhealthy"),
    }


@pytest.fixture
def audio_formats():
    """Provide audio format configurations."""
    return AUDIO_CONFIGS


class MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(self):
        self.tools = {}
        self.tool_calls = []

    def register_tool(self, name: str, handler):
        """Register a tool handler."""
        self.tools[name] = handler

    async def call_tool(self, name: str, params: dict):
        """Call a registered tool."""
        self.tool_calls.append({"name": name, "params": params})

        if name not in self.tools:
            return {
                "status": "error",
                "error": f"Tool '{name}' not found",
            }

        try:
            return await self.tools[name](**params)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_call_count(self, tool_name: str) -> int:
        """Get number of calls to a tool."""
        return sum(1 for call in self.tool_calls if call["name"] == tool_name)

    def reset(self):
        """Reset call history."""
        self.tool_calls = []


@pytest.fixture
def mock_mcp_server():
    """Provide a mock MCP server."""
    return MockMCPServer()


@pytest.fixture
def mock_http_client():
    """Provide a mock HTTP client."""
    from aioresponses import aioresponses

    with aioresponses() as m:
        yield m


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "mock_api: mark test as using mocked APIs"
    )
