"""
Mock fixtures for Kyutai API responses.

Provides mock implementations of Kyutai APIs for testing without external dependencies.
"""

import json
import base64
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import tempfile
from pathlib import Path


class MockKyutaiTTSAPI:
    """Mock Kyutai TTS API for testing."""

    def __init__(self):
        self.call_count = 0
        self.last_request = None

    async def speak(self, text: str, voice_id: str = "default", **kwargs) -> Dict[str, Any]:
        """Mock TTS synthesis."""
        self.call_count += 1
        self.last_request = {
            "text": text,
            "voice_id": voice_id,
            **kwargs
        }

        # Generate mock audio data (silent WAV)
        mock_audio_bytes = self._generate_mock_wav(duration_ms=100)

        return {
            "status": "success",
            "audio_base64": base64.b64encode(mock_audio_bytes).decode(),
            "duration_ms": 100,
            "model_used": "pocket-tts",
            "latency_ms": 45,
        }

    async def speak_with_file(self, text: str, output_path: str, **kwargs) -> Dict[str, Any]:
        """Mock TTS synthesis with file output."""
        result = await self.speak(text, **kwargs)

        # Write mock audio to file
        mock_audio_bytes = base64.b64decode(result["audio_base64"])
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(mock_audio_bytes)

        result["audio_path"] = output_path
        del result["audio_base64"]
        return result

    @staticmethod
    def _generate_mock_wav(duration_ms: int = 100) -> bytes:
        """Generate a minimal valid WAV file header."""
        # Minimal WAV file (44.1kHz, mono, 16-bit)
        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000)
        num_bytes = num_samples * 2

        # WAV header
        header = bytearray()
        header.extend(b"RIFF")
        header.extend((36 + num_bytes).to_bytes(4, "little"))
        header.extend(b"WAVE")
        header.extend(b"fmt ")
        header.extend((16).to_bytes(4, "little"))  # Subchunk1Size
        header.extend((1).to_bytes(2, "little"))   # AudioFormat (PCM)
        header.extend((1).to_bytes(2, "little"))   # NumChannels
        header.extend(sample_rate.to_bytes(4, "little"))  # SampleRate
        header.extend((sample_rate * 2).to_bytes(4, "little"))  # ByteRate
        header.extend((2).to_bytes(2, "little"))   # BlockAlign
        header.extend((16).to_bytes(2, "little"))  # BitsPerSample
        header.extend(b"data")
        header.extend(num_bytes.to_bytes(4, "little"))

        # Add silent audio data
        header.extend(b"\x00" * num_bytes)

        return bytes(header)


class MockKyutaiSTTAPI:
    """Mock Kyutai STT API for testing."""

    def __init__(self):
        self.call_count = 0
        self.last_request = None

    async def transcribe(
        self,
        audio_path: str,
        model: str = "stt-1b-en_fr",
        language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock speech-to-text transcription."""
        self.call_count += 1
        self.last_request = {
            "audio_path": audio_path,
            "model": model,
            "language": language,
            **kwargs
        }

        return {
            "status": "success",
            "text": "This is a mock transcription of the audio.",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 1.5,
                    "text": "This is a mock",
                },
                {
                    "id": 1,
                    "start": 1.5,
                    "end": 2.8,
                    "text": "transcription of the audio.",
                },
            ],
            "language": language or "en",
            "model_used": model,
            "latency_ms": 120,
        }

    async def transcribe_with_timestamps(
        self, audio_path: str, **kwargs
    ) -> Dict[str, Any]:
        """Mock transcription with word-level timestamps."""
        result = await self.transcribe(audio_path, **kwargs)
        result["segments"][0]["words"] = [
            {"word": "This", "start": 0.0, "end": 0.3},
            {"word": "is", "start": 0.3, "end": 0.5},
            {"word": "a", "start": 0.5, "end": 0.7},
            {"word": "mock", "start": 0.7, "end": 1.1},
        ]
        return result


class MockKyutaiHealthAPI:
    """Mock Kyutai health check API."""

    def __init__(self, is_healthy: bool = True):
        self.is_healthy = is_healthy
        self.call_count = 0

    async def check_health(self) -> Dict[str, Any]:
        """Mock health check endpoint."""
        self.call_count += 1
        return {
            "status": "healthy" if self.is_healthy else "unhealthy",
            "models": {
                "pocket-tts": "ready",
                "stt-1b-en_fr": "ready" if self.is_healthy else "loading",
            },
            "uptime_seconds": 3600,
        }

    async def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Mock model status endpoint."""
        return {
            "model_id": model_id,
            "status": "ready" if self.is_healthy else "loading",
            "memory_mb": 1024,
            "last_used": "2024-01-15T10:30:00Z",
        }


class MockConfigFile:
    """Mock configuration file handler."""

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self.config_data = config_data or self._default_config()
        self.config_file = None

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "models": {
                "tts": "pocket-tts",
                "stt": "stt-1b-en_fr",
            },
            "pocket_tts": {
                "voice": "default",
                "speed": 1.0,
            },
            "api_endpoints": {
                "stt": "http://localhost:8001/v1",
                "tts": "http://localhost:8002/v1",
            },
            "health_check_interval": 60,
        }

    def create_temp_config(self) -> str:
        """Create a temporary config file and return its path."""
        import yaml

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(self.config_data, f)
            self.config_file = f.name

        return self.config_file

    def cleanup(self):
        """Delete temporary config file."""
        if self.config_file and Path(self.config_file).exists():
            Path(self.config_file).unlink()

    def __enter__(self):
        return self.create_temp_config()

    def __exit__(self, *args):
        self.cleanup()


class MockAudioFile:
    """Create mock audio files for testing."""

    @staticmethod
    def create_temp_wav(duration_ms: int = 100) -> str:
        """Create a temporary WAV file."""
        from tests.fixtures.mock_kyutai import MockKyutaiTTSAPI

        audio_bytes = MockKyutaiTTSAPI._generate_mock_wav(duration_ms)

        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as f:
            f.write(audio_bytes)
            return f.name

    @staticmethod
    def create_temp_mp3(duration_ms: int = 100) -> str:
        """Create a temporary MP3 file (minimal mock)."""
        # Minimal MP3 frame
        mp3_data = b"ID3" + b"\x00" * 1000

        with tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False
        ) as f:
            f.write(mp3_data)
            return f.name

    @staticmethod
    def cleanup(audio_path: str):
        """Delete temporary audio file."""
        if Path(audio_path).exists():
            Path(audio_path).unlink()


# Pytest fixtures
import pytest


@pytest.fixture
def mock_tts_api():
    """Provide mock TTS API."""
    return MockKyutaiTTSAPI()


@pytest.fixture
def mock_stt_api():
    """Provide mock STT API."""
    return MockKyutaiSTTAPI()


@pytest.fixture
def mock_health_api():
    """Provide mock health API."""
    return MockKyutaiHealthAPI()


@pytest.fixture
def mock_config():
    """Provide mock configuration."""
    config = MockConfigFile()
    config_path = config.create_temp_config()
    yield config_path
    config.cleanup()


@pytest.fixture
def temp_wav_file():
    """Provide temporary WAV file."""
    audio_path = MockAudioFile.create_temp_wav()
    yield audio_path
    MockAudioFile.cleanup(audio_path)


@pytest.fixture
def temp_mp3_file():
    """Provide temporary MP3 file."""
    audio_path = MockAudioFile.create_temp_mp3()
    yield audio_path
    MockAudioFile.cleanup(audio_path)
