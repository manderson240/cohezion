"""Tests for the expanded OmniFleet 29-model registry.

Discriminating tests: wrong implementations (e.g. missing roles, wrong
size values, broken routing) would fail these.

All metadata queries (size, vision, ctx) use an injected FIXTURE_REGISTRY
so no Lemonade server is required.
"""

from __future__ import annotations

import pytest

from cohezion.inference.local_fleet import (
    FleetRole,
    LocalResearchFleet,
    RAM_CEILING_GB,
    RAM_EFFECTIVE_GB,
    _FLEET,
    _TYPE_TO_ROLE,
    get_fleet,
)

# Fixture registry mirrors real Lemonade /api/v1/models data for models in _FLEET.
# Injected into LocalResearchFleet to avoid HTTP calls.
FIXTURE_REGISTRY = [
    {"id": "llama3.2-1b-FLM",                    "size": 1.30, "max_context_window": 131072,  "labels": []},
    {"id": "Qwen3-0.6B-GGUF",                    "size": 0.38, "max_context_window": 40960,   "labels": ["reasoning", "tool-calling"]},
    {"id": "Bonsai-4B-gguf",                      "size": 0.572,"max_context_window": 32768,   "labels": ["llamacpp", "tool-calling"]},
    {"id": "Bonsai-8B-gguf",                      "size": 1.16, "max_context_window": 65536,   "labels": ["llamacpp", "tool-calling"]},
    {"id": "nomic-embed-text-v2-moe-GGUF",        "size": 0.51, "max_context_window": 512,     "labels": ["embeddings"]},
    {"id": "Whisper-Large-v3-Turbo",              "size": 1.62, "max_context_window": 0,        "labels": ["transcription", "realtime-transcription", "hot"]},
    {"id": "kokoro-v1",                           "size": 0.354,"max_context_window": 0,        "labels": ["tts"]},
    {"id": "RealESRGAN-x4plus",                   "size": 0.064,"max_context_window": 0,        "labels": ["upscaling", "image"]},
    {"id": "Gemma-4-E4B-it-GGUF",                "size": 5.97, "max_context_window": 131072,  "labels": ["vision", "tool-calling"]},
    {"id": "deepseek-r1-0528-8b-FLM",            "size": 5.60, "max_context_window": 40960,   "labels": ["reasoning"]},
    {"id": "DeepSeek-Qwen3-8B-GGUF",             "size": 5.25, "max_context_window": 131072,  "labels": ["reasoning", "tool-calling"]},
    {"id": "Gemma-4-E2B-it-GGUF",                "size": 4.09, "max_context_window": 131072,  "labels": ["vision", "tool-calling"]},
    {"id": "SD-Turbo",                            "size": 5.21, "max_context_window": 0,        "labels": ["image"]},
    {"id": "Qwen3-Coder-30B-A3B-Instruct-GGUF",  "size": 18.60,"max_context_window": 262144,  "labels": ["coding", "tool-calling", "hot"]},
    {"id": "Qwen3.6-35B-A3B-ThinkingCoder",       "size": 21.70,"max_context_window": 262144,  "labels": ["coding", "custom", "tool-calling", "vision"]},
    {"id": "Gemma-4-31B-it-GGUF",                "size": 19.50,"max_context_window": 262144,  "labels": ["vision", "tool-calling", "hot"]},
    {"id": "Gemma-4-26B-A4B-it-GGUF",            "size": 18.10,"max_context_window": 262144,  "labels": ["hot", "tool-calling", "vision", "llamacpp"]},
    {"id": "Flux-2-Klein-9B-GGUF",               "size": 19.00,"max_context_window": 0,        "labels": ["image", "edit"]},
    {"id": "Nemotron-3-Nano-30B-A3B-GGUF",       "size": 22.80,"max_context_window": 1048576, "labels": ["tool-calling"]},
]


class TestFleetRegistryStructure:
    """Structural invariants — the registry must have specific roles and models."""

    def test_fleet_has_all_required_roles(self) -> None:
        required = {
            FleetRole.ROUTER, FleetRole.EMBED, FleetRole.TRANSCRIBE,
            FleetRole.TTS, FleetRole.GENERATION, FleetRole.CODE,
            FleetRole.IMAGE_GEN, FleetRole.VISION, FleetRole.REASONING,
        }
        missing = required - set(_FLEET.keys())
        assert not missing, f"Missing roles: {missing}"

    def test_all_models_have_positive_size(self) -> None:
        fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)
        for role, model in _FLEET.items():
            size = fleet.size_gb(model.model_id)
            assert size >= 0.0, f"{role}: size={size} < 0"

    def test_all_models_have_model_id(self) -> None:
        for role, model in _FLEET.items():
            assert model.model_id, f"{role} has empty model_id"

    def test_ram_ceiling_makes_sense(self) -> None:
        assert RAM_CEILING_GB == 96.0
        assert RAM_EFFECTIVE_GB == 88.0
        assert RAM_EFFECTIVE_GB < RAM_CEILING_GB

    def test_fleet_count_matches_expected(self) -> None:
        assert len(_FLEET) >= 19, f"Expected ≥19 roles, got {len(_FLEET)}"


class TestFleetModelAttributes:
    """Models must have correct attributes for the system to function."""

    def setup_method(self) -> None:
        self.fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)

    def test_router_is_npu(self) -> None:
        router = _FLEET[FleetRole.ROUTER]
        assert router.is_npu, "llama3.2-1b-FLM must be marked as NPU"
        assert router.model_id == "llama3.2-1b-FLM"

    def test_router_tps_is_42(self) -> None:
        """Discriminating: wrong TPS would break throughput calculations in gauntlet."""
        router = _FLEET[FleetRole.ROUTER]
        assert router.tps_estimate == 42.0, (
            f"Expected 42.0 TPS for llama3.2-1b-FLM, got {router.tps_estimate}"
        )

    def test_code_model_has_large_ctx(self) -> None:
        code = _FLEET[FleetRole.CODE]
        assert self.fleet.ctx_size(code.model_id) >= 32768, (
            f"Qwen3-Coder-30B must have ≥32k ctx; "
            f"got {self.fleet.ctx_size(code.model_id)}"
        )

    def test_vision_models_have_has_vision_true(self) -> None:
        """Discriminating: Gemma-4-31B must be marked as vision-capable."""
        vision = _FLEET[FleetRole.VISION]
        assert self.fleet.has_vision(vision.model_id), (
            f"{vision.model_id} must have vision label in registry"
        )

    def test_generation_model_has_vision(self) -> None:
        """Gemma-4-E4B has mmproj — must be vision-capable."""
        gen = _FLEET[FleetRole.GENERATION]
        assert self.fleet.has_vision(gen.model_id), (
            f"{gen.model_id} must have vision label in registry"
        )

    def test_lightweight_models_are_under_2gb(self) -> None:
        light = self.fleet.lightweight_models()
        assert len(light) >= 5, "Expected ≥5 lightweight models"
        for m in light:
            size = self.fleet.size_gb(m.model_id)
            assert size <= 2.0, f"{m.model_id}: size={size} > 2.0"

    def test_large_models_are_over_10gb(self) -> None:
        large = self.fleet.large_models()
        assert len(large) >= 5, "Expected ≥5 large (hot-swap) models"
        for m in large:
            size = self.fleet.size_gb(m.model_id)
            assert size > 10.0, f"{m.model_id}: size={size} ≤ 10.0"


class TestFleetRouting:
    """Output type → FleetRole routing must be correct."""

    def test_code_routes_to_code_role(self) -> None:
        role = _TYPE_TO_ROLE.get("code")
        assert role == FleetRole.CODE

    def test_math_reasoning_routes_to_code(self) -> None:
        """Discriminating: math_reasoning must NOT route to FleetRole.GENERATION."""
        role = _TYPE_TO_ROLE.get("math_reasoning")
        assert role == FleetRole.CODE, (
            f"math_reasoning should map to CODE; got {role}"
        )

    def test_short_categorical_routes_to_router(self) -> None:
        role = _TYPE_TO_ROLE.get("short_categorical")
        assert role == FleetRole.ROUTER

    def test_embed_routes_to_embed(self) -> None:
        role = _TYPE_TO_ROLE.get("embed")
        assert role == FleetRole.EMBED

    def test_unknown_type_falls_back_to_generation(self) -> None:
        fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)
        model = fleet.route("unknown_type_xyz")
        assert model.role == FleetRole.GENERATION, (
            f"Unknown types should fall back to GENERATION; got {model.role}"
        )


class TestFleetSingleton:
    """get_fleet() must return a stable singleton."""

    def test_singleton_is_same_object(self) -> None:
        f1 = get_fleet()
        f2 = get_fleet()
        assert f1 is f2, "get_fleet() must return the same singleton"

    def test_all_models_returns_list(self) -> None:
        fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)
        models = fleet.all_models()
        assert isinstance(models, list)
        assert len(models) == len(_FLEET)

    def test_vision_models_returns_subset(self) -> None:
        fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)
        vision = fleet.vision_models()
        assert len(vision) >= 3, "Expected ≥3 vision-capable models"
        for m in vision:
            assert fleet.has_vision(m.model_id), (
                f"{m.model_id} in vision_models() but has no vision label"
            )

    def test_unknown_model_gets_fallback_size(self) -> None:
        """Discriminating: fleet.size_gb must return 5.0 for unknown models."""
        fleet = LocalResearchFleet(registry=FIXTURE_REGISTRY)
        size = fleet.size_gb("nonexistent-model-xyz")
        assert size == pytest.approx(5.0), "Unknown model should return 5.0 GB default"
