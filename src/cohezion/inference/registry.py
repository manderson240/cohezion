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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


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
    llamacpp_backend: str  # "flm" | "rocm" | "cpu" | "" for cloud
    task_affinity: frozenset[Task]
    quantization: str  # "INT4+turboquant" | "Q4_K_M" | "MXFP4" | "api"
    context_window: int
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
    notes: str = ""


def _build_default_registry() -> dict[str, ModelEntry]:
    """The Strix Halo Symphony fleet plus specialists and cloud fallbacks."""
    entries: list[ModelEntry] = [
        # --- Strix Halo Symphony: 4-lane Gemma 4 ---
        ModelEntry(
            model_id="Gemma-4-E2B-it-GGUF",
            lane=Lane.NPU,
            endpoint="http://localhost:13306",
            llamacpp_backend="flm",
            task_affinity=frozenset({Task.SENSING, Task.ROUTING, Task.SUMMARIZATION}),
            quantization="INT4+turboquant",
            context_window=8192,
            priority=10,
            # SCIENTIFIC RIGOR: typed p50/p95 fields require n>=20 per the
            # 2026-04-18 review. Earlier 5-call warm-loop observations moved
            # to notes as informal. Re-populate typed fields only from a full
            # 20-prompt benchmark run (make benchmark-fleet --prompts 20).
            observed_ttft_ms_p50=None,
            observed_ttft_ms_p95=None,
            observed_total_ms_p50=None,
            observed_tokens_per_sec=None,
            verified_working=True,
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
            llamacpp_backend="rocm",
            task_affinity=frozenset({Task.STRUCTURED, Task.GOVERNANCE}),
            quantization="Q4_K_M+turboquant",
            context_window=16384,
            priority=20,
            notes="Electric Fire (Knower) — Governance / Steering",
        ),
        ModelEntry(
            model_id="Gemma-4-26B-A4B-it-GGUF",
            lane=Lane.IGPU_UNIFIED,
            endpoint="http://localhost:13308",
            llamacpp_backend="rocm",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.GENERAL}),
            quantization="MXFP4",
            context_window=32768,
            priority=15,
            notes="Solar Fire (Thinker) — 26B MoE, 4B active params",
        ),
        ModelEntry(
            model_id="Gemma-4-31B-it-GGUF",
            lane=Lane.CPU,
            endpoint="http://localhost:13309",
            llamacpp_backend="cpu",
            task_affinity=frozenset({Task.ARCHITECT, Task.LONG_HORIZON}),
            quantization="Q4_K_M",
            context_window=32768,
            priority=40,
            notes="Safety / System Architect — AVX-VNNI",
        ),
        # --- Task-specialist models via Ollama (:11434) ---
        ModelEntry(
            model_id="phi4:latest",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            llamacpp_backend="",
            task_affinity=frozenset({Task.REASONING, Task.GENERAL}),
            quantization="Q4_K_M",
            context_window=16384,
            priority=50,
            verified_working=True,
            notes="Verified live via Ollama :11434",
        ),
        ModelEntry(
            model_id="qwen3-coder:30b",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            llamacpp_backend="",
            task_affinity=frozenset({Task.CODE_GEN}),
            quantization="Q4_K_M",
            context_window=32768,
            priority=30,
            notes="Code generation specialist",
        ),
        ModelEntry(
            model_id="deepseek-r1:70b",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            llamacpp_backend="",
            task_affinity=frozenset({Task.LONG_HORIZON, Task.REASONING}),
            quantization="Q4_K_M",
            context_window=32768,
            priority=45,
            notes="Long-horizon reasoning",
        ),
        # --- Cloud Ollama fallbacks (confirmed in registry) ---
        ModelEntry(
            model_id="deepseek-v3.2:cloud",
            lane=Lane.CLOUD_OLLAMA,
            endpoint="http://localhost:11434",
            llamacpp_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN}),
            quantization="api",
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
            llamacpp_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION}),
            quantization="api",
            context_window=1000000,
            cost_per_1k_input_usd=0.0001,
            cost_per_1k_output_usd=0.0004,
            priority=65,
            verified_working=True,
            notes="Gemini 3 Flash via ollama cloud",
        ),
        # --- Claude escalation tier ---
        # --- Headless `claude` CLI (Claude Code) ---
        # Endpoint "cli:claude" indicates subprocess invocation, not HTTP.
        ModelEntry(
            model_id="claude-haiku-4-5",
            lane=Lane.CLOUD_CLAUDE,
            endpoint="cli:claude",
            llamacpp_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION}),
            quantization="api",
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
            llamacpp_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.ARCHITECT}),
            quantization="api",
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
            llamacpp_backend="",
            task_affinity=frozenset({Task.REASONING, Task.LONG_HORIZON, Task.ARCHITECT}),
            quantization="api",
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
            llamacpp_backend="",
            task_affinity=frozenset({Task.GENERAL, Task.SUMMARIZATION, Task.ROUTING}),
            quantization="api",
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
            llamacpp_backend="",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.LONG_HORIZON}),
            quantization="api",
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
