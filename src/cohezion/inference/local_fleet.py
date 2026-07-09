"""OmniFleet — role assignment overlay on the Lemonade OmniRouter registry.

We maintain only what Lemonade doesn't track:
  - Role assignments (which model serves which capability)
  - NPU membership (FLM-backend models on XDNA2)
  - TPS estimates (empirically measured on Strix Halo)

All other metadata (size, ctx_size, has_vision) is sourced live from
the Lemonade OmniRouter registry at :13305/api/v1/models.

Inject ``registry=[...]`` into ``LocalResearchFleet`` in tests to avoid
making HTTP calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)

OMNI_URL = "http://localhost:13305/api/v1"
RAM_CEILING_GB: float = 96.0
RAM_EFFECTIVE_GB: float = 88.0  # N3 guard: 8 GB headroom


class FleetRole(str, Enum):
    # Always-on lightweight (≤2 GB)
    ROUTER = "router"
    TRIAGE = "triage"
    SYNTHESIS = "synthesis"
    SKILL = "skill"
    EMBED = "embed"
    TRANSCRIBE = "transcribe"
    TTS = "tts"
    UPSCALE = "upscale"
    # Mid-tier (4–6 GB)
    GENERATION = "generation"
    NPU_THINK = "npu_think"
    REASONING = "reasoning"
    VISION_FAST = "vision_fast"
    IMAGE_FAST = "image_fast"
    # Large (18–24 GB, hot-swap required)
    CODE = "code"
    THINKING_CODE = "thinking_code"
    VISION = "vision"
    DEEP_SYNTHESIS = "deep_synthesis"
    IMAGE_GEN = "image_gen"
    TOOL_CALL = "tool_call"


@dataclass(frozen=True)
class FleetModel:
    """Static role assignment + performance data for a Lemonade model.

    Size, ctx_size, and vision capability are NOT stored here — query
    the live Lemonade registry via ``LocalResearchFleet`` for those.
    """
    model_id: str
    role: FleetRole
    tps_estimate: float       # tokens/sec on Strix Halo (0 = non-LLM)
    is_npu: bool = False      # XDNA2 NPU via FLM backend


# Role → model assignment + empirical performance.
# This is the ONLY place in the codebase that duplicates Lemonade data.
_FLEET: dict[FleetRole, FleetModel] = {
    FleetRole.ROUTER:         FleetModel("llama3.2-1b-FLM",                    FleetRole.ROUTER,         42.0,  is_npu=True),
    FleetRole.TRIAGE:         FleetModel("Qwen3-0.6B-GGUF",                    FleetRole.TRIAGE,         80.0),
    FleetRole.SYNTHESIS:      FleetModel("Bonsai-4B-gguf",                     FleetRole.SYNTHESIS,      90.0),
    FleetRole.SKILL:          FleetModel("Bonsai-8B-gguf",                     FleetRole.SKILL,          60.0),
    FleetRole.EMBED:          FleetModel("nomic-embed-text-v2-moe-GGUF",       FleetRole.EMBED,         200.0),
    FleetRole.TRANSCRIBE:     FleetModel("Whisper-Large-v3-Turbo",             FleetRole.TRANSCRIBE,      0.0, is_npu=True),
    FleetRole.TTS:            FleetModel("kokoro-v1",                          FleetRole.TTS,             0.0),
    FleetRole.UPSCALE:        FleetModel("RealESRGAN-x4plus",                  FleetRole.UPSCALE,         0.0),
    FleetRole.GENERATION:     FleetModel("Gemma-4-E4B-it-GGUF",               FleetRole.GENERATION,     54.0),
    FleetRole.NPU_THINK:      FleetModel("deepseek-r1-0528-8b-FLM",           FleetRole.NPU_THINK,      10.6, is_npu=True),
    FleetRole.REASONING:      FleetModel("DeepSeek-Qwen3-8B-GGUF",            FleetRole.REASONING,      41.0),
    FleetRole.VISION_FAST:    FleetModel("Gemma-4-E2B-it-GGUF",               FleetRole.VISION_FAST,    60.0),
    FleetRole.IMAGE_FAST:     FleetModel("SD-Turbo",                           FleetRole.IMAGE_FAST,      0.0),
    FleetRole.CODE:           FleetModel("Qwen3-Coder-30B-A3B-Instruct-GGUF", FleetRole.CODE,           12.0),
    FleetRole.THINKING_CODE:  FleetModel("Qwen3.6-35B-A3B-ThinkingCoder",     FleetRole.THINKING_CODE,   8.0),
    FleetRole.VISION:         FleetModel("Gemma-4-31B-it-GGUF",               FleetRole.VISION,          6.0),
    FleetRole.DEEP_SYNTHESIS: FleetModel("Gemma-4-26B-A4B-it-GGUF",          FleetRole.DEEP_SYNTHESIS, 43.0),
    FleetRole.IMAGE_GEN:      FleetModel("Flux-2-Klein-9B-GGUF",              FleetRole.IMAGE_GEN,       0.0),
    FleetRole.TOOL_CALL:      FleetModel("Nemotron-3-Nano-30B-A3B-GGUF",      FleetRole.TOOL_CALL,       5.0),
}

# task_classifier output_type → FleetRole
_TYPE_TO_ROLE: dict[str, FleetRole] = {
    "short_categorical": FleetRole.ROUTER,
    "short_answer":      FleetRole.ROUTER,
    "medium_generation": FleetRole.GENERATION,
    "long_generation":   FleetRole.GENERATION,
    "code":              FleetRole.CODE,
    "math_reasoning":    FleetRole.CODE,
    "reasoning":         FleetRole.REASONING,
    "embed":             FleetRole.EMBED,
    "tts":               FleetRole.TTS,
    "image":             FleetRole.IMAGE_GEN,
    "transcribe":        FleetRole.TRANSCRIBE,
}


def _fetch_registry(registry: list[dict] | None) -> dict[str, dict]:
    """Return Lemonade model registry keyed by model_id.

    Args:
        registry: pre-loaded list for testing.  If None, fetches live from :13305.
    """
    if registry is not None:
        return {m["id"]: m for m in registry}
    try:
        import httpx
        r = httpx.get(f"{OMNI_URL}/models", timeout=5.0)
        r.raise_for_status()
        return {m["id"]: m for m in r.json().get("data", [])}
    except Exception as exc:
        logger.debug("local_fleet: Lemonade registry unavailable (%s)", exc)
        return {}


class LocalResearchFleet:
    """Route tasks to the right Lemonade model by role.

    Metadata (size, ctx_size, vision capability) comes from the live Lemonade
    registry.  Pass ``registry=[...]`` in tests to avoid HTTP calls.
    """

    def __init__(self, registry: list[dict] | None = None) -> None:
        self._reg: dict[str, dict] | None = (
            {m["id"]: m for m in registry} if registry is not None else None
        )

    # ── Internal ──────────────────────────────────────────────────────────

    def _registry(self) -> dict[str, dict]:
        if self._reg is None:
            self._reg = _fetch_registry(None)
        return self._reg

    def _info(self, model_id: str) -> dict[str, Any]:
        return self._registry().get(model_id, {})

    # ── Role-based access ─────────────────────────────────────────────────

    def get(self, role: FleetRole) -> FleetModel:
        return _FLEET[role]

    def route(self, task_type: str) -> FleetModel:
        """Return the FleetModel for a given task_classifier output_type."""
        role = _TYPE_TO_ROLE.get(task_type, FleetRole.GENERATION)
        return _FLEET[role]

    def all_models(self) -> list[FleetModel]:
        return list(_FLEET.values())

    # ── Registry-backed queries (sourced from Lemonade) ───────────────────

    def size_gb(self, model_id: str) -> float:
        return float(self._info(model_id).get("size", 5.0))

    def ctx_size(self, model_id: str) -> int:
        return int(self._info(model_id).get("max_context_window", 8192))

    def has_vision(self, model_id: str) -> bool:
        return "vision" in self._info(model_id).get("labels", [])

    def vision_models(self) -> list[FleetModel]:
        """Models with multimodal image input (have mmproj)."""
        return [m for m in _FLEET.values() if self.has_vision(m.model_id)]

    def lightweight_models(self) -> list[FleetModel]:
        """Models ≤2 GB — safe to keep always loaded."""
        return [m for m in _FLEET.values() if self.size_gb(m.model_id) <= 2.0]

    def large_models(self) -> list[FleetModel]:
        """Models >10 GB — require hot-swap coordination."""
        return [m for m in _FLEET.values() if self.size_gb(m.model_id) > 10.0]


_fleet: LocalResearchFleet | None = None


def get_fleet() -> LocalResearchFleet:
    global _fleet
    if _fleet is None:
        _fleet = LocalResearchFleet()
    return _fleet
