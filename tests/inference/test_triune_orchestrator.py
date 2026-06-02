from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from cohezion.inference.task_classifier import classify as classify_task
from cohezion.inference.triune_orchestrator import build_triune_orchestrator


def _mock_gaia_tier(model_id: str, **_kwargs):
    tier = MagicMock()
    tier.label = f"gaia:{model_id}"
    return tier


@contextmanager
def _mock_tiers():
    """Mock build_gaia_native_tier at BOTH import sites so the build is fully offline.

    The NPU/CPU tiers resolve it from the triune_orchestrator module; the default
    CLaSp iGPU tier resolves it (function-local) from gaia_adapter. Patching only the
    former leaves the CLaSp path importing real `gaia` — which fails where amd-gaia
    is not installed (e.g. CI).
    """
    with (
        patch(
            "cohezion.inference.triune_orchestrator.build_gaia_native_tier",
            side_effect=_mock_gaia_tier,
        ),
        patch(
            "cohezion.inference.gaia_adapter.build_gaia_native_tier",
            side_effect=_mock_gaia_tier,
        ),
    ):
        yield


def test_build_triune_orchestrator_structure():
    """Verify the orchestrator is built with 3 tiers using correct model IDs (N2 invariant)."""
    with _mock_tiers():
        orch = build_triune_orchestrator()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    # N2 invariant: NPU must use llama3.2-1b-FLM (fits XDNA2 SRAM, 42 TPS)
    # NOT qwen3.5-4b-FLM (spills to system RAM, 8.6 TPS — 5x slower)
    assert "gaia:llama3.2-1b-FLM" in labels, "N2: NPU tier must use llama3.2-1b-FLM"
    assert "gaia:qwen3.5-4b-FLM" not in labels, "N2: qwen3.5-4b-FLM is banned from NPU tier"
    assert "gaia:Gemma-4-31B-it-GGUF" in labels, "CPU tier must be Gemma-4-31B"
    # iGPU tier is the CLaSp speculative-decoding tier by default (clasp_draft_port=13308):
    # E2B drafts, E4B verifies. The label must identify both, and the verify model is E4B.
    igpu_label = labels[1]
    assert igpu_label.startswith("clasp:"), f"iGPU tier must be CLaSp by default, got {igpu_label}"
    assert "Gemma-4-E2B-it-GGUF" in igpu_label, "CLaSp draft model must be E2B"
    assert "Gemma-4-E4B-it-GGUF" in igpu_label, "CLaSp verify model must be E4B"


def test_build_triune_orchestrator_quality_gates():
    """Verify the quality gates."""
    with _mock_tiers():
        orch = build_triune_orchestrator()
    assert orch.tiers[0][1].min_chars == 500  # NPU: solid start
    assert orch.tiers[1][1].min_chars == 750  # iGPU: calibrated (EXP-ROUTE-12)
    assert orch.tiers[2][1].min_chars is None  # CPU: TRUST (guaranteed completion)


def test_build_triune_orchestrator_pre_dispatch_classifier_wired():
    """pre_dispatch_classifier must be the task_classifier.classify function."""
    with _mock_tiers():
        orch = build_triune_orchestrator()
    assert orch._pre_dispatch_classifier is classify_task, (
        "pre_dispatch_classifier must be wired to task_classifier.classify — "
        "without it, categorical tasks get gate=500 and escalate to iGPU unnecessarily"
    )


def test_build_triune_orchestrator_npu_first():
    """NPU tier must be at index 0 — cheapest, fastest tier runs first."""
    with _mock_tiers():
        orch = build_triune_orchestrator()
    assert orch.tiers[0][0].label == "gaia:llama3.2-1b-FLM", "NPU must be tier 0"
    assert orch.tiers[1][0].label.startswith("clasp:"), "iGPU (CLaSp) must be tier 1"
    assert "Gemma-4-E4B-it-GGUF" in orch.tiers[1][0].label, "iGPU CLaSp must verify with E4B"
    assert orch.tiers[2][0].label == "gaia:Gemma-4-31B-it-GGUF", "CPU must be tier 2"
