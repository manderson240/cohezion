"""
Test data and fixtures for Kyutai MCP server tests.
"""

from typing import Dict, List, Any


# Sample inputs for tool tests
SAMPLE_TEXTS = {
    "short": "Hello world",
    "medium": "This is a test message for text-to-speech synthesis.",
    "long": " ".join(["This is a longer test message."] * 20),
    "with_special_chars": "Testing special chars: @#$%^&*()!",
    "with_numbers": "The numbers are 1 2 3 4 5.",
    "multilingual": "Hello world! Bonjour le monde!",
}

# Sample voice configurations
VOICE_CONFIGS = {
    "default": {
        "voice_id": "default",
        "gender": "neutral",
        "language": "en",
    },
    "character_1": {
        "voice_id": "character_1",
        "gender": "male",
        "language": "en",
        "age": "adult",
    },
    "character_2": {
        "voice_id": "character_2",
        "gender": "female",
        "language": "fr",
        "age": "adult",
    },
}

# Sample audio configurations
AUDIO_CONFIGS = {
    "wav_16bit": {
        "format": "wav",
        "sample_rate": 16000,
        "bits": 16,
        "channels": 1,
    },
    "wav_24bit": {
        "format": "wav",
        "sample_rate": 44100,
        "bits": 24,
        "channels": 2,
    },
    "mp3": {
        "format": "mp3",
        "sample_rate": 44100,
        "bitrate": "192k",
    },
}

# Sample model configurations
MODEL_CATALOG = {
    "tts": [
        {
            "id": "pocket-tts",
            "name": "Pocket TTS",
            "parameters": 100_000_000,
            "size_gb": 0.4,
            "input_modality": ["text"],
            "output_modality": ["audio"],
            "languages": ["en", "fr"],
            "inference_device": "cpu",
            "latency_ms": 45,
        },
        {
            "id": "kyutai-tts-1.6b",
            "name": "Kyutai TTS 1.6B",
            "parameters": 1_600_000_000,
            "size_gb": 3.2,
            "input_modality": ["text"],
            "output_modality": ["audio"],
            "languages": ["en", "fr", "es", "de"],
            "inference_device": "gpu",
            "latency_ms": 120,
        },
    ],
    "stt": [
        {
            "id": "stt-1b-en_fr",
            "name": "STT 1B English/French",
            "parameters": 1_000_000_000,
            "size_gb": 2.0,
            "input_modality": ["audio"],
            "output_modality": ["text"],
            "languages": ["en", "fr"],
            "inference_device": "cpu",
            "latency_ms": 150,
        },
        {
            "id": "stt-2.6b-multilingual",
            "name": "STT 2.6B Multilingual",
            "parameters": 2_600_000_000,
            "size_gb": 5.2,
            "input_modality": ["audio"],
            "output_modality": ["text"],
            "languages": ["en", "fr", "es", "de", "it", "pt", "ja", "zh"],
            "inference_device": "gpu",
            "latency_ms": 200,
        },
    ],
    "dialogue": [
        {
            "id": "moshi",
            "name": "Moshi",
            "parameters": 7_000_000_000,
            "size_gb": 14.0,
            "input_modality": ["audio", "text"],
            "output_modality": ["audio", "text"],
            "languages": ["en", "fr"],
            "inference_device": "gpu",
            "latency_ms": 500,
        },
    ],
}

# Health check responses
HEALTH_RESPONSES = {
    "healthy": {
        "status": "healthy",
        "models": {
            "pocket-tts": "ready",
            "stt-1b-en_fr": "ready",
        },
        "uptime_seconds": 3600,
        "timestamp": "2024-01-15T10:30:00Z",
    },
    "degraded": {
        "status": "degraded",
        "models": {
            "pocket-tts": "ready",
            "stt-1b-en_fr": "loading",
        },
        "uptime_seconds": 300,
        "timestamp": "2024-01-15T10:30:00Z",
    },
    "unhealthy": {
        "status": "unhealthy",
        "models": {
            "pocket-tts": "error",
            "stt-1b-en_fr": "error",
        },
        "uptime_seconds": 0,
        "timestamp": "2024-01-15T10:30:00Z",
    },
}

# Transcription test data
TRANSCRIPTION_RESULTS = {
    "simple": {
        "text": "Hello world",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 1.0,
                "text": "Hello world",
            },
        ],
        "language": "en",
    },
    "with_timestamps": {
        "text": "This is a test",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 0.5,
                "text": "This is",
                "words": [
                    {"word": "This", "start": 0.0, "end": 0.2},
                    {"word": "is", "start": 0.2, "end": 0.5},
                ],
            },
            {
                "id": 1,
                "start": 0.5,
                "end": 1.2,
                "text": "a test",
                "words": [
                    {"word": "a", "start": 0.5, "end": 0.7},
                    {"word": "test", "start": 0.7, "end": 1.2},
                ],
            },
        ],
        "language": "en",
    },
}

# Error scenarios
ERROR_SCENARIOS = {
    "text_too_long": {
        "error": "text_length_exceeded",
        "message": "Text exceeds maximum length of 4096 characters",
        "max_length": 4096,
        "provided_length": 5000,
    },
    "invalid_voice_id": {
        "error": "invalid_voice_id",
        "message": "Voice ID 'invalid_voice' not found. Using default voice.",
        "provided_voice_id": "invalid_voice",
    },
    "model_not_available": {
        "error": "model_not_available",
        "message": "Model 'unknown-model' not available",
        "model": "unknown-model",
        "available_models": ["pocket-tts", "kyutai-tts-1.6b"],
    },
    "file_not_found": {
        "error": "file_not_found",
        "message": "Audio file not found: /path/to/nonexistent/file.wav",
        "file_path": "/path/to/nonexistent/file.wav",
    },
    "unsupported_format": {
        "error": "unsupported_format",
        "message": "Unsupported audio format: flac",
        "provided_format": "flac",
        "supported_formats": ["wav", "mp3", "ogg", "m4a"],
    },
    "disk_full": {
        "error": "disk_full",
        "message": "Insufficient disk space: 100MB required, 50MB available",
        "required_mb": 100,
        "available_mb": 50,
    },
}

# Configuration test data
CONFIG_DATA = {
    "minimal": {
        "models": {
            "tts": "pocket-tts",
        },
    },
    "standard": {
        "models": {
            "tts": "pocket-tts",
            "stt": "stt-1b-en_fr",
        },
        "api_endpoints": {
            "stt": "http://localhost:8001/v1",
            "tts": "http://localhost:8002/v1",
        },
    },
    "advanced": {
        "models": {
            "tts": "kyutai-tts-1.6b",
            "stt": "stt-2.6b-multilingual",
            "dialogue": "moshi",
        },
        "api_endpoints": {
            "stt": "http://localhost:8001/v1",
            "tts": "http://localhost:8002/v1",
            "dialogue": "ws://localhost:8003/v1",
        },
        "pocket_tts": {
            "voice": "default",
            "speed": 1.2,
            "quality": "high",
        },
        "health_check_interval": 30,
    },
}


def get_sample_text(key: str = "medium") -> str:
    """Get a sample text by key."""
    return SAMPLE_TEXTS.get(key, SAMPLE_TEXTS["medium"])


def get_voice_config(key: str = "default") -> Dict[str, Any]:
    """Get a voice configuration by key."""
    return VOICE_CONFIGS.get(key, VOICE_CONFIGS["default"]).copy()


def get_model_list(category: str = "tts") -> List[Dict[str, Any]]:
    """Get a model list by category."""
    return MODEL_CATALOG.get(category, []).copy()


def get_health_response(status: str = "healthy") -> Dict[str, Any]:
    """Get a health response by status."""
    return HEALTH_RESPONSES.get(status, HEALTH_RESPONSES["healthy"]).copy()


def get_error_scenario(error_type: str) -> Dict[str, Any]:
    """Get an error scenario by type."""
    return ERROR_SCENARIOS.get(error_type, {}).copy()
