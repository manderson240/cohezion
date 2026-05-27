from unittest.mock import MagicMock, patch

from cohezion.inference.task_classifier import classify as classify_task
from cohezion.inference.triune_orchestrator import build_triune_orchestrator


def _mock_gaia_tier(model_id: str, **_kwargs):
    tier = MagicMock()
    tier.label = f"gaia:{model_id}"
    return tier


def _build_local_only(**kwargs):
    """Build with cloud=False and no CLaSp so all tiers go through the mock."""
    return build_triune_orchestrator(include_cloud=False, clasp_draft_port=None, **kwargs)


def test_build_triune_orchestrator_structure():
    """3 local tiers with correct model IDs (N2 invariant). Cloud/CLaSp tested separately."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = _build_local_only()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    # N2: NPU must use llama3.2-1b-FLM (fits XDNA2 SRAM, 42 TPS — NOT qwen3.5-4b-FLM at 8.6 TPS)
    assert "gaia:llama3.2-1b-FLM" in labels, "N2: NPU tier must use llama3.2-1b-FLM"
    assert "gaia:qwen3.5-4b-FLM" not in labels, "N2: qwen3.5-4b-FLM is banned from NPU tier"
    assert "gaia:Gemma-4-E4B-it-GGUF" in labels
    assert "gaia:Gemma-4-31B-it-GGUF" in labels


def test_build_triune_orchestrator_quality_gates():
    """Quality gates: NPU=500, iGPU=750 (EXP-ROUTE-12), CPU=1000."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = _build_local_only()
    assert orch.tiers[0][1].min_chars == 500  # NPU: XDNA2
    assert orch.tiers[1][1].min_chars == 750  # iGPU: EXP-ROUTE-12 reduced from 2000
    assert orch.tiers[2][1].min_chars == 1000  # CPU: AVX-512


def test_build_triune_orchestrator_pre_dispatch_classifier_wired():
    """pre_dispatch_classifier must be the task_classifier.classify function."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = _build_local_only()
    assert orch._pre_dispatch_classifier is classify_task, (
        "pre_dispatch_classifier must be wired to task_classifier.classify — "
        "without it, categorical tasks get gate=500 and escalate to iGPU unnecessarily"
    )


def test_build_triune_orchestrator_npu_first():
    """NPU at tier 0, iGPU at tier 1, CPU at tier 2 — cheapest first."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = _build_local_only()
    assert orch.tiers[0][0].label == "gaia:llama3.2-1b-FLM", "NPU must be tier 0"
    assert orch.tiers[1][0].label == "gaia:Gemma-4-E4B-it-GGUF", "iGPU must be tier 1"
    assert orch.tiers[2][0].label == "gaia:Gemma-4-31B-it-GGUF", "CPU must be tier 2"


def test_build_triune_orchestrator_cloud_tiers():
    """With include_cloud=True, 5-tier tapestry: NPU+iGPU+CPU+Haiku+Sonnet."""
    with patch(
        "cohezion.inference.triune_orchestrator.build_gaia_native_tier", side_effect=_mock_gaia_tier
    ):
        orch = build_triune_orchestrator(include_cloud=True, clasp_draft_port=None)
    assert len(orch.tiers) == 5, "5-tier tapestry: 3 local + Haiku + Sonnet"
    cloud_ids = [t[0] for t in orch.tiers[3:]]
    assert "claude-haiku-4-5" in cloud_ids
    assert "claude-sonnet-4-6" in cloud_ids


def test_build_triune_orchestrator_cpu_port_lemonade():
    """N2 invariant: cpu_port default must be 13309 (lemonade), not 11434 (Ollama)."""
    import inspect

    sig = inspect.signature(build_triune_orchestrator)
    cpu_port_default = sig.parameters["cpu_port"].default
    assert cpu_port_default == 13309, (
        f"N2: cpu_port default must be 13309 (lemonade), got {cpu_port_default}. "
        "Ollama (11434) no longer serves the CPU tier — migrated 2026-05-21."
    )
