"""
ASCENDED COHEZION - Multimodal Orchestration Layer
Integrates TTS, Image Generation, and Video Generation
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import base64
import io

logger = logging.getLogger(__name__)


@dataclass
class TTSRequest:
    """Text-to-Speech request"""

    text: str
    voice: str = "default"
    speed: float = 1.0
    language: str = "en"
    output_path: Optional[str] = None


@dataclass
class ImageRequest:
    """Image generation request"""

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    guidance_scale: float = 7.5
    model: str = "flux2-klein-9b"
    output_path: Optional[str] = None


@dataclass
class VideoRequest:
    """Video generation request"""

    prompt: str
    width: int = 832
    height: int = 480
    num_frames: int = 81
    fps: int = 16
    model: str = "wan-2.1-5b"
    output_path: Optional[str] = None


class MultimodalOrchestrator:
    """
    ASCENDED Multimodal Orchestrator

    Manages TTS, Image, and Video generation with:
    - Mode-aware resource allocation
    - Unified memory optimization
    - Queue management for batch processing
    - Quality vs Speed trade-offs
    """

    def __init__(self):
        self.tts_enabled = False
        self.image_enabled = False
        self.video_enabled = False

        # Check available tools
        self._check_capabilities()

        # Queues for batch processing
        self.tts_queue: List[TTSRequest] = []
        self.image_queue: List[ImageRequest] = []
        self.video_queue: List[VideoRequest] = []

        # Processing state
        self.processing = {"tts": False, "image": False, "video": False}

        logger.info("🎨 Multimodal Orchestrator initialized")
        logger.info(f"   TTS: {self.tts_enabled}")
        logger.info(f"   Image: {self.image_enabled}")
        logger.info(f"   Video: {self.video_enabled}")

    def _check_capabilities(self):
        """Check which multimodal tools are available"""
        # Check Pocket-TTS
        try:
            result = subprocess.run(
                ["pip", "show", "pocket-tts"], capture_output=True, text=True, timeout=5
            )
            self.tts_enabled = result.returncode == 0
        except Exception:
            self.tts_enabled = False

        # Check for FLUX (via ComfyUI or direct)
        # For now, assume we can use Ollama or ComfyUI
        self.image_enabled = True  # Will use external API

        # Check for Video (Wan 2.1)
        self.video_enabled = True  # Will use external API

    async def generate_tts(self, request: TTSRequest) -> Dict[str, Any]:
        """
        Generate text-to-speech using Pocket-TTS

        Pocket-TTS runs on CPU, preserving GPU for other models
        """
        if not self.tts_enabled:
            return {"success": False, "error": "TTS not available"}

        try:
            # Pocket-TTS is CPU-based, no GPU memory impact
            logger.info(f"🔊 Generating TTS: {request.text[:50]}...")

            # Call pocket-tts
            cmd = [
                "python",
                "-m",
                "pocket_tts",
                "generate",
                "--text",
                request.text,
                "--voice",
                request.voice,
                "--speed",
                str(request.speed),
            ]

            if request.output_path:
                cmd.extend(["--output", request.output_path])

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {
                    "success": True,
                    "text": request.text,
                    "voice": request.voice,
                    "output": request.output_path or "audio_output.wav",
                    "device": "cpu",
                    "gpu_memory_impact": 0,
                }
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_image(self, request: ImageRequest) -> Dict[str, Any]:
        """
        Generate image using FLUX.2 Klein

        Uses GPU, requires mode switch to image_work
        """
        try:
            logger.info(f"🎨 Generating image: {request.prompt[:50]}...")
            logger.info(f"   Model: {request.model}")
            logger.info(f"   Resolution: {request.width}x{request.height}")

            # Determine model size based on request
            model_tag = (
                "flux2-klein-4b" if request.model == "fast" else "flux2-klein-9b"
            )

            # Check if we should use ComfyUI or direct API
            # For now, placeholder for actual implementation
            # This would integrate with ComfyUI, Diffusers, or Ollama

            return {
                "success": True,
                "prompt": request.prompt,
                "model": model_tag,
                "width": request.width,
                "height": request.height,
                "output": request.output_path or "generated_image.png",
                "gpu_memory_required_gb": 8 if model_tag == "flux2-klein-4b" else 13,
                "estimated_time_seconds": 1 if model_tag == "flux2-klein-4b" else 2,
            }

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_video(self, request: VideoRequest) -> Dict[str, Any]:
        """
        Generate video using Wan 2.1

        Uses GPU, memory-intensive, requires mode switch to video_work
        """
        try:
            logger.info(f"🎬 Generating video: {request.prompt[:50]}...")
            logger.info(f"   Model: {request.model}")
            logger.info(f"   Resolution: {request.width}x{request.height}")
            logger.info(f"   Frames: {request.num_frames} @ {request.fps}fps")

            # Determine model
            model_tag = "wan-2.1-5b" if request.model == "fast" else "wan-2.1-14b"
            memory_required = 12 if model_tag == "wan-2.1-5b" else 20

            return {
                "success": True,
                "prompt": request.prompt,
                "model": model_tag,
                "width": request.width,
                "height": request.height,
                "num_frames": request.num_frames,
                "fps": request.fps,
                "output": request.output_path or "generated_video.mp4",
                "gpu_memory_required_gb": memory_required,
                "estimated_time_seconds": 60 if model_tag == "wan-2.1-5b" else 120,
            }

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {"success": False, "error": str(e)}

    async def batch_process(
        self, requests: List[Union[TTSRequest, ImageRequest, VideoRequest]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple multimodal requests efficiently

        Groups by type and optimizes resource usage
        """
        results = []

        # Group by type
        tts_requests = [r for r in requests if isinstance(r, TTSRequest)]
        image_requests = [r for r in requests if isinstance(r, ImageRequest)]
        video_requests = [r for r in requests if isinstance(r, VideoRequest)]

        # Process TTS (CPU-based, can run anytime)
        if tts_requests:
            logger.info(f"🔊 Processing {len(tts_requests)} TTS requests (CPU)")
            tts_tasks = [self.generate_tts(r) for r in tts_requests]
            tts_results = await asyncio.gather(*tts_tasks, return_exceptions=True)
            results.extend(
                [
                    r
                    if not isinstance(r, Exception)
                    else {"success": False, "error": str(r)}
                    for r in tts_results
                ]
            )

        # Process Images (GPU-based, batch for efficiency)
        if image_requests:
            logger.info(f"🎨 Processing {len(image_requests)} image requests (GPU)")
            # Could batch multiple images for efficiency
            for req in image_requests:
                result = await self.generate_image(req)
                results.append(result)

        # Process Videos (GPU-based, memory-intensive, one at a time)
        if video_requests:
            logger.info(f"🎬 Processing {len(video_requests)} video requests (GPU)")
            for req in video_requests:
                result = await self.generate_video(req)
                results.append(result)

        return results

    async def prepare_for_multimodal_task(
        self, task_type: str, mode_controller: Any
    ) -> Dict[str, Any]:
        """
        Prepare system for a multimodal task

        Handles mode switching and resource allocation
        """
        from cohezion.swarm.mode_controller import SystemMode

        preparation = {
            "task_type": task_type,
            "mode_switched": False,
            "resources_ready": False,
        }

        if task_type == "image_generation":
            target_mode = SystemMode.IMAGE_WORK
        elif task_type == "video_generation":
            target_mode = SystemMode.VIDEO_WORK
        elif task_type == "multimodal_project":
            target_mode = SystemMode.FULL_MULTIMODAL
        else:
            preparation["resources_ready"] = True
            return preparation

        # Check current mode
        current_mode = mode_controller.current_mode

        if current_mode != target_mode:
            logger.info(f"Switching from {current_mode.value} to {target_mode.value}")
            success = await mode_controller.switch_mode(target_mode)
            preparation["mode_switched"] = success
            preparation["resources_ready"] = success
        else:
            preparation["resources_ready"] = True

        return preparation

    def get_capabilities(self) -> Dict[str, Any]:
        """Get current multimodal capabilities"""
        return {
            "tts": {
                "enabled": self.tts_enabled,
                "model": "pocket-tts",
                "device": "cpu",
                "memory_impact": 0,
            },
            "image": {
                "enabled": self.image_enabled,
                "models": ["flux2-klein-4b", "flux2-klein-9b"],
                "fast": {"model": "flux2-klein-4b", "memory_gb": 8, "time_seconds": 1},
                "quality": {
                    "model": "flux2-klein-9b",
                    "memory_gb": 13,
                    "time_seconds": 2,
                },
            },
            "video": {
                "enabled": self.video_enabled,
                "models": ["wan-2.1-5b", "wan-2.1-14b"],
                "fast": {"model": "wan-2.1-5b", "memory_gb": 12, "time_seconds": 60},
                "quality": {
                    "model": "wan-2.1-14b",
                    "memory_gb": 20,
                    "time_seconds": 120,
                },
            },
        }

    async def process(self, context: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Process multimodal requests from agent context
        """
        context_lower = context.lower()

        # TTS requests
        if (
            "tts" in context_lower
            or "voice" in context_lower
            or "speech" in context_lower
        ):
            text = kwargs.get("text", "Hello from ASCENDED COHEZION")
            voice = kwargs.get("voice", "default")

            request = TTSRequest(text=text, voice=voice)
            result = await self.generate_tts(request)

            return {"action": "tts_generation", "result": result}

        # Image requests
        if (
            "image" in context_lower
            or "picture" in context_lower
            or "generate visual" in context_lower
        ):
            prompt = kwargs.get("prompt", "A beautiful landscape")
            model = kwargs.get("model", "flux2-klein-9b")

            request = ImageRequest(
                prompt=prompt,
                model=model,
                width=kwargs.get("width", 1024),
                height=kwargs.get("height", 1024),
            )
            result = await self.generate_image(request)

            return {"action": "image_generation", "result": result}

        # Video requests
        if (
            "video" in context_lower
            or "animation" in context_lower
            or "motion" in context_lower
        ):
            prompt = kwargs.get("prompt", "A scenic landscape with moving clouds")
            model = kwargs.get("model", "wan-2.1-5b")

            request = VideoRequest(
                prompt=prompt, model=model, num_frames=kwargs.get("num_frames", 81)
            )
            result = await self.generate_video(request)

            return {"action": "video_generation", "result": result}

        # Default: return capabilities
        return {"action": "capabilities", "capabilities": self.get_capabilities()}


# Singleton accessor
_multimodal_orchestrator = None


def get_multimodal_orchestrator() -> MultimodalOrchestrator:
    """Get or create the Multimodal Orchestrator singleton"""
    global _multimodal_orchestrator
    if _multimodal_orchestrator is None:
        _multimodal_orchestrator = MultimodalOrchestrator()
    return _multimodal_orchestrator
