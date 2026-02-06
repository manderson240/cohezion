#!/usr/bin/env python3
"""
COHEZION Pocket TTS Integration Module
Complete integration of Kyutai Pocket TTS with COHEZION ecosystem
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    """Configuration for Pocket TTS integration"""

    model_path: str | None = None
    default_voice: str = "alba"
    sample_rate: int = 24000
    output_format: str = "wav"
    cache_size: int = 100
    enable_streaming: bool = True


class PocketTTSManager:
    """Elite TTS management using Kyutai Pocket TTS"""

    def __init__(self, config: TTSConfig | None = None):
        self.config = config or TTSConfig()
        self.model = None
        self.voice_cache = {}
        self.performance_stats = {
            "total_generations": 0,
            "average_latency_ms": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    async def initialize(self) -> bool:
        """Initialize Pocket TTS model"""
        try:
            # Check if pocket-tts is installed
            try:
                import pocket_tts
                import scipy.io.wavfile
                import torch

                logger.info("✅ Pocket TTS dependencies available")
            except ImportError as e:
                logger.error(f"❌ Pocket TTS not available: {e}")
                logger.info("Install with: pip install pocket-tts")
                return False

            # Load model
            self.model = pocket_tts.TTSModel.load_model()
            logger.info("✅ Pocket TTS model loaded successfully")

            # Pre-load default voice
            await self._preload_voice(self.config.default_voice)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Pocket TTS: {e}")
            return False

    async def _preload_voice(self, voice: str) -> bool:
        """Pre-load voice state for caching"""
        try:
            if voice not in self.voice_cache:
                voice_state = self.model.get_state_for_audio_prompt(voice)
                self.voice_cache[voice] = voice_state
                logger.info(f"✅ Pre-loaded voice: {voice}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to preload voice {voice}: {e}")
            return False

    async def generate_speech(
        self,
        text: str,
        voice: str | None = None,
        output_path: str | None = None,
        speed: float = 1.0,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Generate speech from text using Pocket TTS"""

        if not self.model:
            return {"success": False, "error": "Model not initialized"}

        try:
            # Use default voice if not specified
            voice = voice or self.config.default_voice

            # Generate output path if not provided
            if not output_path:
                output_path = f"/tmp/pocket_tts_{len(text)}_{hash(text) % 10000}.wav"

            # Check cache first
            cache_key = f"{voice}_{hash(text)}" if use_cache else None
            if cache_key and cache_key in getattr(self, "_audio_cache", {}):
                self.performance_stats["cache_hits"] += 1
                cached_audio = self._audio_cache[cache_key]
                import scipy.io.wavfile

                scipy.io.wavfile.write(
                    output_path, self.config.sample_rate, cached_audio.numpy()
                )

                return {
                    "success": True,
                    "output_path": output_path,
                    "voice": voice,
                    "duration": len(cached_audio) / self.config.sample_rate,
                    "cached": True,
                }

            self.performance_stats["cache_misses"] += 1

            # Get or load voice state
            if voice not in self.voice_cache:
                if not await self._preload_voice(voice):
                    return {"success": False, "error": f"Failed to load voice: {voice}"}

            voice_state = self.voice_cache[voice]

            # Generate audio
            import time

            start_time = time.time()

            audio = self.model.generate_audio(voice_state, text)

            generation_time = (time.time() - start_time) * 1000  # Convert to ms

            # Save audio
            import scipy.io.wavfile

            scipy.io.wavfile.write(output_path, self.config.sample_rate, audio.numpy())

            # Cache the result
            if not hasattr(self, "_audio_cache"):
                self._audio_cache = {}
            if cache_key and len(self._audio_cache) < self.config.cache_size:
                self._audio_cache[cache_key] = audio

            # Update performance stats
            self.performance_stats["total_generations"] += 1
            self._update_latency_stats(generation_time)

            duration = len(audio) / self.config.sample_rate
            file_size = os.path.getsize(output_path)

            return {
                "success": True,
                "output_path": output_path,
                "voice": voice,
                "duration": duration,
                "file_size_bytes": file_size,
                "generation_time_ms": generation_time,
                "real_time_factor": duration / (len(text.split()) * 0.5)
                if text.split()
                else 0,
                "cached": False,
            }

        except Exception as e:
            logger.error(f"❌ Speech generation failed: {e}")
            return {"success": False, "error": str(e)}

    def _update_latency_stats(self, latency_ms: float):
        """Update average latency statistics"""
        total = self.performance_stats["total_generations"]
        current_avg = self.performance_stats["average_latency_ms"]

        if total == 1:
            self.performance_stats["average_latency_ms"] = latency_ms
        else:
            # Rolling average
            self.performance_stats["average_latency_ms"] = (
                current_avg * (total - 1) + latency_ms
            ) / total

    async def get_available_voices(self) -> list[str]:
        """Get list of available voices"""
        voices = [
            "alba",
            "marius",
            "javert",
            "jean",
            "fantine",
            "cosette",
            "eponine",
            "azelma",
        ]
        return voices

    async def clone_voice(self, audio_path: str) -> dict[str, Any]:
        """Clone voice from audio sample"""
        try:
            if not self.model:
                return {"success": False, "error": "Model not initialized"}

            if not os.path.exists(audio_path):
                return {
                    "success": False,
                    "error": f"Audio file not found: {audio_path}",
                }

            # Generate voice state from audio
            voice_state = self.model.get_state_for_audio_prompt(audio_path)

            # Cache the cloned voice
            voice_name = f"cloned_{os.path.basename(audio_path)}"
            self.voice_cache[voice_name] = voice_state

            return {
                "success": True,
                "voice_name": voice_name,
                "message": f"Voice cloned successfully as: {voice_name}",
            }

        except Exception as e:
            logger.error(f"❌ Voice cloning failed: {e}")
            return {"success": False, "error": str(e)}

    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics"""
        stats = self.performance_stats.copy()

        if stats["total_generations"] > 0:
            stats["cache_hit_rate"] = (
                stats["cache_hits"]
                / (stats["cache_hits"] + stats["cache_misses"])
                * 100
            )
        else:
            stats["cache_hit_rate"] = 0

        stats["voices_cached"] = len(self.voice_cache)
        stats["model_loaded"] = self.model is not None

        return stats

    async def benchmark_performance(self, test_texts: list[str]) -> dict[str, Any]:
        """Benchmark TTS performance"""
        if not self.model:
            return {"success": False, "error": "Model not initialized"}

        results = {
            "total_tests": len(test_texts),
            "successful_generations": 0,
            "total_generation_time_ms": 0,
            "average_latency_ms": 0,
            "min_latency_ms": float("inf"),
            "max_latency_ms": 0,
            "total_audio_duration": 0,
            "average_real_time_factor": 0,
        }

        for text in test_texts:
            try:
                import time

                start_time = time.time()

                # Generate speech
                audio = self.model.generate_audio(
                    self.voice_cache[self.config.default_voice], text
                )

                generation_time = (time.time() - start_time) * 1000
                duration = len(audio) / self.config.sample_rate

                results["successful_generations"] += 1
                results["total_generation_time_ms"] += generation_time
                results["total_audio_duration"] += duration
                results["min_latency_ms"] = min(
                    results["min_latency_ms"], generation_time
                )
                results["max_latency_ms"] = max(
                    results["max_latency_ms"], generation_time
                )

            except Exception as e:
                logger.error(f"Benchmark test failed: {e}")

        if results["successful_generations"] > 0:
            results["average_latency_ms"] = (
                results["total_generation_time_ms"] / results["successful_generations"]
            )
            if results["total_audio_duration"] > 0:
                results["average_real_time_factor"] = results[
                    "total_audio_duration"
                ] / (results["total_generation_time_ms"] / 1000)

        if results["min_latency_ms"] == float("inf"):
            results["min_latency_ms"] = 0

        return results


class TTSToolIntegration:
    """Integration of TTS with COHEZION tool ecosystem"""

    def __init__(self, tts_manager: PocketTTSManager):
        self.tts = tts_manager

    async def voice_code_review(self, code: str, review_text: str) -> dict[str, Any]:
        """Generate voice-over for code review"""
        try:
            # Prepare review text
            voice_text = f"Code Review. {review_text}"

            # Generate speech
            result = await self.tts.generate_speech(
                text=voice_text,
                voice="jean",  # Professional voice
                speed=0.9,  # Slightly slower for clarity
            )

            if result["success"]:
                result["context"] = "voice_code_review"
                result["code_lines"] = len(code.split("\n"))

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def accessibility_narration(
        self, content: str, content_type: str = "text"
    ) -> dict[str, Any]:
        """Generate narration for accessibility"""
        try:
            # Prepare accessibility-friendly text
            if content_type == "code":
                narration = f"Code content. {content}"
            elif content_type == "table":
                narration = f"Table data. {content}"
            else:
                narration = content

            result = await self.tts.generate_speech(
                text=narration,
                voice="alba",  # Clear voice
                speed=1.0,
            )

            if result["success"]:
                result["context"] = "accessibility"
                result["content_type"] = content_type

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def multilingual_translation(
        self, text: str, target_language: str = "en"
    ) -> dict[str, Any]:
        """Generate speech in different languages (future enhancement)"""
        # Note: Pocket TTS currently supports English only
        # This is a placeholder for future multilingual capabilities

        return {
            "success": False,
            "error": f"Multilingual support not yet available. Pocket TTS currently supports English only. Requested language: {target_language}",
        }


# Initialize global TTS manager
_tts_manager = None
_tts_integration = None


async def get_tts_manager() -> PocketTTSManager:
    """Get or initialize TTS manager"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = PocketTTSManager()
        await _tts_manager.initialize()
    return _tts_manager


async def get_tts_integration() -> TTSToolIntegration:
    """Get or initialize TTS tool integration"""
    global _tts_integration
    if _tts_integration is None:
        tts_manager = await get_tts_manager()
        _tts_integration = TTSToolIntegration(tts_manager)
    return _tts_integration


# Performance comparison function
def get_tts_performance_comparison() -> dict[str, Any]:
    """Get performance comparison with other TTS solutions"""
    return {
        "pocket_tts": {
            "model_size_mb": 400,
            "latency_ms": 200,
            "real_time_factor": "6x",
            "cpu_cores": 2,
            "gpu_required": False,
            "voice_cloning": True,
            "cost": "free",
            "license": "MIT",
        },
        "elevenlabs": {
            "model_size_mb": "cloud",
            "latency_ms": 300,
            "real_time_factor": "1x",
            "cpu_cores": "cloud",
            "gpu_required": False,
            "voice_cloning": True,
            "cost": "$1-5 per 1k chars",
            "license": "proprietary",
        },
        "openai_tts": {
            "model_size_mb": "cloud",
            "latency_ms": 250,
            "real_time_factor": "1x",
            "cpu_cores": "cloud",
            "gpu_required": False,
            "voice_cloning": False,
            "cost": "$15 per 1M chars",
            "license": "proprietary",
        },
    }
