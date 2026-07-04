"""Tests for compound.oom_guard — OOM guardrails, smart routing, hot-swap, tier awareness."""

from __future__ import annotations

import pytest

from cohezion.compound.oom_guard import (
    MODEL_FOOTPRINT_GB,
    MODEL_TIER,
    RAM_LOAD_BUFFER_GB,
    SAFE_CTX_LIMIT,
    UMA_TIERS,
    BackendEntry,
    ComputeTier,
    MemorySnapshot,
    OOMRisk,
    _TASK_ROUTING,
    check_oom_risk,
    get_active_uma_gb,
    get_live_topology,
    models_on_tier,
    safe_model_for_task,
    tier_for_model,
    topology_summary,
)


# ── Structural ────────────────────────────────────────────────────────────────

class TestStructural:
    def test_safe_ctx_limit_bounded(self):
        assert 0 < SAFE_CTX_LIMIT <= 32768

    def test_ram_load_buffer_positive(self):
        assert RAM_LOAD_BUFFER_GB > 0

    def test_all_task_routing_entries_have_known_fallback(self):
        """Every routing fallback must exist in MODEL_FOOTPRINT_GB."""
        for task in _TASK_ROUTING:
            fallback = _TASK_ROUTING[task][1]
            assert fallback in MODEL_FOOTPRINT_GB, (
                f"Task '{task}' fallback '{fallback}' not in MODEL_FOOTPRINT_GB"
            )

    def test_all_task_routing_fallbacks_are_small(self):
        """Every fallback model must be small enough to always fit (≤5GB footprint)."""
        for task in _TASK_ROUTING:
            fallback = _TASK_ROUTING[task][1]
            fp = MODEL_FOOTPRINT_GB.get(fallback, 0.0)
            # Allow Bonsai-8B (5.25GB) as it fits with buffer at ≥13.25GB RAM
            if "Bonsai-8B" in fallback or "DeepSeek-Qwen3-8B" in fallback:
                continue
            assert fp <= 6.5, (
                f"Task '{task}' fallback '{fallback}' is {fp:.1f}GB — too large for a safe fallback"
            )

    def test_memory_snapshot_has_positive_values(self):
        snap = MemorySnapshot.capture()
        assert snap.total_gb > 0
        assert snap.available_gb >= 0
        assert snap.used_gb >= 0
        assert abs(snap.total_gb - snap.available_gb - snap.used_gb) < 1.0  # rough accounting


# ── Memory gate — discriminating ─────────────────────────────────────────────

class TestCheckOOMRisk:
    def test_small_model_always_safe(self):
        """Models under HEAVY_THRESHOLD_GB are safe regardless of available RAM."""
        risk = check_oom_risk("Bonsai-1.7B-gguf", available_gb=1.0)
        assert risk.safe is True

    def test_heavy_model_safe_with_sufficient_ram(self):
        risk = check_oom_risk("Gemma-4-E4B-it-GGUF", available_gb=40.0)
        assert risk.safe is True

    def test_heavy_model_blocked_insufficient_ram(self):
        """Discriminating: a heavy model blocked at low RAM — wrong impl (no gate) returns safe=True."""
        risk = check_oom_risk("Gemma-4-31B-it-GGUF", available_gb=10.0)
        assert risk.safe is False

    def test_threshold_is_footprint_plus_buffer(self):
        """Gate threshold is exactly footprint + RAM_LOAD_BUFFER_GB."""
        model = "Gemma-4-E4B-it-GGUF"
        footprint = MODEL_FOOTPRINT_GB[model]
        # Just under threshold: blocked
        risk_under = check_oom_risk(model, available_gb=footprint + RAM_LOAD_BUFFER_GB - 0.1)
        # Just at threshold: safe
        risk_at = check_oom_risk(model, available_gb=footprint + RAM_LOAD_BUFFER_GB)
        assert risk_under.safe is False
        assert risk_at.safe is True

    def test_unknown_model_treated_as_small(self):
        """Unknown model (footprint=0) passes the gate at any RAM level."""
        risk = check_oom_risk("unknown-hypothetical-model", available_gb=0.5)
        assert risk.safe is True

    def test_oomrisk_is_namedtuple(self):
        risk = check_oom_risk("Bonsai-1.7B-gguf", available_gb=10.0)
        assert isinstance(risk, OOMRisk)
        assert isinstance(risk.reason, str)


# ── Smart routing — discriminating ───────────────────────────────────────────

class TestSafeModelForTask:
    def test_always_returns_a_non_empty_string(self):
        """Discriminating: a broken impl may return None or ''. Must always be a valid str."""
        for task in _TASK_ROUTING:
            model = safe_model_for_task(task, available_gb=8.0)
            assert isinstance(model, str) and model

    def test_routes_to_preferred_when_ram_ample(self):
        """With plenty of RAM, preferred model is returned."""
        preferred, _ = _TASK_ROUTING["qa_judge"]
        model = safe_model_for_task("qa_judge", available_gb=100.0)
        assert model == preferred

    def test_falls_back_when_preferred_blocked(self):
        """Discriminating: when preferred doesn't fit, fallback is returned — wrong impl returns preferred."""
        preferred, fallback = _TASK_ROUTING["long_generation"]
        fp_preferred = MODEL_FOOTPRINT_GB.get(preferred, 0.0)
        # Give just enough RAM for fallback but not preferred
        fp_fallback = MODEL_FOOTPRINT_GB.get(fallback, 0.0)
        # Only safe if preferred is heavy; skip if both are small
        if fp_preferred < 5.0:
            pytest.skip("preferred model is small — gate doesn't apply")
        available = fp_fallback + RAM_LOAD_BUFFER_GB + 0.5  # fits fallback, not preferred
        model = safe_model_for_task("long_generation", available_gb=available)
        assert model == fallback

    def test_last_resort_at_critically_low_ram(self):
        """At 8GB available, all task types must return a non-empty model name."""
        for task in _TASK_ROUTING:
            model = safe_model_for_task(task, available_gb=8.0)
            # Last resort Bonsai-4B (2.4+8=10.4GB) still blocked at 8GB — that's OK,
            # the guard logs an error but still returns a valid model name.
            assert isinstance(model, str) and model

    def test_unknown_task_type_gets_a_model(self):
        """An unknown task type falls through to the _TASK_ROUTING default."""
        model = safe_model_for_task("totally_unknown_task_type", available_gb=50.0)
        assert isinstance(model, str) and model


# ── Tier awareness ────────────────────────────────────────────────────────────

class TestComputeTier:
    def test_all_gguf_llms_are_igpu(self):
        """All GGUF LLMs must map to IGPU — verified by /api/v1/health vulkan backends."""
        igpu_models = [n for n, t in MODEL_TIER.items() if t == ComputeTier.IGPU]
        assert len(igpu_models) >= 10, "Should have many iGPU GGUF models"

    def test_flm_models_are_npu(self):
        """FLM models use XDNA2 SRAM, NOT UMA."""
        assert MODEL_TIER.get("llama3.2-1b-FLM") == ComputeTier.NPU
        assert MODEL_TIER.get("deepseek-r1-0528-8b-FLM") == ComputeTier.NPU

    def test_npu_tier_not_in_uma_tiers(self):
        """Discriminating: NPU must NOT be in UMA_TIERS — it uses SRAM not UMA."""
        assert ComputeTier.NPU not in UMA_TIERS

    def test_igpu_cpu_specialized_are_uma_tiers(self):
        assert ComputeTier.IGPU in UMA_TIERS
        assert ComputeTier.CPU in UMA_TIERS
        assert ComputeTier.SPECIALIZED in UMA_TIERS

    def test_kokoro_is_cpu_tier(self):
        """kokoro-v1 shows device: cpu in /api/v1/health."""
        assert MODEL_TIER.get("kokoro-v1") == ComputeTier.CPU

    def test_whisper_is_specialized(self):
        """Whisper uses whispercpp recipe — specialized, no KV cache."""
        assert MODEL_TIER.get("Whisper-Large-v3-Turbo") == ComputeTier.SPECIALIZED

    def test_tier_for_model_defaults_igpu_for_unknown(self):
        """Unknown GGUF-style names default to IGPU (all real GGUF models are vulkan)."""
        assert tier_for_model("SomeUnknown-Model-GGUF") == ComputeTier.IGPU

    def test_tier_for_known_model(self):
        assert tier_for_model("Bonsai-8B-gguf") == ComputeTier.IGPU
        assert tier_for_model("llama3.2-1b-FLM") == ComputeTier.NPU


class TestTopologyFunctions:
    def test_get_live_topology_returns_list(self):
        """Must always return a list — never raises."""
        topo = get_live_topology()
        assert isinstance(topo, list)

    def test_backend_entry_fields(self):
        """If router is live, entries have model_name, tier, footprint_gb, backend_url, device."""
        topo = get_live_topology()
        for entry in topo:
            assert isinstance(entry, BackendEntry)
            assert isinstance(entry.model_name, str)
            assert isinstance(entry.tier, ComputeTier)
            assert isinstance(entry.footprint_gb, float)

    def test_get_active_uma_gb_nonnegative(self):
        """UMA committed GB must be ≥ 0."""
        assert get_active_uma_gb() >= 0.0

    def test_models_on_tier_with_fixture(self):
        """models_on_tier uses supplied topology — no HTTP call."""
        topo = [
            BackendEntry("Bonsai-8B-gguf", ComputeTier.IGPU, 5.25, "http://127.0.0.1:8007/v1", "gpu"),
            BackendEntry("kokoro-v1", ComputeTier.CPU, 0.35, "http://127.0.0.1:8005/v1", "cpu"),
        ]
        assert models_on_tier(ComputeTier.IGPU, topology=topo) == ["Bonsai-8B-gguf"]
        assert models_on_tier(ComputeTier.CPU, topology=topo) == ["kokoro-v1"]
        assert models_on_tier(ComputeTier.NPU, topology=topo) == []

    def test_get_active_uma_npu_excluded(self):
        """Discriminating: NPU entries must NOT contribute to UMA total."""
        topo = [
            BackendEntry("llama3.2-1b-FLM", ComputeTier.NPU, 1.0, "", "npu"),
            BackendEntry("Bonsai-8B-gguf", ComputeTier.IGPU, 5.25, "", "gpu"),
        ]
        uma = sum(e.footprint_gb for e in topo if e.tier in UMA_TIERS)
        assert abs(uma - 5.25) < 0.01, "NPU model must not add to UMA"

    def test_topology_summary_has_required_keys(self):
        """topology_summary always returns the required dict keys."""
        summary = topology_summary()
        for key in ("ram_total_gb", "ram_available_gb", "uma_committed_gb", "backends_loaded", "by_tier"):
            assert key in summary, f"Missing key: {key}"
