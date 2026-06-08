from unittest.mock import MagicMock, patch

from cohezion.compound.fleet_client import RouterModelInfo
from cohezion.inference.activation_router import PrefillActivationRouter
from cohezion.inference.task_classifier import classify as classify_task
from cohezion.inference.triune_orchestrator import build_triune_orchestrator

_OOM_GUARD_PATH = "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"
# Patch the class in its defining module; local import inside build_triune_orchestrator
# picks up the patched version because the binding is created at call time.
_ROUTER_CLIENT_PATH = "cohezion.compound.fleet_client.LemonadeRouterClient"


def _sufficient_ram():
    """Mock MemorySnapshot.capture() to return sufficient RAM (32 GB) for local tiers."""
    snap = MagicMock()
    snap.available_gb = 32.0
    return snap


def _make_router_mock(hot_models=None):
    """Return a mock LemonadeRouterClient with all three tiers hot by default."""
    if hot_models is None:
        hot_models = [
            RouterModelInfo("llama3.2-1b-FLM", "npu", "http://localhost:13305", 0),
            RouterModelInfo("Granite-4.1-8B-GGUF", "gpu", "http://localhost:13305", 0),
            RouterModelInfo("Gemma-4-31B-it-GGUF", "cpu", "http://localhost:13305", 0),
        ]
    mock_router = MagicMock()
    mock_router.available.return_value = True
    mock_router.hot_models.return_value = hot_models
    mock_router.port = 13305
    return mock_router


def _build_local_only(hot_models=None, **kwargs):
    """Build with cloud=False; mock router to report tiers as hot."""
    with patch(_OOM_GUARD_PATH) as mock_ms, patch(_ROUTER_CLIENT_PATH) as mock_cls:
        mock_ms.capture.return_value = _sufficient_ram()
        mock_cls.return_value = _make_router_mock(hot_models)
        return build_triune_orchestrator(include_cloud=False, clasp_draft_port=None, **kwargs)


def test_build_triune_orchestrator_structure():
    """3 local tiers with correct model IDs (N2 invariant). Labels use router: prefix.

    Router-centric topology (2026-06-07): tiers built from hot-model catalog on :13305.
    RouterLemonadeTier.label format: ``router:<model>@:<port>``.
    """
    orch = _build_local_only()
    assert len(orch.tiers) == 3
    labels = [tier[0].label for tier in orch.tiers]
    # N2: NPU must use llama3.2-1b-FLM (fits XDNA2 SRAM, 42 TPS — NOT qwen3.5-4b-FLM at 8.6 TPS)
    assert "router:llama3.2-1b-FLM@:13305" in labels, "N2: NPU tier must use llama3.2-1b-FLM"
    assert not any("qwen3.5-4b-FLM" in lbl for lbl in labels), "N2: qwen3.5-4b-FLM is banned"
    # iGPU: first hot candidate from _IGPU_MODELS (Granite-4.1-8B-GGUF in mock)
    assert "router:Granite-4.1-8B-GGUF@:13305" in labels, "iGPU must be Granite-4.1-8B-GGUF"
    # CPU: Gemma-4-31B (first hot candidate from _CPU_MODELS in mock)
    assert "router:Gemma-4-31B-it-GGUF@:13305" in labels, "CPU tier must use Gemma-4-31B"


def test_build_triune_orchestrator_quality_gates():
    """Quality gates: NPU=1, iGPU=5, CPU=10 (router tiers, exp_OOOO3)."""
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
    """NPU at tier 0, iGPU at tier 1, CPU at tier 2 — cheapest first (router labels)."""
    orch = _build_local_only()
    assert orch.tiers[0][0].label == "router:llama3.2-1b-FLM@:13305", "NPU must be tier 0"
    assert orch.tiers[1][0].label == "router:Granite-4.1-8B-GGUF@:13305", "iGPU must be tier 1"
    assert orch.tiers[2][0].label == "router:Gemma-4-31B-it-GGUF@:13305", "CPU must be tier 2"


def test_build_triune_orchestrator_cloud_tiers():
    """With include_cloud=True, 5-tier tapestry: NPU+iGPU+CPU+Haiku+Sonnet."""
    with patch(_OOM_GUARD_PATH) as mock_ms, patch(_ROUTER_CLIENT_PATH) as mock_cls:
        mock_ms.capture.return_value = _sufficient_ram()
        mock_cls.return_value = _make_router_mock()
        orch = build_triune_orchestrator(include_cloud=True, clasp_draft_port=None)
    assert len(orch.tiers) == 5, "5-tier tapestry: 3 local + Haiku + Sonnet"
    cloud_ids = [t[0] for t in orch.tiers[3:]]
    assert "claude-haiku-4-5" in cloud_ids
    assert "claude-sonnet-4-6" in cloud_ids


def test_build_triune_orchestrator_cpu_port_lemonade():
    """N2 invariant: cpu_port default must be 13309 (lemonade fallback), not 11434 (Ollama)."""
    import inspect

    sig = inspect.signature(build_triune_orchestrator)
    cpu_port_default = sig.parameters["cpu_port"].default
    assert cpu_port_default == 13309, (
        f"N2: cpu_port default must be 13309 (lemonade fallback), got {cpu_port_default}. "
        "Ollama (11434) no longer serves the CPU tier — migrated 2026-05-21."
    )


def test_build_triune_orchestrator_router_port_default():
    """Router port default must be 13305 (unified Lemonade router, 2026-06-07)."""
    import inspect

    sig = inspect.signature(build_triune_orchestrator)
    router_port_default = sig.parameters["router_port"].default
    assert router_port_default == 13305, (
        f"router_port default must be 13305 (unified Lemonade router), got {router_port_default}."
    )


def test_build_triune_orchestrator_path_b_fallback():
    """PATH B (direct ports) fires when router is unreachable."""
    # direct_tier functions are imported locally inside build_triune_orchestrator PATH B branch;
    # patch them at their defining module so the local binding sees the mock.
    with (
        patch(_OOM_GUARD_PATH) as mock_ms,
        patch(_ROUTER_CLIENT_PATH) as mock_cls,
        patch("cohezion.inference.direct_tier.build_direct_npu_tier") as mock_npu,
        patch("cohezion.inference.direct_tier.build_direct_igpu_tier") as mock_igpu,
        patch("cohezion.inference.direct_tier.build_direct_cpu_tier") as mock_cpu,
    ):
        mock_ms.capture.return_value = _sufficient_ram()
        mock_router = MagicMock()
        mock_router.available.return_value = False  # router unreachable → PATH B
        mock_cls.return_value = mock_router
        mock_npu.return_value = MagicMock(label="direct:llama3.2-1b-FLM")
        mock_igpu.return_value = MagicMock(label="direct:deepseek-r1-0528-8b-FLM")
        mock_cpu.return_value = MagicMock(label="direct:Gemma-4-31B-it-GGUF")
        orch = build_triune_orchestrator(include_cloud=False, clasp_draft_port=None)
    assert len(orch.tiers) == 3, "PATH B must produce 3 direct-port tiers"
    labels = [t[0].label for t in orch.tiers]
    assert "direct:llama3.2-1b-FLM" in labels
    assert "direct:Gemma-4-31B-it-GGUF" in labels


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
