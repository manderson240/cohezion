from unittest.mock import MagicMock, patch

from cohezion.inference.activation_router import PrefillActivationRouter
from cohezion.inference.task_classifier import classify as classify_task
from cohezion.inference.triune_orchestrator import build_triune_orchestrator


def _sufficient_ram():
    """Mock MemorySnapshot.capture() to return RAM sufficient for all local tiers.

    64 GB clears both the 16 GB top-level OOM buffer and the per-CPU-tier gate
    (16 GB buffer + ~20 GB for the Gemma-4-31B reasoner = 36 GB).
    """
    snap = MagicMock()
    snap.available_gb = 64.0
    return snap


_OOM_GUARD_PATH = "cohezion.competition.orchestrator.resource_guard.MemorySnapshot"
_CHECK_PORT_PATH = "cohezion.inference.triune_orchestrator._check_port"


def _build_local_only(**kwargs):
    """Build with cloud=False and no CLaSp so all tiers go through direct HTTP.

    Patches _check_port→True so the CPU tier selects the direct :13309 path (the test
    env has no live :13309 server; without this it would fall back to the router :13305
    path and the tier label would be ``router:`` not ``direct:``). This controls topology
    the same way ``clasp_draft_port=None`` controls the iGPU path — it does not change
    what the assertions verify.
    """
    with patch(_OOM_GUARD_PATH) as mock_ms, patch(_CHECK_PORT_PATH, return_value=True):
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


# ── Reasoning lane escalation + router-CPU tier (Task 1+2) ──────────────────

import asyncio

from cohezion.inference.direct_tier import RouterCpuTier, build_router_cpu_tier
from cohezion.inference.orchestrator import OrchestrationResult, QualityGate, TieredOrchestrator
from cohezion.inference.task_classifier import classify


class _FakeTier:
    """Mock tier returning a fixed text, recording whether it ran."""

    def __init__(self, label, text):
        self.label = label
        self.text = text
        self.ran = False

    async def run(self, prompt, **kwargs):
        self.ran = True
        return OrchestrationResult(
            text=self.text,
            primary_model=self.label,
            final_model=self.label,
            escalation_count=0,
            tier_path=[],
            cost_usd=0.0,
            latency_ms=1.0,
            ttft_ms=None,
            error=None,
        )


def test_reasoning_prompt_reaches_cpu_even_when_igpu_is_verbose():
    """DISCRIMINATING: the iGPU model (deepseek-r1) is a thinking model that emits long
    chain-of-thought — a verbose-but-shallow iGPU answer (3000 chars) would PASS a length
    gate and be trusted at the mid tier. The start-tier=CPU mechanism guarantees reasoning
    bypasses iGPU ENTIRELY and reaches the CPU reasoner regardless of iGPU verbosity.

    A wrong implementation that relies only on gate=2000 would let this 3000-char iGPU
    answer through → cpu.ran would be False. This test fails that wrong implementation."""
    npu = _FakeTier("direct:llama3.2-1b-FLM", "npu answer")
    # Verbose iGPU answer: 3000 chars — would PASS any reasonable length gate.
    igpu = _FakeTier("direct:deepseek-r1-0528-8b-FLM", "x" * 3000)
    cpu = _FakeTier("router:Gemma-4-31B-it-GGUF", "the reasoned CPU answer " * 30)

    orch = TieredOrchestrator(
        tiers=[
            (npu, QualityGate(min_chars=1)),
            (igpu, QualityGate(min_chars=5)),
            (cpu, QualityGate(min_chars=10)),
        ],
        pre_dispatch_classifier=classify,  # reasoning → node=gpu, start_tier=CPU
    )

    prompt = "Analyze the tradeoffs between Redis and Memcached and recommend one."
    result = asyncio.run(orch.run(prompt))

    assert not npu.ran, "reasoning is node=gpu → NPU (tier 0) must be skipped"
    assert not igpu.ran, (
        "reasoning must BYPASS iGPU entirely — a verbose iGPU answer must NOT intercept "
        "(deepseek-r1 emits long CoT; a length gate alone would trust it)"
    )
    assert cpu.ran, "the CPU reasoner must run as the start tier for reasoning"
    assert result.final_model == "router:Gemma-4-31B-it-GGUF"
    # Only the CPU tier (index 2) appears in the path.
    assert all(p.tier_index == 2 for p in result.tier_path)


def test_reasoning_falls_back_to_last_tier_when_cpu_omitted():
    """Clamp guard: when the CPU tier is absent (RAM-omitted) and no cloud, start_tier
    clamps to the last available tier so reasoning still runs something (iGPU as last
    resort) rather than exhausting with empty text."""
    npu = _FakeTier("direct:llama3.2-1b-FLM", "npu answer")
    igpu = _FakeTier("direct:deepseek-r1-0528-8b-FLM", "the reasoned iGPU answer " * 20)

    orch = TieredOrchestrator(
        tiers=[(npu, QualityGate(min_chars=1)), (igpu, QualityGate(min_chars=5))],
        pre_dispatch_classifier=classify,
    )
    result = asyncio.run(orch.run("Compare the tradeoffs of optimistic vs pessimistic locking."))
    assert not npu.ran, "NPU still skipped for reasoning"
    assert igpu.ran, "start_tier clamps to last tier (iGPU) when CPU/cloud absent"
    assert result.error is None and result.text


def test_router_cpu_tier_is_bounded_ctx_and_cpu_backend():
    """N3: the router-CPU tier carries a bounded ctx_size (≤16384) and llamacpp_backend=cpu."""
    tier = build_router_cpu_tier()
    assert isinstance(tier, RouterCpuTier)
    assert tier.port == 13305, "router-CPU tier targets the unified router :13305"
    assert tier.backend == "cpu"
    assert 1 <= tier.ctx_size <= 16384, "N3: ctx must be bounded ≤16384, never 0"
    assert tier.label == "router:Gemma-4-31B-it-GGUF"


def test_router_cpu_tier_clamps_oversized_ctx():
    """N3 guard: an oversized ctx request is clamped to the 16384 ceiling."""
    tier = build_router_cpu_tier(ctx_size=999999)
    assert tier.ctx_size == 16384


def test_router_cpu_tier_preload_uses_load_endpoint_with_bounded_ctx():
    """RouterCpuTier pre-loads via POST :13305/api/v1/load with bounded ctx before chat (N3)."""
    from unittest.mock import MagicMock, patch

    tier = build_router_cpu_tier()
    captured = {}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, **k):
            captured["url"] = url
            captured["json"] = json
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(
                return_value={"choices": [{"message": {"content": "reasoned answer"}}]}
            )
            return resp

    with patch("httpx.AsyncClient", _FakeClient):
        # First post is the /api/v1/load (we only assert the load happened with bounded ctx).
        asyncio.run(tier._ensure_loaded())

    assert captured["url"].endswith("/api/v1/load")
    assert captured["json"]["llamacpp_backend"] == "cpu"
    assert captured["json"]["ctx_size"] == 16384
    assert captured["json"]["save_options"] is True


def _low_ram():
    snap = MagicMock()
    snap.available_gb = 8.0  # below 16+20 → CPU reasoner must be omitted
    return snap


def test_cpu_reasoner_omitted_when_ram_unsafe():
    """OOM gate (N3): when RAM is unsafe the 31B CPU reasoner is omitted so reasoning
    escalates to cloud rather than risk an OOM hang."""
    with patch(_OOM_GUARD_PATH) as mock_ms, patch(_CHECK_PORT_PATH, return_value=True):
        mock_ms.capture.return_value = _low_ram()
        orch = build_triune_orchestrator(include_cloud=True, clasp_draft_port=None)
    labels = [t[0].label if hasattr(t[0], "label") else t[0] for t in orch.tiers]
    assert "router:Gemma-4-31B-it-GGUF" not in labels
    assert "direct:Gemma-4-31B-it-GGUF" not in labels, "CPU reasoner must be omitted (RAM unsafe)"
    # Cloud tiers remain so reasoning still has an escalation target.
    assert "claude-haiku-4-5" in labels


def test_cpu_reasoner_falls_back_to_router_when_direct_port_down():
    """When the dedicated :13309 server is down, the CPU tier uses the router :13305 path."""
    with patch(_OOM_GUARD_PATH) as mock_ms, patch(_CHECK_PORT_PATH, return_value=False):
        mock_ms.capture.return_value = _sufficient_ram()
        orch = build_triune_orchestrator(include_cloud=False, clasp_draft_port=None)
    labels = [t[0].label for t in orch.tiers]
    assert "router:Gemma-4-31B-it-GGUF" in labels, "direct :13309 down → router CPU path"
    assert "direct:Gemma-4-31B-it-GGUF" not in labels
