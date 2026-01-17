"""
TTS Service - FastAPI wrapper for pocket-tts.

pocket-tts is Kyutai's lightweight (100M parameter) model that generates
high-fidelity, emotional speech by predicting continuous audio vectors
rather than discrete tokens.

This service:
1. Wraps pocket-tts in a FastAPI endpoint
2. Provides voice profile mapping
3. Runs on port 8081 for local integration
4. Generates audio faster than real-time on CPU
"""

import asyncio
import io
import logging
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VoiceProfile:
    """Configuration for a voice profile."""
    name: str
    style: str = "neutral"  # neutral, expressive, calm, energetic
    speed: float = 1.0
    pitch: float = 1.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "style": self.style,
            "speed": self.speed,
            "pitch": self.pitch,
        }


# Default voice profiles from pocket-tts
# Extended with agent personas from democratic_debate.py
VOICE_PROFILES = {
    # Base pocket-tts voices
    "azelma": VoiceProfile("Azelma", style="calm"),
    "marius": VoiceProfile("Marius", style="neutral"),
    "cosette": VoiceProfile("Cosette", style="expressive"),
    "valjean": VoiceProfile("Valjean", style="neutral", pitch=0.9),
    
    # Agent Personas - from DemocraticDebate
    # Aurora (Architect) - Visionary, systematic, calm
    "aurora": VoiceProfile("Aurora", style="calm", speed=0.95, pitch=1.05),
    
    # Marcus (Builder) - Practical, steady, grounded
    "marcus": VoiceProfile("Marcus", style="neutral", speed=1.0, pitch=0.95),
    
    # Helena (Guardian) - Vigilant, passionate about security
    "helena": VoiceProfile("Helena", style="expressive", speed=0.9, pitch=1.0),
    
    # Phoenix (Explorer) - Bold, creative, energetic
    "phoenix": VoiceProfile("Phoenix", style="expressive", speed=1.1, pitch=1.1),
    
    # Sage (Synthesizer) - Deep, diplomatic, integrative
    "sage": VoiceProfile("Sage", style="neutral", speed=0.85, pitch=0.85),
}


class TTSService:
    """
    Text-to-Speech service using pocket-tts.
    
    Provides high-quality speech synthesis with emotional control.
    Falls back to simpler TTS if pocket-tts is not available.
    """
    
    def __init__(
        self,
        model_path: Path | str | None = None,
        device: str = "cpu",
        default_voice: str = "azelma",
    ):
        """
        Initialize the TTS service.
        
        Args:
            model_path: Path to pocket-tts model weights
            device: Device to run on (cpu/cuda)
            default_voice: Default voice profile name
        """
        self.model_path = Path(model_path) if model_path else None
        self.device = device
        self.default_voice = default_voice
        
        self._model: Any = None
        self._available = False
        self._fallback_available = False
    
    async def initialize(self) -> bool:
        """
        Initialize the TTS model.
        
        Returns True if pocket-tts is available, False if using fallback.
        """
        # Try to import pocket-tts
        try:
            from pocket_tts import PocketTTS
            
            self._model = PocketTTS(
                model_path=str(self.model_path) if self.model_path else None,
                device=self.device,
            )
            self._available = True
            logger.info("pocket-tts initialized successfully")
            return True
            
        except ImportError:
            logger.warning(
                "pocket-tts not installed. "
                "Install with: pip install pocket-tts"
            )
        except Exception as e:
            logger.error(f"Failed to initialize pocket-tts: {e}")
        
        # Try fallback TTS
        try:
            import pyttsx3
            self._fallback_available = True
            logger.info("Using pyttsx3 fallback TTS")
        except ImportError:
            logger.warning("No TTS backend available")
        
        return False
    
    def get_voice_profile(self, voice_name: str) -> VoiceProfile:
        """Get a voice profile by name."""
        return VOICE_PROFILES.get(
            voice_name.lower(), 
            VOICE_PROFILES[self.default_voice]
        )
    
    async def synthesize(
        self,
        text: str,
        voice: str = "azelma",
        output_path: Path | str | None = None,
        style: str | None = None,
        speed: float | None = None,
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to speak
            voice: Voice profile name
            output_path: Optional path to save WAV file
            style: Override voice style
            speed: Override speaking speed
            
        Returns:
            WAV audio bytes
        """
        profile = self.get_voice_profile(voice)
        
        if style:
            profile.style = style
        if speed:
            profile.speed = speed
        
        if self._available and self._model:
            return await self._synthesize_pocket(text, profile, output_path)
        elif self._fallback_available:
            return await self._synthesize_fallback(text, profile, output_path)
        else:
            return self._generate_silent_audio()
    
    async def _synthesize_pocket(
        self,
        text: str,
        profile: VoiceProfile,
        output_path: Path | str | None,
    ) -> bytes:
        """Synthesize using pocket-tts."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(
                None,
                lambda: self._model.synthesize(
                    text,
                    voice=profile.name,
                    style=profile.style,
                    speed=profile.speed,
                ),
            )
            
            # Convert to WAV bytes
            wav_bytes = self._audio_to_wav(audio)
            
            if output_path:
                Path(output_path).write_bytes(wav_bytes)
            
            return wav_bytes
            
        except Exception as e:
            logger.error(f"pocket-tts synthesis failed: {e}")
            return self._generate_silent_audio()
    
    async def _synthesize_fallback(
        self,
        text: str,
        profile: VoiceProfile,
        output_path: Path | str | None,
    ) -> bytes:
        """Synthesize using pyttsx3 fallback."""
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            engine.setProperty('rate', int(150 * profile.speed))
            
            # Save to temp file
            temp_path = Path(output_path) if output_path else Path("/tmp/tts_output.wav")
            engine.save_to_file(text, str(temp_path))
            engine.runAndWait()
            
            wav_bytes = temp_path.read_bytes()
            
            if not output_path:
                temp_path.unlink(missing_ok=True)
            
            return wav_bytes
            
        except Exception as e:
            logger.error(f"Fallback TTS failed: {e}")
            return self._generate_silent_audio()
    
    def _audio_to_wav(
        self,
        audio_data: Any,
        sample_rate: int = 24000,
    ) -> bytes:
        """Convert audio array to WAV bytes."""
        import numpy as np
        
        if hasattr(audio_data, 'numpy'):
            audio_data = audio_data.numpy()
        
        # Normalize to int16
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data.tobytes())
        
        return buffer.getvalue()
    
    def _generate_silent_audio(
        self,
        duration_ms: int = 100,
        sample_rate: int = 24000,
    ) -> bytes:
        """Generate silent audio placeholder."""
        import numpy as np
        
        samples = int(sample_rate * duration_ms / 1000)
        silent = np.zeros(samples, dtype=np.int16)
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(silent.tobytes())
        
        return buffer.getvalue()
    
    @property
    def is_available(self) -> bool:
        """Check if TTS is available."""
        return self._available or self._fallback_available


# FastAPI app for running as a service
def create_app() -> Any:
    """Create FastAPI app for TTS service."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import Response
        from pydantic import BaseModel
    except ImportError:
        logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
        return None
    
    app = FastAPI(
        title="Cohezion TTS Service",
        description="pocket-tts wrapper for speech synthesis",
        version="0.1.0",
    )
    
    tts = TTSService()
    
    class SynthesizeRequest(BaseModel):
        text: str
        voice: str = "azelma"
        style: str | None = None
        speed: float | None = None
    
    @app.on_event("startup")
    async def startup():
        await tts.initialize()
    
    @app.post("/synthesize")
    async def synthesize(request: SynthesizeRequest) -> Response:
        """Synthesize speech from text."""
        audio = await tts.synthesize(
            text=request.text,
            voice=request.voice,
            style=request.style,
            speed=request.speed,
        )
        return Response(content=audio, media_type="audio/wav")
    
    @app.get("/voices")
    async def list_voices() -> dict[str, Any]:
        """List available voice profiles."""
        return {
            "voices": {
                name: profile.to_dict() 
                for name, profile in VOICE_PROFILES.items()
            }
        }
    
    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "tts_available": tts.is_available,
        }
    
    return app


if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    if app:
        uvicorn.run(app, host="0.0.0.0", port=8081)
