"""Fleet model registry - single source of truth for lane x model x task affinity.

Maps the Strix Halo Symphony (4-lane Gemma 4 deployment) plus specialist task
models and cloud fallbacks into a unified table that every other module in
``cohezion.inference`` consumes.

Lane layout (per STRIX_HALO_SYMPHONY_GUIDE.md):

============  ======  ================================  ===============================
Lane          Port    Model                             Role (manifest translation)
============  ======  ================================  ===============================
NPU XDNA2     13306   Gemma-4-E2B-it-GGUF               Sensing (Fire by Friction / Doer)
iGPU ROCWMMA  13307   Gemma-4-E4B-it-GGUF               Steering (Governance / Knower)
iGPU Unified  13308   Gemma-4-26B-A4B-it-GGUF (MoE)     Building (Solar Fire / Thinker)
CPU AVX-VNNI  13309   Gemma-4-31B-it-GGUF               Architect (Safety)
============  ======  ================================  ===============================

Task affinity informs ``fleet.route()`` when the caller doesn't pin a model.
Cost in USD/1K tokens is zero for local lanes and used for ``extend_claude``
budget accounting on the cloud fallbacks.

Phase 1 of the TurboQuant plan split the old ``quantization: str`` field into
two orthogonal axes:
  * ``weight_quant: WeightQuant`` — how model weights are stored (INT4, MXFP4, API, ...).
  * ``kv_quant: KVQuant`` — how the KV cache is compressed at inference time
    (scheme=none / turboquant / quarot / kv8, bits, rotation size, etc.).
Old readers get a legacy ``.quantization`` property that composes the two
into the ``"{weight}+{scheme}"`` string they used to read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal


class Lane(StrEnum):
    NPU = "npu"
    IGPU_ROCWMMA = "igpu_rocwmma"
    IGPU_UNIFIED = "igpu_unified"
    CPU = "cpu"
    CLOUD_OLLAMA = "cloud_ollama"
    CLOUD_CLAUDE = "cloud_claude"  # headless `claude` CLI
    CLOUD_GEMINI = "cloud_gemini"  # headless `gemini` CLI


class Task(StrEnum):
    SENSING = "sensing"
    ROUTING = "routing"
    SUMMARIZATION = "summarization"
    STRUCTURED = "structured"
    GOVERNANCE = "governance"
    REASONING = "reasoning"
    CODE_GEN = "code_gen"
    MATH = "math"
    LONG_HORIZON = "long_horizon"
    ARCHITECT = "architect"
    GENERAL = "general"


class WeightQuant(StrEnum):
    """How model weights are stored on disk / loaded into the runtime."""

    INT4 = "int4"
    INT8 = "int8"
    Q4_K_M = "q4_k_m"
    Q5_K_M = "q5_k_m"
    MXFP4 = "mxfp4"
    BF16 = "bf16"
    FP16 = "fp16"
    QUAROT_INT4 = "quarot_int4"  # INT4 with a QuaRot Hadamard rotation baked in (Phase 4)
    API = "api"  # cloud-hosted; weight quant is whatever the provider uses


@dataclass
class KVQuant:
    """How the attention KV cache is compressed at inference time.

    Orthogonal to ``WeightQuant`` — TurboQuant (ICLR 2026, arXiv:2504.19874) is
    a KV-cache-only algorithm, so weight and KV quant can be mixed independently.
    """

    scheme: Literal["none", "turboquant", "quarot", "kv8"] = "none"
    bits: float = 16.0
    hadamard_size: int = 128
    qjl_correction: bool = False
    asymmetric_kv: bool = False  # K rotated, V passed through (dense models)
    runtime_flag: dict[str, str] = field(default_factory=dict)
    """Map of runtime name → CLI flag value, e.g.
    ``{"vllm": "tbq4", "llama.cpp": "turbo3", "sglang": "tbq4"}``.
    Lets ``fleet.py`` emit the right token per backend without per-runtime
    special cases at the call site.
    """


@dataclass
class ModelEntry:
    """A single model available to the fleet.

    Latency fields are empirical observations, not vendor claims. They feed the
    benchmark harness and drive `fleet.route()` when a caller sets
    `prefer_latency=True` (future) or when two candidates tie on priority.
    """

    model_id: str
    lane: Lane
    endpoint: str
    runtime_backend: (
        str  # "flm" | "vllm_rocm" | "llamacpp_hip" | "sglang_triton" | "cpu" | "" for cloud
    )
    task_affinity: frozenset[Task]
    weight_quant: WeightQuant
    context_window: int
    kv_quant: KVQuant = field(default_factory=KVQuant)
    cost_per_1k_input_usd: float = 0.0
    cost_per_1k_output_usd: float = 0.0
    priority: int = 100  # lower = preferred
    verified_working: bool = False
    last_verified_at: datetime | None = None
    # Empirical latency targets (milliseconds) — populated from benchmark runs.
    # None = not yet measured. Used by the benchmark harness and for
    # latency-first routing policies.
    observed_ttft_ms_p50: float | None = None  # 50th percentile time-to-first-token
    observed_ttft_ms_p95: float | None = None  # 95th percentile TTFT
    observed_total_ms_p50: float | None = None  # 50th percentile full-response latency
    observed_tokens_per_sec: float | None = None  # sustained generation throughput
    # Reasoning-mode models (e.g. Gemma 4 FLM) emit <thinking> tokens first and
    # only then produce visible output. With small `max_tokens` budgets the
    # thinking block consumes the whole budget and the caller sees empty text.
    # route() uses this flag to emit a warning when max_tokens is too small for
    # a reasoning-mode lane (local_environment_quirks.md: "reasoning models
    # need max_tokens >= 128 headroom").
    reasoning_mode: bool = False
    notes: str = ""

    @property
    def quantization(self) -> str:
        """Legacy accessor — composes ``weight_quant`` + ``kv_quant.scheme``.

        Returned as ``"{weight}"`` when the KV scheme is ``"none"`` (no
        compression), else ``"{weight}+{scheme}"`` — matching the pre-Phase-1
        strings like ``"INT4+turboquant"`` so external readers keep working.
        """
        weight = self.weight_quant.value
        if self.kv_quant.scheme == "none":
            return weight
        return f"{weight}+{self.kv_quant.scheme}"


def _build_default_registry() -> dict[str, ModelEntry]:
    """The Strix Halo Symphony fleet plus specialists and cloud fallbacks."""
    # TurboQuant KV preset for the iGPU lanes. 3.5-bit matches ICLR 2026
    # paper's FP16-parity point; 4-bit adds safety margin for MoE / long context.
    tbq_35 = KVQuant(
        scheme="turboquant",
        bits=3.5,
        hadamard_size=128,
        qjl_correction=True,
        asymmetric_kv=True,
        runtime_flag={"llama.cpp": "turbo3", "vllm": "tbq4", "sglang": "tbq4"},
    )
    tbq_40 = KVQuant(
        scheme="turboquant",
        bits=4.0,
        hadamard_size=128,
        qjl_correction=True,
        asymmetric_kv=False,
        runtime_flag={"vllm": "tbq4", "llama.cpp": "turbo3", "sglang": "tbq4"},
    )

    entries: list[ModelEntry] = [
        # --- Strix Halo Symphony: 4-lane Gemma 4 ---
        ModelEntry(
            model_id="Gemma-4-E2B-it-GGUF",
            lane=Lane.NPU,
            endpoint="http://localhost:13306",
            runtime_backend="flm",
            task_affinity=frozenset({Task.SENSING, Task.ROUTING, Task.SUMMARIZATION}),
            weight_quant=WeightQuant.INT4,
            kv_quant=KVQuant(),  # AMD Ryzen AI compiler has no TBQ op as of 1.7.1
            context_window=8192,
            priority=10,
            # SCIENTIFIC RIGOR: typed p50/p95 fields require n>=20 per the
            # 2026-04-18 review. Earlier 5-call warm-loop observations moved
            # to notes as informal. Re-populate typed fields only from a full
            # 20-prompt benchmark run (make benchmark-fleet --prompts 20).
            verified_working=True,
            reasoning_mode=True,
            notes=(
                "Fire by Friction (Doer) — manifest NPU lane. "
                "Informal 5-call warm-loop 2026-04-18: TTFT ~80ms, total ~200ms. "
                "NOT a statistically valid p50/p95; see benchmarks/fleet_report.md "
                "for the harness-verified numbers. Reasoning-mode: emits "
                "delta.reasoning_content before delta.content."
            ),
        ),
        ModelEntry(
            model_id="Gemma-4-E4B-it-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # upstream llama.cpp PR #20969
            task_affinity=frozenset({Task.STRUCTURED, Task.GOVERNANCE}),
            weight_quant=WeightQuant.Q4_K_M,
            kv_quant=tbq_35,
            context_window=16384,
            priority=20,
            reasoning_mode=True,
            notes="Electric Fire (Knower) — Governance / Steering",
        ),
        ModelEntry(
            model_id="Gemma-4-26B-A4B-it-GGUF",
            lane=Lane.IGPU_UNIFIED,
            endpoint="http://localhost:13308",
            runtime_backend="vllm_rocm",  # vLLM-rocm nightly with --kv-cache-dtype tbq4
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.GENERAL}),
            weight_quant=WeightQuant.MXFP4,
            kv_quant=tbq_40,
            context_window=32768,
            priority=15,
            reasoning_mode=True,
            notes="Solar Fire (Thinker) — 26B MoE, 4B active params",
        ),
        ModelEntry(
            model_id="Gemma-4-31B-it-GGUF",
            lane=Lane.CPU,
            endpoint="http://localhost:13309",
            runtime_backend="cpu",
            task_affinity=frozenset({Task.ARCHITECT, Task.LONG_HORIZON}),
            weight_quant=WeightQuant.Q4_K_M,
            kv_quant=KVQuant(),  # No public AVX-512 TBQ kernels exist (April 2026)
            context_window=32768,
            priority=40,
            reasoning_mode=True,
            notes="Safety / System Architect — AVX-VNNI",
        ),
        # --- Task-specialist models via Ollama (:11434) ---
        ModelEntry(
            model_id="phi4:latest",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.REASONING, Task.GENERAL}),
            weight_quant=WeightQuant.Q4_K_M,
            context_window=16384,
            priority=50,
            verified_working=True,
            notes="Verified live via Ollama :11434",
        ),
        ModelEntry(
            model_id="qwen3-coder:30b",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.CODE_GEN}),
            weight_quant=WeightQuant.Q4_K_M,
            context_window=32768,
            priority=30,
            notes="Code generation specialist",
        ),
        ModelEntry(
            model_id="deepseek-r1:70b",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.LONG_HORIZON, Task.REASONING}),
            weight_quant=WeightQuant.Q4_K_M,
            context_window=32768,
            priority=45,
            reasoning_mode=True,
            notes="Long-horizon reasoning (deepseek-r1 emits <think> blocks)",
        ),
        # --- Cloud Ollama fallbacks (confirmed in registry) ---
        ModelEntry(
            model_id="deepseek-v3.2:cloud",
            lane=Lane.CLOUD_OLLAMA,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN}),
            weight_quant=WeightQuant.API,
            context_window=131072,
            cost_per_1k_input_usd=0.0002,
            cost_per_1k_output_usd=0.0006,
            priority=70,
            verified_working=True,
            notes="671B deepseek-v3.2 via ollama cloud",
        ),
        ModelEntry(
            model_id="gemini-3-flash-preview:cloud",
            lane=Lane.CLOUD_OLLAMA,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION}),
            weight_quant=WeightQuant.API,
            context_window=1000000,
            cost_per_1k_input_usd=0.0001,
            cost_per_1k_output_usd=0.0004,
            priority=65,
            verified_working=True,
            notes="Gemini 3 Flash via ollama cloud",
        ),
        # --- Headless `claude` CLI (Claude Code) ---
        # Endpoint "cli:claude" indicates subprocess invocation, not HTTP.
        ModelEntry(
            model_id="claude-haiku-4-5",
            lane=Lane.CLOUD_CLAUDE,
            endpoint="cli:claude",
            runtime_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION}),
            weight_quant=WeightQuant.API,
            context_window=200000,
            cost_per_1k_input_usd=0.001,
            cost_per_1k_output_usd=0.005,
            priority=80,
            # Typical Claude API TTFT (network + model) per Anthropic docs.
            observed_ttft_ms_p50=600.0,
            observed_ttft_ms_p95=1500.0,
            observed_total_ms_p50=1500.0,
            notes="Haiku 4.5 via headless `claude -p --model haiku-4-5`",
        ),
        ModelEntry(
            model_id="claude-sonnet-4-6",
            lane=Lane.CLOUD_CLAUDE,
            endpoint="cli:claude",
            runtime_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.ARCHITECT}),
            weight_quant=WeightQuant.API,
            context_window=200000,
            cost_per_1k_input_usd=0.003,
            cost_per_1k_output_usd=0.015,
            priority=90,
            notes="Sonnet 4.6 via headless `claude -p --model sonnet-4-6`",
        ),
        ModelEntry(
            model_id="claude-opus-4-7",
            lane=Lane.CLOUD_CLAUDE,
            endpoint="cli:claude",
            runtime_backend="",
            task_affinity=frozenset({Task.REASONING, Task.LONG_HORIZON, Task.ARCHITECT}),
            weight_quant=WeightQuant.API,
            context_window=200000,
            cost_per_1k_input_usd=0.015,
            cost_per_1k_output_usd=0.075,
            priority=100,
            notes="Opus 4.7 via headless `claude -p --model opus-4-7`",
        ),
        # --- Headless `gemini` CLI ---
        ModelEntry(
            model_id="gemini-3-flash",
            lane=Lane.CLOUD_GEMINI,
            endpoint="cli:gemini",
            runtime_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION, Task.ROUTING}),
            weight_quant=WeightQuant.API,
            context_window=1000000,
            cost_per_1k_input_usd=0.0001,
            cost_per_1k_output_usd=0.0004,
            priority=75,
            notes="Gemini 3 Flash via headless `gemini -p -m gemini-3-flash -o json`",
        ),
        ModelEntry(
            model_id="gemini-3-pro",
            lane=Lane.CLOUD_GEMINI,
            endpoint="cli:gemini",
            runtime_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.LONG_HORIZON}),
            weight_quant=WeightQuant.API,
            context_window=2000000,
            cost_per_1k_input_usd=0.00125,
            cost_per_1k_output_usd=0.005,
            priority=85,
            notes="Gemini 3 Pro via headless `gemini -p -m gemini-3-pro -o json`",
        ),
    ]
    return {entry.model_id: entry for entry in entries}


@dataclass
class FleetRegistry:
    """Registry of all models x lanes x tasks. Instantiated as a module singleton."""

    models: dict[str, ModelEntry] = field(default_factory=_build_default_registry)

    def for_task(self, task: Task) -> list[ModelEntry]:
        """Candidates for a task, sorted by priority (lowest first = preferred)."""
        return sorted(
            (m for m in self.models.values() if task in m.task_affinity),
            key=lambda m: m.priority,
        )

    def by_lane(self, lane: Lane) -> list[ModelEntry]:
        return [m for m in self.models.values() if m.lane == lane]

    def local_only(self) -> list[ModelEntry]:
        local_lanes = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
        return [m for m in self.models.values() if m.lane in local_lanes]

    def mark_verified(self, model_id: str) -> None:
        if model_id in self.models:
            self.models[model_id].verified_working = True
            self.models[model_id].last_verified_at = datetime.now()


_registry: FleetRegistry | None = None


def get_registry() -> FleetRegistry:
    """Module singleton accessor."""
    global _registry
    if _registry is None:
        _registry = FleetRegistry()
    return _registry
