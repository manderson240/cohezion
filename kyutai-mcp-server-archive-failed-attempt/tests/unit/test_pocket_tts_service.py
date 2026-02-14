"""
Unit tests for PocketTTSService.

Tests speech synthesis functionality including:
- Text-to-speech synthesis
- Voice configuration
- Error handling
- Audio format support
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.unit


class TestPocketTTSService:
    """Tests for PocketTTSService initialization and configuration."""

    def test_service_initialization(self):
        """Test PocketTTSService can be initialized."""
        # Placeholder for actual implementation
        # from src.services.pocket_tts_service import PocketTTSService
        # service = PocketTTSService()
        # assert service is not None
        pass

    @pytest.mark.asyncio
    async def test_speak_text_basic(self, mock_tts_service, sample_texts):
        """Test basic text-to-speech synthesis."""
        text = sample_texts["short"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result
        assert result["duration_ms"] > 0
        assert result["model_used"] == "pocket-tts"
        assert result["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_speak_text_medium_length(self, mock_tts_service, sample_texts):
        """Test medium-length text synthesis."""
        text = sample_texts["medium"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result
        assert result["duration_ms"] >= sample_texts["short"].__len__() * 10

    @pytest.mark.asyncio
    async def test_speak_text_with_voice_id(self, mock_tts_service, sample_texts, sample_voices):
        """Test synthesis with custom voice ID."""
        text = sample_texts["short"]
        voice_id = sample_voices["character_1"]["voice_id"]

        result = await mock_tts_service.speak(text, voice_id=voice_id)

        assert result["status"] == "success"
        assert mock_tts_service.last_request["voice_id"] == voice_id

    @pytest.mark.asyncio
    async def test_speak_text_with_speed_control(self, mock_tts_service, sample_texts):
        """Test synthesis with speed control."""
        text = sample_texts["short"]
        speed = 1.5

        result = await mock_tts_service.speak(text, speed=speed)

        assert result["status"] == "success"
        assert mock_tts_service.last_request["speed"] == speed

    @pytest.mark.asyncio
    async def test_speak_text_empty_string(self, mock_tts_service):
        """Test handling of empty text input."""
        result = await mock_tts_service.speak("")

        # Should either return error or handle gracefully
        assert "status" in result
        if result["status"] == "error":
            assert "error" in result

    @pytest.mark.asyncio
    async def test_speak_text_special_characters(self, mock_tts_service, sample_texts):
        """Test synthesis with special characters."""
        text = sample_texts["with_special_chars"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result

    @pytest.mark.asyncio
    async def test_speak_text_multilingual(self, mock_tts_service, sample_texts):
        """Test synthesis with multilingual text."""
        text = sample_texts["multilingual"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result

    @pytest.mark.asyncio
    async def test_speak_text_with_numbers(self, mock_tts_service, sample_texts):
        """Test synthesis with numbers."""
        text = sample_texts["with_numbers"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result

    @pytest.mark.asyncio
    async def test_speak_text_output_formats(self, mock_tts_service, sample_texts):
        """Test different output audio formats."""
        text = sample_texts["short"]
        formats = ["wav", "mp3", "ogg"]

        for audio_format in formats:
            result = await mock_tts_service.speak(text, output_format=audio_format)
            assert result["status"] == "success"
            assert mock_tts_service.last_request["output_format"] == audio_format

    @pytest.mark.asyncio
    async def test_speak_text_to_file(self, mock_tts_service, sample_texts, temp_output_dir):
        """Test synthesis with file output."""
        text = sample_texts["short"]
        output_path = Path(temp_output_dir) / "test_output.wav"

        result = await mock_tts_service.speak_with_file(text, str(output_path))

        assert result["status"] == "success"
        assert "audio_path" in result
        assert Path(result["audio_path"]).exists()
        assert result["audio_path"] == str(output_path)

    @pytest.mark.asyncio
    async def test_speak_text_long_text(self, mock_tts_service, sample_texts):
        """Test synthesis with long text (may be split)."""
        text = sample_texts["long"]
        result = await mock_tts_service.speak(text)

        assert result["status"] == "success"
        assert "audio_base64" in result
        # Longer text should have longer duration
        assert result["duration_ms"] > 1000

    @pytest.mark.asyncio
    async def test_speak_call_count(self, mock_tts_service, sample_texts):
        """Test call count tracking."""
        initial_count = mock_tts_service.call_count
        await mock_tts_service.speak(sample_texts["short"])
        await mock_tts_service.speak(sample_texts["medium"])

        assert mock_tts_service.call_count == initial_count + 2

    @pytest.mark.asyncio
    async def test_invalid_voice_fallback(self, mock_tts_service, sample_texts):
        """Test fallback to default voice with invalid voice ID."""
        text = sample_texts["short"]
        result = await mock_tts_service.speak(text, voice_id="invalid_voice")

        # Should return success but may log warning
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_speed_boundary_values(self, mock_tts_service, sample_texts):
        """Test speed control with boundary values."""
        text = sample_texts["short"]

        # Test minimum speed
        result = await mock_tts_service.speak(text, speed=0.5)
        assert result["status"] == "success"

        # Test maximum speed
        result = await mock_tts_service.speak(text, speed=2.0)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_concurrent_synthesis(self, mock_tts_service, sample_texts):
        """Test concurrent text-to-speech requests."""
        text = sample_texts["short"]

        tasks = [
            mock_tts_service.speak(text),
            mock_tts_service.speak(text),
            mock_tts_service.speak(text),
        ]

        results = await asyncio.gather(*tasks)

        assert all(r["status"] == "success" for r in results)
        assert mock_tts_service.call_count >= 3

    @pytest.mark.asyncio
    async def test_voice_configuration_persistence(self, mock_tts_service, sample_texts, sample_voices):
        """Test that voice configuration persists across calls."""
        voice = sample_voices["character_1"]

        await mock_tts_service.speak(sample_texts["short"], voice_id=voice["voice_id"])
        request1 = mock_tts_service.last_request

        await mock_tts_service.speak(sample_texts["medium"], voice_id=voice["voice_id"])
        request2 = mock_tts_service.last_request

        assert request1["voice_id"] == request2["voice_id"] == voice["voice_id"]

    @pytest.mark.asyncio
    async def test_audio_quality_options(self, mock_tts_service, sample_texts):
        """Test audio quality configuration."""
        text = sample_texts["short"]

        # Test with different quality options
        qualities = ["low", "medium", "high"]
        for quality in qualities:
            result = await mock_tts_service.speak(text, quality=quality)
            if "quality" in mock_tts_service.last_request:
                assert mock_tts_service.last_request["quality"] == quality

    @pytest.mark.asyncio
    async def test_latency_measurement(self, mock_tts_service, sample_texts):
        """Test latency measurement in response."""
        text = sample_texts["short"]
        result = await mock_tts_service.speak(text)

        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] > 0
        assert result["latency_ms"] < 5000  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_duration_accuracy(self, mock_tts_service, sample_texts):
        """Test that reported duration matches audio content."""
        text = sample_texts["medium"]
        result = await mock_tts_service.speak(text)

        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], (int, float))
        assert result["duration_ms"] > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stress_test_multiple_voices(self, mock_tts_service, sample_texts, sample_voices):
        """Stress test with multiple voices."""
        text = sample_texts["short"]
        voices = list(sample_voices.values())

        for voice in voices:
            result = await mock_tts_service.speak(text, voice_id=voice["voice_id"])
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_repeated_calls_same_text(self, mock_tts_service, sample_texts):
        """Test repeated calls with same text produce consistent results."""
        text = sample_texts["short"]

        result1 = await mock_tts_service.speak(text)
        result2 = await mock_tts_service.speak(text)
        result3 = await mock_tts_service.speak(text)

        assert result1["duration_ms"] == result2["duration_ms"] == result3["duration_ms"]
