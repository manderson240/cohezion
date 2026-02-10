"""Configuration management for Kyutai MCP Server."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ServiceConfig:
    """Configuration for a single service (Pocket TTS, STT API, etc.)."""

    enabled: bool
    url: Optional[str] = None  # For APIs
    api_key: Optional[str] = None
    default_model: str = "pocket-tts"
    timeout_seconds: int = 30
    retry_count: int = 3


@dataclass
class KyutaiMCPConfig:
    """Main configuration for Kyutai MCP server."""

    host: str = "127.0.0.1"
    port: int = 8361
    log_level: str = "info"

    # Phase 1
    pocket_tts_enabled: bool = True
    pocket_tts_model_config: str = "b6369a24"
    pocket_tts_temperature: float = 0.7
    pocket_tts_eos_threshold: float = -4.0
    pocket_tts_voices_dir: str = ""

    # Phase 2
    tts_api_enabled: bool = False
    tts_api_url: Optional[str] = None
    tts_api_key: Optional[str] = None
    tts_api_model: str = "tts-1"

    stt_api_enabled: bool = False
    stt_api_url: Optional[str] = None
    stt_api_key: Optional[str] = None
    stt_api_model: str = "whisper-1"

    # Phase 3
    moshi_enabled: bool = False
    moshi_url: Optional[str] = None

    # Features
    health_check_enabled: bool = True
    health_check_interval: int = 60
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_audio_mb: int = 500
    max_text_length: int = 4096
    request_timeout_seconds: int = 30

    @staticmethod
    def load(path: str) -> "KyutaiMCPConfig":
        """Load configuration from YAML file."""
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path):
            # Return defaults if file doesn't exist
            return KyutaiMCPConfig()

        with open(expanded_path) as f:
            data = yaml.safe_load(f) or {}

        config = KyutaiMCPConfig()

        # Load server config
        if "server" in data:
            server_config = data["server"]
            config.host = server_config.get("host", config.host)
            config.port = server_config.get("port", config.port)
            config.log_level = server_config.get("log_level", config.log_level)

        # Load Pocket TTS config
        if "pocket_tts" in data:
            pt_config = data["pocket_tts"]
            config.pocket_tts_enabled = pt_config.get("enabled", config.pocket_tts_enabled)
            config.pocket_tts_model_config = pt_config.get("model_config", config.pocket_tts_model_config)
            config.pocket_tts_temperature = pt_config.get("temperature", config.pocket_tts_temperature)
            config.pocket_tts_eos_threshold = pt_config.get("eos_threshold", config.pocket_tts_eos_threshold)
            voices_dir = pt_config.get("voices_dir")
            if voices_dir:
                config.pocket_tts_voices_dir = os.path.expanduser(voices_dir)

        # Load APIs config
        if "apis" in data:
            apis = data["apis"]

            if "tts" in apis:
                tts = apis["tts"]
                config.tts_api_enabled = tts.get("enabled", config.tts_api_enabled)
                config.tts_api_url = tts.get("url", config.tts_api_url)
                config.tts_api_key = tts.get("api_key", config.tts_api_key)
                config.tts_api_model = tts.get("default_model", config.tts_api_model)

            if "stt" in apis:
                stt = apis["stt"]
                config.stt_api_enabled = stt.get("enabled", config.stt_api_enabled)
                config.stt_api_url = stt.get("url", config.stt_api_url)
                config.stt_api_key = stt.get("api_key", config.stt_api_key)
                config.stt_api_model = stt.get("default_model", config.stt_api_model)

        # Load Moshi config
        if "moshi" in data:
            moshi = data["moshi"]
            config.moshi_enabled = moshi.get("enabled", config.moshi_enabled)
            config.moshi_url = moshi.get("url", config.moshi_url)

        # Load health check config
        if "health" in data:
            health = data["health"]
            config.health_check_enabled = health.get("enabled", config.health_check_enabled)
            config.health_check_interval = health.get("interval_seconds", config.health_check_interval)

        # Load cache config
        if "cache" in data:
            cache = data["cache"]
            config.cache_enabled = cache.get("enabled", config.cache_enabled)
            config.cache_ttl_seconds = cache.get("ttl_seconds", config.cache_ttl_seconds)
            config.cache_max_audio_mb = cache.get("max_audio_mb", config.cache_max_audio_mb)

        return config

    @staticmethod
    def load_or_create(path: Optional[str] = None) -> "KyutaiMCPConfig":
        """Load config from path or environment, creating defaults if needed."""
        if not path:
            path = os.path.expanduser("~/.kyutai-mcp/config.yaml")

        return KyutaiMCPConfig.load(path)
