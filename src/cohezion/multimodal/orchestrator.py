r"""Cohezion Unified Multimodal Orchestrator
===========================================
Integrates Text, Vision, Audio, 3D Mesh, Music, and Image models
across local NPU, iGPU, and CPU silicon on Strix Halo 128GB Unified Memory.

Model Routing Matrix:
  - Text & Deep Reasoning : `qwen3.6-moe-35b-a3b-FLM` (NPU MoE, pinned=true)
  - Vision & Image QA     : `qwen3vl-it-4b-FLM` (NPU Vision) / `STEP3-VL-10B`
  - Audio & Speech        : `gemma4-it-e2b-FLM` (NPU Audio) / `Whisper-Large-v3-Turbo` / `kokoro-v1`
  - Image Generation      : `Flux-2-Klein-9B-GGUF` / `SD-Turbo` / NanoBanana MCP
  - 3D Spatial & Mesh     : `TRELLIS-3D` / `RealESRGAN-x4plus`
  - Music & Sonification  : `ACE-Step-Music` / `LyricaLlama`
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Any

from cohezion.reliability.oom_guard import OOMGuard

logger = logging.getLogger(__name__)


class MultimodalModality(enum.Enum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    IMAGE_GEN = "image_gen"
    MESH_3D = "mesh_3d"
    MUSIC = "music"


@dataclass(frozen=True, slots=True)
class MultimodalModelEntry:
    modality: MultimodalModality
    model_id: str
    hardware_lane: str  # "NPU", "iGPU", "CPU"
    supports_zero_copy: bool = True


class UnifiedMultimodalOrchestrator:
    """Orchestrates local multimodal model dispatching with OOM headroom guards."""

    ROSTER: dict[MultimodalModality, list[MultimodalModelEntry]] = {
        MultimodalModality.TEXT: [
            MultimodalModelEntry(MultimodalModality.TEXT, "qwen3.6-moe-35b-a3b-FLM", "NPU"),
            MultimodalModelEntry(MultimodalModality.TEXT, "Qwen3-Coder-30B-A3B-Instruct-GGUF", "iGPU"),
        ],
        MultimodalModality.VISION: [
            MultimodalModelEntry(MultimodalModality.VISION, "qwen3vl-it-4b-FLM", "NPU"),
            MultimodalModelEntry(MultimodalModality.VISION, "gemma4-it-e2b-FLM", "NPU"),
        ],
        MultimodalModality.AUDIO: [
            MultimodalModelEntry(MultimodalModality.AUDIO, "gemma4-it-e2b-FLM", "NPU"),
            MultimodalModelEntry(MultimodalModality.AUDIO, "Whisper-Large-v3-Turbo", "iGPU"),
            MultimodalModelEntry(MultimodalModality.AUDIO, "kokoro-v1", "CPU"),
        ],
        MultimodalModality.IMAGE_GEN: [
            MultimodalModelEntry(MultimodalModality.IMAGE_GEN, "Flux-2-Klein-9B-GGUF", "iGPU"),
            MultimodalModelEntry(MultimodalModality.IMAGE_GEN, "SD-Turbo", "iGPU"),
        ],
        MultimodalModality.MESH_3D: [
            MultimodalModelEntry(MultimodalModality.MESH_3D, "TRELLIS-3D", "iGPU"),
            MultimodalModelEntry(MultimodalModality.MESH_3D, "RealESRGAN-x4plus", "iGPU"),
        ],
        MultimodalModality.MUSIC: [
            MultimodalModelEntry(MultimodalModality.MUSIC, "ACE-Step-Music", "iGPU"),
            MultimodalModelEntry(MultimodalModality.MUSIC, "LyricaLlama-Q8_0-GGUF-Q8_0", "iGPU"),
        ],
    }

    @classmethod
    def resolve_model(cls, modality: MultimodalModality, prefer_npu: bool = True) -> MultimodalModelEntry:
        """Resolve the optimal local model entry for a given modality."""
        candidates = cls.ROSTER.get(modality, [])
        if not candidates:
            raise ValueError(f"No local model candidates registered for modality: {modality}")

        if prefer_npu:
            for entry in candidates:
                if entry.hardware_lane == "NPU":
                    return entry

        return candidates[0]

    @classmethod
    def check_preflight_safety(cls) -> tuple[bool, str]:
        """Verify memory state before launching multimodal pipeline."""
        state = OOMGuard.get_memory_state()
        if not state.is_safe:
            return (
                False,
                f"Memory headroom insufficient ({state.available_gb} GiB < {OOMGuard.MIN_AVAILABLE_GB} GiB floor)",
            )
        return (True, f"Safe: {state.available_gb} GiB available")
