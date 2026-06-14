"""Registry structure and lookup tests."""

from __future__ import annotations

from cohezion.inference.registry import (
    FleetRegistry,
    Lane,
    ModelEntry,
    Task,
    WeightQuant,
    get_registry,
)


def test_default_registry_has_four_gemma_lanes() -> None:
    registry = FleetRegistry()
    gemma_models = [m for m in registry.models.values() if m.model_id.startswith("Gemma-4-")]
    assert len(gemma_models) == 4, "Expect E2B, E4B, 26B-A4B, 31B per Symphony Guide"


def test_gemma_lanes_bind_to_correct_silicon() -> None:
    registry = FleetRegistry()
    assert registry.models["Gemma-4-E2B-it-GGUF"].lane == Lane.NPU
    assert registry.models["Gemma-4-E4B-it-GGUF"].lane == Lane.IGPU_ROCWMMA
    assert registry.models["Gemma-4-26B-A4B-it-GGUF"].lane == Lane.IGPU_UNIFIED
    assert registry.models["Gemma-4-31B-it-GGUF"].lane == Lane.CPU


def test_gemma_lane_ports_match_symphony_launch_script() -> None:
    registry = FleetRegistry()
    assert "13306" in registry.models["Gemma-4-E2B-it-GGUF"].endpoint
    assert "13307" in registry.models["Gemma-4-E4B-it-GGUF"].endpoint
    assert "13308" in registry.models["Gemma-4-26B-A4B-it-GGUF"].endpoint
    assert "13309" in registry.models["Gemma-4-31B-it-GGUF"].endpoint


def test_for_task_returns_sorted_by_priority() -> None:
    registry = FleetRegistry()
    candidates = registry.for_task(Task.REASONING)
    priorities = [c.priority for c in candidates]
    assert priorities == sorted(priorities), "for_task must yield priority-ordered list"


def test_for_task_returns_only_task_affine_models() -> None:
    registry = FleetRegistry()
    candidates = registry.for_task(Task.CODE_GEN)
    for c in candidates:
        assert Task.CODE_GEN in c.task_affinity


def test_claude_tier_has_ascending_cost() -> None:
    registry = FleetRegistry()
    haiku = registry.models["claude-haiku-4-5"]
    sonnet = registry.models["claude-sonnet-4-6"]
    opus = registry.models["claude-opus-4-7"]
    assert (
        haiku.cost_per_1k_output_usd < sonnet.cost_per_1k_output_usd < opus.cost_per_1k_output_usd
    )


def test_local_only_excludes_cloud() -> None:
    registry = FleetRegistry()
    for m in registry.local_only():
        assert m.lane not in {Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE}


def test_mark_verified_sets_timestamp() -> None:
    registry = FleetRegistry()
    model_id = "Gemma-4-E2B-it-GGUF"
    assert registry.models[model_id].last_verified_at is None
    registry.mark_verified(model_id)
    assert registry.models[model_id].verified_working
    assert registry.models[model_id].last_verified_at is not None


def test_get_registry_returns_singleton() -> None:
    a = get_registry()
    b = get_registry()
    assert a is b


def test_model_entry_is_dataclass_with_expected_fields() -> None:
    sample = ModelEntry(
        model_id="x",
        lane=Lane.NPU,
        endpoint="http://localhost:1",
        runtime_backend="flm",
        task_affinity=frozenset({Task.ROUTING}),
        weight_quant=WeightQuant.INT4,
        context_window=1024,
    )
    assert sample.cost_per_1k_input_usd == 0.0
    assert sample.verified_working is False


# Supported values for llama.cpp's --cache-type-k / --cache-type-v flags.
# This set is intentionally narrow — any kv_quant.runtime_flag["llama.cpp"]
# value that isn't in here would be silently ignored at server startup and
# the cache would silently fall back to fp16. Kept as a regression guard
# against the TurboQuant lesson (`turbo3` was declared but the binary had no
# such flag, so the entire declaration was a silent no-op).
LLAMACPP_CACHE_TYPE_WHITELIST = {
    "f32",
    "f16",
    "bf16",
    "q8_0",
    "q4_0",
    "q4_1",
    "q5_0",
    "q5_1",
    "iq4_nl",
}


def test_kv_quant_llamacpp_runtime_flags_are_in_whitelist() -> None:
    registry = FleetRegistry()
    for model in registry.models.values():
        flag = model.kv_quant.runtime_flag.get("llama.cpp")
        if flag is None:
            continue
        assert flag in LLAMACPP_CACHE_TYPE_WHITELIST, (
            f"{model.model_id} declares kv_quant.runtime_flag['llama.cpp']={flag!r} "
            f"but llama-server --cache-type-k/-v only accepts "
            f"{sorted(LLAMACPP_CACHE_TYPE_WHITELIST)}. A value outside the whitelist "
            f"is silently ignored at server startup — the KV cache falls back to fp16 "
            f"with no error. See ~/.claude/plans/do-we-have-turbo-distributed-torvalds.md."
        )


def test_audit_liveness_classifies_all_four_drift_categories() -> None:
    """audit_liveness must reconcile static `verified_working` flags against a
    live probe and classify each local-lane model into exactly one category.

    Uses an injected fake `check_fleet_fn` so this runs deterministically in CI
    without depending on actual Lemonade/Ollama processes.
    """
    from types import SimpleNamespace

    from cohezion.inference.registry import LivenessAudit

    # Fake FleetHealth: npu DOWN, igpu_rocwmma UP, igpu_unified DOWN, cpu UP.
    fake_lanes = {
        "npu": SimpleNamespace(status=SimpleNamespace(value="down")),
        "igpu_rocwmma": SimpleNamespace(status=SimpleNamespace(value="up")),
        "igpu_unified": SimpleNamespace(status=SimpleNamespace(value="down")),
        "cpu": SimpleNamespace(status=SimpleNamespace(value="up")),
    }
    fake_health = SimpleNamespace(lanes=fake_lanes)

    registry = FleetRegistry()
    # Force a known shape: toggle verified_working so all four categories appear.
    registry.models["Gemma-4-E2B-it-GGUF"].verified_working = True  # NPU down → critical_stale
    registry.models["Gemma-4-E4B-it-GGUF"].verified_working = False  # rocwmma up → unverified_up
    registry.models["Gemma-4-26B-A4B-it-GGUF"].verified_working = False  # unified down → lane_down
    registry.models["Gemma-4-31B-it-GGUF"].verified_working = True  # cpu up → healthy

    audit = registry.audit_liveness(check_fleet_fn=lambda: fake_health)

    assert isinstance(audit, LivenessAudit)
    categories = {i.model_id: i.category for i in audit.items}
    assert categories["Gemma-4-E2B-it-GGUF"] == "critical_stale"
    assert categories["Gemma-4-E4B-it-GGUF"] == "unverified_up"
    assert categories["Gemma-4-26B-A4B-it-GGUF"] == "lane_down"
    assert categories["Gemma-4-31B-it-GGUF"] == "healthy"

    # Convenience properties return filtered subsets.
    assert {i.model_id for i in audit.critical_stale} >= {"Gemma-4-E2B-it-GGUF"}
    assert {i.model_id for i in audit.healthy} >= {"Gemma-4-31B-it-GGUF"}
    assert {i.model_id for i in audit.unverified_up} >= {"Gemma-4-E4B-it-GGUF"}
    assert {i.model_id for i in audit.lane_down} >= {"Gemma-4-26B-A4B-it-GGUF"}


def test_audit_liveness_skips_cloud_and_cli_lanes() -> None:
    """Cloud/CLI lanes (Claude, Gemini, Ollama-cloud) have unreachability handled
    via try/except on dispatch, not health probes. audit_liveness should include
    only the four local silicon lanes (NPU/iGPU-ROCWMMA/iGPU-Unified/CPU).
    """
    from types import SimpleNamespace

    fake_health = SimpleNamespace(
        lanes={
            "npu": SimpleNamespace(status=SimpleNamespace(value="up")),
            "igpu_rocwmma": SimpleNamespace(status=SimpleNamespace(value="up")),
            "igpu_unified": SimpleNamespace(status=SimpleNamespace(value="up")),
            "cpu": SimpleNamespace(status=SimpleNamespace(value="up")),
        }
    )
    registry = FleetRegistry()
    audit = registry.audit_liveness(check_fleet_fn=lambda: fake_health)
    local_lane_values = {"npu", "igpu_rocwmma", "igpu_unified", "cpu"}
    for item in audit.items:
        assert item.lane in local_lane_values, (
            f"{item.model_id} got audited with non-local lane {item.lane!r}; cloud/CLI models should be filtered out."
        )


# ---------------------------------------------------------------------------
# Item 50 — Gemma-4 QAT q4_0 alternatives registration
# ---------------------------------------------------------------------------

_QAT_MODEL_IDS = {
    "Gemma-4-E2B-it-qat-q4_0-GGUF",
    "Gemma-4-E4B-it-qat-q4_0-GGUF",
    "Gemma-4-26B-A4B-it-qat-q4_0-GGUF",
    "Gemma-4-31B-it-qat-q4_0-GGUF",
}

_QAT_TO_PTQ = {
    "Gemma-4-E2B-it-qat-q4_0-GGUF": "Gemma-4-E2B-it-GGUF",
    "Gemma-4-E4B-it-qat-q4_0-GGUF": "Gemma-4-E4B-it-GGUF",
    "Gemma-4-26B-A4B-it-qat-q4_0-GGUF": "Gemma-4-26B-A4B-it-GGUF",
    "Gemma-4-31B-it-qat-q4_0-GGUF": "Gemma-4-31B-it-GGUF",
}


def test_qat_q4_0_all_four_symphony_tiers_registered() -> None:
    """Item 50: all four QAT variants must be present in the default registry."""
    registry = FleetRegistry()
    present = set(registry.models)
    missing = _QAT_MODEL_IDS - present
    assert not missing, f"QAT variants missing from registry: {missing}"


def test_qat_variants_unverified_working() -> None:
    """Item 50: QAT models are alternatives pending the swap-proof — never auto-verified."""
    registry = FleetRegistry()
    for qat_id in _QAT_MODEL_IDS:
        m = registry.models.get(qat_id)
        assert m is not None, f"{qat_id} not in registry"
        assert not m.verified_working, (
            f"{qat_id} has verified_working=True before the swap-proof; "
            "registration must be additive (verified_working=False) per item-50 policy"
        )


def test_qat_variants_surface_in_for_task() -> None:
    """Item 50 falsifiable check: each QAT variant appears in for_task() for its tier's tasks."""
    registry = FleetRegistry()
    # E2B QAT → same task affinity as the PTQ E2B
    e2b_ids = {m.model_id for m in registry.for_task(Task.SENSING)}
    assert "Gemma-4-E2B-it-qat-q4_0-GGUF" in e2b_ids, (
        "Gemma-4-E2B-it-qat-q4_0-GGUF must surface in for_task(SENSING)"
    )
    # E4B QAT → same as PTQ E4B
    e4b_ids = {m.model_id for m in registry.for_task(Task.GOVERNANCE)}
    assert "Gemma-4-E4B-it-qat-q4_0-GGUF" in e4b_ids, (
        "Gemma-4-E4B-it-qat-q4_0-GGUF must surface in for_task(GOVERNANCE)"
    )
    # 26B QAT → same as PTQ 26B
    m26_ids = {m.model_id for m in registry.for_task(Task.REASONING)}
    assert "Gemma-4-26B-A4B-it-qat-q4_0-GGUF" in m26_ids, (
        "Gemma-4-26B-A4B-it-qat-q4_0-GGUF must surface in for_task(REASONING)"
    )
    # 31B QAT → same as PTQ 31B
    m31_ids = {m.model_id for m in registry.for_task(Task.ARCHITECT)}
    assert "Gemma-4-31B-it-qat-q4_0-GGUF" in m31_ids, (
        "Gemma-4-31B-it-qat-q4_0-GGUF must surface in for_task(ARCHITECT)"
    )


def test_qat_variants_non_displacing_priority() -> None:
    """Item 50: QAT priority > PTQ priority so the unverified alternative never auto-displaces
    the verified working model in for_task() ordering."""
    registry = FleetRegistry()
    for qat_id, ptq_id in _QAT_TO_PTQ.items():
        qat = registry.models[qat_id]
        ptq = registry.models[ptq_id]
        assert qat.priority > ptq.priority, (
            f"{qat_id} (priority={qat.priority}) must have LOWER preference than "
            f"{ptq_id} (priority={ptq.priority}) — an unverified QAT must not displace "
            "the verified PTQ model in routing. Set QAT priority = PTQ_priority + 1."
        )


def test_qat_variants_bind_to_same_silicon_as_ptq() -> None:
    """Item 50: each QAT variant targets the same lane/endpoint as its PTQ counterpart
    (same physical hardware, different GGUF file)."""
    registry = FleetRegistry()
    for qat_id, ptq_id in _QAT_TO_PTQ.items():
        qat = registry.models[qat_id]
        ptq = registry.models[ptq_id]
        assert qat.lane == ptq.lane, (
            f"{qat_id} lane={qat.lane} != {ptq_id} lane={ptq.lane}; "
            "QAT variant must target the same silicon as its PTQ counterpart"
        )
        assert qat.endpoint == ptq.endpoint, (
            f"{qat_id} endpoint={qat.endpoint} != {ptq_id} endpoint={ptq.endpoint}"
        )


# ---------------------------------------------------------------------------
# Item 53 — Qwen3.6-35B-A3B-MTP-GGUF iGPU main-tier MTP candidate registration
# ---------------------------------------------------------------------------

_MTP_MODEL_ID = "Qwen3.6-35B-A3B-MTP-GGUF"
# The primary iGPU main-tier model it would eventually displace (after the speed proof).
_MTP_PRIMARY_ID = "Gemma-4-26B-A4B-it-GGUF"


def test_qwen36_mtp_registered() -> None:
    """Item 53: Qwen3.6-35B-A3B-MTP-GGUF must be present in the default registry."""
    registry = FleetRegistry()
    assert _MTP_MODEL_ID in registry.models, (
        f"{_MTP_MODEL_ID} missing from registry; item 53 additive registration not done"
    )


def test_qwen36_mtp_unverified_working() -> None:
    """Item 53: MTP candidate is additive-first (unverified) — swap is experiment-gated."""
    registry = FleetRegistry()
    m = registry.models.get(_MTP_MODEL_ID)
    assert m is not None, f"{_MTP_MODEL_ID} not in registry"
    assert not m.verified_working, (
        f"{_MTP_MODEL_ID} has verified_working=True; registration must be additive "
        "(verified_working=False) — the SWAP requires a speed/memory/quality proof first"
    )


def test_qwen36_mtp_surfaces_in_for_task() -> None:
    """Item 53 FALSIFIABLE check: MTP candidate surfaces in for_task() for iGPU-affine tasks.

    This check CAN come back negative: if the task_affinity is wrong (e.g. only SUMMARIZATION)
    it would PASS test_qwen36_mtp_registered but FAIL here, proving the implementation is wrong.
    """
    registry = FleetRegistry()
    reasoning_ids = {m.model_id for m in registry.for_task(Task.REASONING)}
    assert _MTP_MODEL_ID in reasoning_ids, (
        f"{_MTP_MODEL_ID} must surface in for_task(REASONING) — "
        "Qwen3.6 35B-A3B is a reasoning-capable model"
    )
    code_ids = {m.model_id for m in registry.for_task(Task.CODE_GEN)}
    assert _MTP_MODEL_ID in code_ids, (
        f"{_MTP_MODEL_ID} must surface in for_task(CODE_GEN) — "
        "Qwen3 series is particularly strong at code generation"
    )


def test_qwen36_mtp_non_displacing_priority() -> None:
    """Item 53: MTP candidate priority > iGPU primary so it never auto-displaces the resident.

    The swap from primary to MTP is experiment-gated. Until the proof passes, the MTP
    entry must have higher priority (= lower preference) than the current primary.
    """
    registry = FleetRegistry()
    mtp = registry.models[_MTP_MODEL_ID]
    primary = registry.models[_MTP_PRIMARY_ID]
    assert mtp.priority > primary.priority, (
        f"{_MTP_MODEL_ID} (priority={mtp.priority}) must have LOWER preference than "
        f"{_MTP_PRIMARY_ID} (priority={primary.priority}) — an unverified MTP candidate "
        "must not displace the resident iGPU model before the speed proof passes."
    )


def test_qwen36_mtp_on_igpu_unified_lane() -> None:
    """Item 53: MTP candidate targets the iGPU Unified lane (the 'main tier' for large models).

    Qwen3.6-35B-A3B at IQ4_XS is ~17-20 GB — fits unified memory (IGPU_UNIFIED/13308).
    It is NOT on the ROCWMMA lane (which hosts smaller models like E4B at 4.6 GB).
    """
    registry = FleetRegistry()
    m = registry.models.get(_MTP_MODEL_ID)
    assert m is not None, f"{_MTP_MODEL_ID} not in registry"
    assert m.lane == Lane.IGPU_UNIFIED, (
        f"{_MTP_MODEL_ID} lane={m.lane}; expected IGPU_UNIFIED — "
        "35B-A3B at IQ4_XS (~17-20 GB) is the main-tier iGPU replacement candidate, "
        "not a small-model ROCWMMA slot"
    )
    assert "13308" in m.endpoint, (
        f"{_MTP_MODEL_ID} endpoint={m.endpoint!r}; expected port 13308 (iGPU Unified)"
    )


# ---------------------------------------------------------------------------
# Item 54 — PaddleOCR-VL-1.6-GGUF second OCR_DOC specialist registration
# ---------------------------------------------------------------------------

_PADDLEOCR_ID = "PaddleOCR-VL-1.6-GGUF"
_GLM_OCR_ID = "GLM-OCR-GGUF"  # the existing OCR_DOC seed (priority=25); must remain present


def test_paddleocr_vl16_registered() -> None:
    """Item 54: PaddleOCR-VL-1.6-GGUF must be present in the default registry."""
    registry = FleetRegistry()
    assert _PADDLEOCR_ID in registry.models, (
        f"{_PADDLEOCR_ID} missing from registry; item 54 additive registration not done"
    )


def test_paddleocr_vl16_unverified_working() -> None:
    """Item 54: PaddleOCR is additive-first — OmniDocBench bake-off is experiment-gated."""
    registry = FleetRegistry()
    m = registry.models.get(_PADDLEOCR_ID)
    assert m is not None, f"{_PADDLEOCR_ID} not in registry"
    assert not m.verified_working, (
        f"{_PADDLEOCR_ID} has verified_working=True; the mmproj serving proof and "
        "OmniDocBench field-accuracy bake-off must pass first (item 54 policy)"
    )


def test_for_task_ocr_doc_includes_both_candidates() -> None:
    """Item 54 FALSIFIABLE check: for_task(OCR_DOC) must include BOTH GLM-OCR AND PaddleOCR.

    This check CAN come back negative in two ways:
    - PaddleOCR missing task_affinity OCR_DOC → not in for_task
    - GLM-OCR accidentally removed → only one candidate returned
    Either would reveal a bug the test successfully catches.
    """
    registry = FleetRegistry()
    ocr_ids = {m.model_id for m in registry.for_task(Task.OCR_DOC)}
    assert _GLM_OCR_ID in ocr_ids, (
        f"{_GLM_OCR_ID} must remain in for_task(OCR_DOC) after item 54 — "
        "PaddleOCR registration is ADDITIVE; GLM-OCR must not be displaced"
    )
    assert _PADDLEOCR_ID in ocr_ids, (
        f"{_PADDLEOCR_ID} must appear in for_task(OCR_DOC) — "
        "0.9B 96.33% OmniDocBench SOTA model must be routable"
    )


def test_paddleocr_vl16_non_displacing_priority() -> None:
    """Item 54: PaddleOCR priority > GLM-OCR so the unverified alternative never auto-displaces.

    The bake-off (OmniDocBench accuracy >= GLM-OCR at <= memory) must pass before raising
    PaddleOCR's priority above GLM-OCR. Until then, GLM-OCR is preferred.
    """
    registry = FleetRegistry()
    paddle = registry.models[_PADDLEOCR_ID]
    glm = registry.models[_GLM_OCR_ID]
    assert paddle.priority > glm.priority, (
        f"{_PADDLEOCR_ID} (priority={paddle.priority}) must have LOWER preference than "
        f"{_GLM_OCR_ID} (priority={glm.priority}) — the unverified PaddleOCR must not "
        "displace the existing OCR seed before the bake-off proof passes."
    )


def test_paddleocr_vl16_shares_lane_with_glm_ocr() -> None:
    """Item 54: PaddleOCR targets the same lane/endpoint as GLM-OCR (same mmproj path).

    Both are VLMs served via llama-mtmd sidecar on the IGPU_ROCWMMA lane. Using the
    same endpoint ensures the serving recipe (item 18 path) applies to both.
    """
    registry = FleetRegistry()
    paddle = registry.models[_PADDLEOCR_ID]
    glm = registry.models[_GLM_OCR_ID]
    assert paddle.lane == glm.lane, (
        f"{_PADDLEOCR_ID} lane={paddle.lane} != {_GLM_OCR_ID} lane={glm.lane}; "
        "both OCR_DOC VLMs share the mmproj serving path on the same silicon"
    )
    assert paddle.endpoint == glm.endpoint, (
        f"{_PADDLEOCR_ID} endpoint={paddle.endpoint!r} != {_GLM_OCR_ID} endpoint={glm.endpoint!r}"
    )
