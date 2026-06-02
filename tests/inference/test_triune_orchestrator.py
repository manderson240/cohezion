from unittest.mock import MagicMock, patch

from cohezion.inference.activation_router import PrefillActivationRouter
from cohezion.inference.task_classifier import classify as classify_task
from cohezion.inference.triune_orchestrator import build_triune_orchestrator


def _sufficient_ram():
    """Mock MemorySnapshot.capture() to return sufficient RAM (32 GB) for local tiers."""
    snap = MagicMock()
    snap.available_gb = 32.0
    return snap


_OOM_GUARD_PATH = "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"


def _build_local_only(**kwargs):
    """Build with cloud=False and no CLaSp so all tiers go through direct HTTP."""
    with patch(_OOM_GUARD_PATH) as mock_ms:
        mock_ms.capture.return_value = _sufficient_ram()
        return build_triune_orchestrator(include_cloud=False, clasp_draft_port=None, **kwargs)


def test_build_triune_orchestrator_structure():
    """3 local tiers with correct model IDs (N2 invariant). Cloud/CLaSp tested separately."""
    orch = _build_local_only()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    # N2: NPU must use llama3.2-1b-FLM (fits XDNA2 SRAM, 42 TPS — NOT qwen3.5-4b-FLM at 8.6 TPS)
    assert "direct:llama3.2-1b-FLM" in labels, "N2: NPU tier must use llama3.2-1b-FLM"
    assert "direct:qwen3.5-4b-FLM" not in labels, "N2: qwen3.5-4b-FLM is banned from NPU tier"
    # iGPU: deepseek-r1-0528-8b-FLM per harness N1/N2 spec
    assert "direct:deepseek-r1-0528-8b-FLM" in labels, "iGPU must use deepseek-r1-0528-8b-FLM"
    assert "direct:Gemma-4-31B-it-GGUF" in labels, "CPU tier must use Gemma-4-31B"


def test_build_triune_orchestrator_quality_gates():
    """Quality gates: NPU=1, iGPU=5, CPU=10 (direct HTTP tiers, exp_OOOO3)."""
    orch = _build_local_only()
    assert orch.tiers[0][1].min_chars == 1  # NPU: accept any non-trivial response
    assert orch.tiers[1][1].min_chars == 5  # iGPU: slightly stricter
    assert orch.tiers[2][1].min_chars == 10  # CPU: AVX-512 fallback


def test_build_triune_orchestrator_pre_dispatch_classifier_wired():
    """pre_dispatch_classifier must be a PrefillActivationRouter wrapping task_classifier.classify."""
    orch = _build_local_only()
    assert isinstance(orch._pre_dispatch_classifier, PrefillActivationRouter), (
        "pre_dispatch_classifier must be PrefillActivationRouter"
    )
    assert orch._pre_dispatch_classifier.base_classifier is classify_task, (
        "pre_dispatch_classifier's base must be wired to task_classifier.classify — "
        "without it, categorical tasks get gate=1 and escalate to iGPU unnecessarily"
    )


def test_build_triune_orchestrator_npu_first():
    """NPU at tier 0, iGPU at tier 1, CPU at tier 2 — cheapest first."""
    orch = _build_local_only()
    assert orch.tiers[0][0].label == "direct:llama3.2-1b-FLM", "NPU must be tier 0"
    assert orch.tiers[1][0].label == "direct:deepseek-r1-0528-8b-FLM", "iGPU must be tier 1"
    assert orch.tiers[2][0].label == "direct:Gemma-4-31B-it-GGUF", "CPU must be tier 2"


def test_build_triune_orchestrator_cloud_tiers():
    """With include_cloud=True, 5-tier tapestry: NPU+iGPU+CPU+Haiku+Sonnet."""
    with patch(_OOM_GUARD_PATH) as mock_ms:
        mock_ms.capture.return_value = _sufficient_ram()
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


def test_pre_dispatch_classifier_property_setter():
    """pre_dispatch_classifier property setter must update _pre_dispatch_classifier (exp_NNNN4)."""
    orch = _build_local_only()
    assert isinstance(orch._pre_dispatch_classifier, PrefillActivationRouter)
    assert orch._pre_dispatch_classifier.base_classifier is classify_task
    # Public property setter must route to private attribute
    orch.pre_dispatch_classifier = None
    assert orch._pre_dispatch_classifier is None, (
        "Property setter must update _pre_dispatch_classifier to avoid public/private mismatch "
        "(exp_NNNN4: setting orc.pre_dispatch_classifier = None had no effect before this fix)"
    )
