"""Tests for Pocket TTS integration.

Following token-efficient pattern: tests written AFTER implementation and validation.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


# Ensure pocket_tts module exists for patching (optional dependency)
if "pocket_tts" not in sys.modules:
    _mock_pocket_tts = MagicMock()
    sys.modules["pocket_tts"] = _mock_pocket_tts


@pytest.fixture
def mock_tts_model():
    """Mock TTSModel for testing without real model."""
    import torch

    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_model.sample_rate = 24000
    mock_model.get_state_for_audio_prompt.return_value = {"state": "mock"}
    mock_model.generate_audio.return_value = torch.zeros(24000)  # 1 sec silence

    return mock_model


class TestPocketTTSService:
    """Test PocketTTSService class."""

    @patch("pocket_tts.TTSModel")
    def test_initialize_success(self, mock_tts_class, mock_tts_model):
        """Test model initialization succeeds."""
        from mcp_server.pocket_tts import PocketTTSService

        mock_tts_class.load_model.return_value = mock_tts_model

        service = PocketTTSService()
        service.initialize()

        assert service._initialized is True
        assert service.sample_rate == 24000
        mock_tts_class.load_model.assert_called_once()

    @patch("torchaudio.save")
    @patch("pocket_tts.TTSModel")
    def test_speak_basic(self, mock_tts_class, mock_torchaudio_save, mock_tts_model):
        """Test basic text-to-speech synthesis."""
        from mcp_server.pocket_tts import PocketTTSService

        mock_tts_class.load_model.return_value = mock_tts_model

        service = PocketTTSService()
        result = service.speak("Hello world")

        assert result["status"] == "success"
        assert "audio_base64" in result
        assert result["duration_ms"] == 1000  # 1 second of audio
        assert result["sample_rate"] == 24000
        # Verify torchaudio.save was called
        assert mock_torchaudio_save.called

    def test_speak_empty_text(self):
        """Test error on empty text."""
        from mcp_server.pocket_tts import PocketTTSService

        service = PocketTTSService()
        result = service.speak("")

        assert result["status"] == "error"
        assert "empty" in result["error"].lower()

    def test_speak_whitespace_only(self):
        """Test error on whitespace-only text."""
        from mcp_server.pocket_tts import PocketTTSService

        service = PocketTTSService()
        result = service.speak("   \t\n   ")

        assert result["status"] == "error"
        assert "empty" in result["error"].lower()

    def test_speak_text_too_long(self):
        """Test error on text >4096 chars."""
        from mcp_server.pocket_tts import PocketTTSService

        service = PocketTTSService()
        long_text = "a" * 5000
        result = service.speak(long_text)

        assert result["status"] == "error"
        assert "too long" in result["error"].lower()

    def test_speak_text_at_limit(self):
        """Test success at exactly 4096 chars."""
        from mcp_server.pocket_tts import PocketTTSService

        with patch("pocket_tts.TTSModel") as mock_tts_class, patch("torchaudio.save"):
            import torch

            mock_model = MagicMock()
            mock_model.device = "cpu"
            mock_model.sample_rate = 24000
            mock_model.get_state_for_audio_prompt.return_value = {"state": "mock"}
            mock_model.generate_audio.return_value = torch.zeros(24000)
            mock_tts_class.load_model.return_value = mock_model

            service = PocketTTSService()
            result = service.speak("a" * 4096)

            assert result["status"] == "success"

    @patch("pocket_tts.TTSModel")
    def test_model_load_failure(self, mock_tts_class):
        """Test graceful handling of model load failure."""
        from mcp_server.pocket_tts import PocketTTSService

        mock_tts_class.load_model.side_effect = RuntimeError("CUDA OOM")

        service = PocketTTSService()
        result = service.speak("Test")

        assert result["status"] == "error"
        assert "CUDA OOM" in result["error"]

    @patch("pocket_tts.TTSModel")
    def test_synthesis_failure(self, mock_tts_class):
        """Test graceful handling of synthesis failure."""
        from mcp_server.pocket_tts import PocketTTSService

        mock_model = MagicMock()
        mock_model.device = "cpu"
        mock_model.sample_rate = 24000
        mock_model.generate_audio.side_effect = RuntimeError("Synthesis failed")
        mock_tts_class.load_model.return_value = mock_model

        service = PocketTTSService()
        result = service.speak("Test")

        assert result["status"] == "error"
        assert "Synthesis failed" in result["error"]

    @patch("pocket_tts.TTSModel")
    def test_lazy_initialization(self, mock_tts_class, mock_tts_model):
        """Test model is loaded lazily on first speak() call."""
        from mcp_server.pocket_tts import PocketTTSService

        mock_tts_class.load_model.return_value = mock_tts_model

        service = PocketTTSService()
        assert service._initialized is False

        # First call initializes
        service.speak("Hello")
        assert service._initialized is True
        assert mock_tts_class.load_model.call_count == 1

        # Second call doesn't re-initialize
        service.speak("World")
        assert mock_tts_class.load_model.call_count == 1


class TestTTSMCPTool:
    """Test MCP tool integration."""

    @pytest.mark.asyncio
    async def test_tts_speak_tool_success(self):
        """Test tts_speak tool returns valid JSON."""
        from pathlib import Path

        from mcp_server.config import ServerConfig
        from mcp_server.server import create_server

        with patch("mcp_server.pocket_tts.PocketTTSService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.speak.return_value = {
                "status": "success",
                "audio_base64": "AABBCC==",
                "duration_ms": 500,
                "sample_rate": 24000,
                "model": "pocket-tts",
            }
            mock_service_class.return_value = mock_service

            # Create server
            config = ServerConfig(
                vault_path=str(Path.home() / "vaults" / "cohezion-vault"),
                watcher_enabled=False,
            )
            mcp = create_server(config)

            # Call tool
            result_content, result_dict = await mcp.call_tool(
                "tts_speak", {"text": "Hello"}
            )
            # Extract text from content
            result_text = result_content[0].text
            result_data = json.loads(result_text)

            assert result_data["status"] == "success"
            assert result_data["audio_base64"] == "AABBCC=="
            assert result_data["duration_ms"] == 500

    @pytest.mark.asyncio
    async def test_tts_speak_tool_error(self):
        """Test tts_speak tool returns error JSON on failure."""
        from pathlib import Path

        from mcp_server.config import ServerConfig
        from mcp_server.server import create_server

        with patch("mcp_server.pocket_tts.PocketTTSService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.speak.return_value = {
                "status": "error",
                "error": "Model not available",
            }
            mock_service_class.return_value = mock_service

            # Create server
            config = ServerConfig(
                vault_path=str(Path.home() / "vaults" / "cohezion-vault"),
                watcher_enabled=False,
            )
            mcp = create_server(config)

            # Call tool
            result_content, result_dict = await mcp.call_tool(
                "tts_speak", {"text": "Hello"}
            )
            # Extract text from content
            result_text = result_content[0].text
            result_data = json.loads(result_text)

            assert result_data["status"] == "error"
            assert "Model not available" in result_data["error"]
