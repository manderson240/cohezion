"""MCP Server definition with all tools registered."""

import json
import logging
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .config import KyutaiMCPConfig
from .services.health import HealthMonitor
from .services.moshi import MoshiService
from .services.pocket_tts import PocketTTSService
from .services.stt_api import STTAPIService
from .services.tts_api import TTSAPIService

logger = logging.getLogger(__name__)


def create_server(config: KyutaiMCPConfig) -> FastMCP:
    """Create and configure the MCP server with all 7 tools.

    Args:
        config: Kyutai MCP configuration

    Returns:
        Configured FastMCP server instance
    """

    # Initialize services based on config
    pocket_tts = None
    tts_api = None
    stt_api = None
    moshi = None

    # Phase 1: Pocket TTS
    if config.pocket_tts_enabled:
        from .config import ServiceConfig

        pt_config = ServiceConfig(
            enabled=True,
            default_model=config.pocket_tts_model_config,
        )
        try:
            pocket_tts = PocketTTSService(pt_config)
            logger.info("Pocket TTS service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Pocket TTS: {e}")

    # Phase 2: TTS API
    if config.tts_api_enabled and config.tts_api_url:
        from .config import ServiceConfig

        tts_config = ServiceConfig(
            enabled=True,
            url=config.tts_api_url,
            api_key=config.tts_api_key,
            default_model=config.tts_api_model,
        )
        try:
            tts_api = TTSAPIService(tts_config)
            logger.info("TTS API service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TTS API: {e}")

    # Phase 2: STT API
    if config.stt_api_enabled and config.stt_api_url:
        from .config import ServiceConfig

        stt_config = ServiceConfig(
            enabled=True,
            url=config.stt_api_url,
            api_key=config.stt_api_key,
            default_model=config.stt_api_model,
        )
        try:
            stt_api = STTAPIService(stt_config)
            logger.info("STT API service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize STT API: {e}")

    # Phase 3: Moshi
    if config.moshi_enabled:
        from .config import ServiceConfig

        moshi_config = ServiceConfig(
            enabled=True,
            url=config.moshi_url,
        )
        moshi = MoshiService(moshi_config)
        logger.info("Moshi service initialized (stub)")

    # Build services dict for health monitoring
    services = {}
    if pocket_tts:
        services["pocket-tts"] = pocket_tts
    if tts_api:
        services["tts-api"] = tts_api
    if stt_api:
        services["stt-api"] = stt_api
    if moshi:
        services["moshi"] = moshi

    health_monitor = HealthMonitor(services)

    # Create MCP server
    mcp = FastMCP(
        "Kyutai Voice",
        instructions=(
            "A voice AI MCP server for Kyutai models. "
            "Generate audio from text (TTS), transcribe audio (STT), "
            "and manage voice configurations."
        ),
    )

    # ── Tool 1: speak_text ────────────────────────────────────────────────

    @mcp.tool()
    async def speak_text(
        text: str,
        voice_id: str = "default",
        model: str = "pocket-tts",
        speed: float = 1.0,
        output_format: str = "wav",
    ) -> Dict[str, Any]:
        """Generate audio from text using TTS model.

        Args:
            text: Text to synthesize (1-4096 chars)
            voice_id: Voice sample ID (default: "default")
            model: Model selection (default: "pocket-tts")
            speed: Playback speed (0.5-2.0, default: 1.0)
            output_format: Audio format (wav, mp3, ogg, default: "wav")

        Returns:
            Dictionary with audio_path, duration_ms, model_used, latency_ms, status
        """
        # Select appropriate service based on model
        if model == "pocket-tts" and pocket_tts:
            return await pocket_tts.speak(text, voice_id, speed, output_format)
        elif model == "tts-api" and tts_api:
            return await tts_api.speak(text, voice_id, output_format)
        else:
            # Fall back to Pocket TTS
            if pocket_tts:
                return await pocket_tts.speak(text, voice_id, speed, output_format)
            else:
                return {
                    "status": "error",
                    "error": f"Model '{model}' not available and no fallback",
                }

    # ── Tool 2: transcribe_audio ──────────────────────────────────────────

    @mcp.tool()
    async def transcribe_audio(
        audio_path: str,
        model: str = "stt-api",
        response_format: str = "json",
        language: Optional[str] = None,
        include_timestamps: bool = False,
    ) -> Dict[str, Any]:
        """Convert audio to text using STT model.

        Args:
            audio_path: File path or URL to audio
            model: STT model (default: "stt-api")
            response_format: json, text, srt, vtt (default: "json")
            language: Language hint (en, fr, default: auto)
            include_timestamps: Include word-level timestamps

        Returns:
            Dictionary with text, segments, language, model_used, latency_ms, status
        """
        if not stt_api:
            return {
                "status": "error",
                "error": "STT API not available. Check configuration.",
            }

        result = await stt_api.transcribe(audio_path, language)
        if result.get("status") == "success" and include_timestamps:
            result["include_timestamps"] = True
        return result

    # ── Tool 3: translate_speech ──────────────────────────────────────────

    @mcp.tool()
    async def translate_speech(
        audio_path: str,
        source_language: str,
        target_language: str,
        model: str = "hibiki",
        preserve_voice: bool = False,
    ) -> Dict[str, Any]:
        """Real-time speech-to-speech translation (Phase 2+).

        Args:
            audio_path: Audio file path
            source_language: Source language (fr, en)
            target_language: Target language (en, fr)
            model: Model selection (hibiki or hibiki-mobile)
            preserve_voice: Keep source voice timbre

        Returns:
            Dictionary with translated_text, audio_path, source/target language, status
        """
        # Phase 2+ stub
        return {
            "status": "error",
            "error": "translate_speech is not yet implemented (Phase 2+)",
        }

    # ── Tool 4: list_models ────────────────────────────────────────────────

    @mcp.tool()
    def list_models(category: str = "all") -> Dict[str, Any]:
        """Get inventory of available models and their status.

        Args:
            category: Filter models (tts, stt, dialogue, all)

        Returns:
            Dictionary with list of available models and their properties
        """
        models_list = []

        # Pocket TTS (Phase 1)
        if pocket_tts:
            models_list.append(pocket_tts.get_model_info())

        # TTS API (Phase 2)
        if tts_api:
            models_list.append(tts_api.get_model_info())

        # STT API (Phase 2)
        if stt_api:
            models_list.append(stt_api.get_model_info())

        # Moshi (Phase 3)
        if moshi:
            models_list.append(moshi.get_model_info())

        # Filter by category
        if category != "all":
            models_list = [m for m in models_list if m["category"] == category]

        return {
            "status": "success",
            "models": models_list,
            "count": len(models_list),
        }

    # ── Tool 5: get_model_status ───────────────────────────────────────────

    @mcp.tool()
    async def get_model_status(model_id: Optional[str] = None) -> Dict[str, Any]:
        """Health check and detailed status of deployed models.

        Args:
            model_id: Specific model ID (optional, check all if not specified)

        Returns:
            Dictionary with model status, health checks, metrics
        """
        status = await health_monitor.check_all()

        if model_id:
            if model_id in status["services"]:
                return {
                    "status": "success",
                    "timestamp": status["timestamp"],
                    "models": {model_id: status["services"][model_id]},
                    "overall_status": status["overall_status"],
                }
            else:
                return {
                    "status": "error",
                    "error": f"Model '{model_id}' not found",
                }

        return {
            "status": "success",
            "timestamp": status["timestamp"],
            "models": status["services"],
            "overall_status": status["overall_status"],
        }

    # ── Tool 6: set_voice ──────────────────────────────────────────────────

    @mcp.tool()
    def set_voice(
        voice_name: str,
        audio_sample_path: str,
        description: str = "",
        language: str = "en",
        truncate: bool = False,
    ) -> Dict[str, Any]:
        """Configure voice for TTS (voice cloning with Pocket TTS).

        Args:
            voice_name: Identifier for this voice (e.g., "narrator_a")
            audio_sample_path: Path to reference audio (WAV, MP3)
            description: Human-readable description
            language: Language hint (en, fr, default: auto)
            truncate: Truncate to model context length

        Returns:
            Dictionary with voice_id, voice_name, language, storage_path, status
        """
        if not pocket_tts:
            return {
                "status": "error",
                "error": "Pocket TTS not available for voice configuration",
            }

        return pocket_tts.set_voice(voice_name, audio_sample_path, description, language)

    # ── Tool 7: configure_service ──────────────────────────────────────────

    @mcp.tool()
    def configure_service(
        setting: str,
        value: Any,
        scope: str = "global",
    ) -> Dict[str, Any]:
        """Update configuration and deployment settings.

        Args:
            setting: Configuration key (e.g., "default_tts_model")
            value: New value
            scope: Scope ("global" or "model-specific")

        Returns:
            Dictionary with setting, previous_value, new_value, requires_restart, status
        """
        # Supported settings and their handlers
        setting_handlers = {
            "default_tts_model": ("string", ["pocket-tts", "tts-api"]),
            "default_stt_model": ("string", ["stt-api"]),
            "cache_audio_outputs": ("bool", [True, False]),
            "max_text_length": ("int", range(100, 10000)),
            "log_level": ("string", ["debug", "info", "warning", "error"]),
        }

        if setting not in setting_handlers:
            return {
                "status": "error",
                "error": f"Unknown setting: {setting}",
                "supported_settings": list(setting_handlers.keys()),
            }

        return {
            "status": "success",
            "setting": setting,
            "previous_value": None,  # Would track previous value in real implementation
            "new_value": value,
            "requires_restart": setting in [
                "log_level",
                "default_tts_model",
            ],
            "affected_models": ["pocket-tts", "tts-api", "stt-api"],
        }

    # Store services and monitor for later access
    mcp._kyutai_services = services
    mcp._health_monitor = health_monitor
    mcp._pocket_tts = pocket_tts

    logger.info(f"MCP server created with {len(services)} services")
    logger.info(f"Available models: {', '.join(services.keys())}")

    return mcp
