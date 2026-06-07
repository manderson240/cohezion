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

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from collections.abc import Callable


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
    # Task-specialist members (task-aware routing, 2026-06-05; research:
    # docs/research/TASK_HARNESS_ROUTING_LEVERS_2026-06-05.md). Added so for_task() can
    # express small-specialist lanes. No model is registered for these yet, so for_task
    # returns [] for them until a specialist ModelEntry is added (e.g. LFM2.5-VL → EXTRACTION).
    EXTRACTION = "extraction"
    VISION = "vision"
    FIM = "fim"
    FUNCTION_CALL = "function_call"
    RERANK = "rerank"
    OCR_DOC = "ocr_doc"
    # Multimodal in+out members (thread M item 83 + user video directive, 2026-06-06). cohezion
    # already ingests images (VISION/EXTRACTION/OCR_DOC); these declare the OUTPUT modalities plus
    # video INPUT. No model is registered for them yet → for_task returns [] until a specialist
    # ModelEntry is added behind its serving proof: IMAGE_GEN (sd.cpp Vulkan, item 86), AUDIO_TTS
    # (PocketTTS item 85 / Higgs research-only item 93), VIDEO_GEN (research-gated item 87),
    # VIDEO_UNDERSTAND (video input — research-gated until a fleet-runnable video VLM is verified).
    IMAGE_GEN = "image_gen"
    AUDIO_TTS = "audio_tts"
    VIDEO_GEN = "video_gen"
    VIDEO_UNDERSTAND = "video_understand"


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
    # HISTORICAL marker — True means this model was successfully invoked at least
    # once (see `FleetRegistry.mark_verified` / `last_verified_at`). It does NOT
    # mean the endpoint is reachable right now. For LIVE status, use
    # `cohezion.inference.health.check_fleet()` — `fleet.route()` already does.
    # Use `FleetRegistry.audit_liveness()` to reconcile the two and surface drift.
    verified_working: bool = False
    last_verified_at: datetime | None = None
    # Empirical latency targets (milliseconds) — populated from benchmark runs.
    # None = not yet measured. Used by the benchmark harness and for
    # latency-first routing policies.
    observed_ttft_ms_p50: float | None = None  # 50th percentile time-to-first-token
    observed_ttft_ms_p95: float | None = None  # 95th percentile TTFT
    observed_total_ms_p50: float | None = None  # 50th percentile full-response latency
    observed_tokens_per_sec: float | None = None  # sustained generation throughput
    # Approximate resident size in GB (weights + KV) for the per-candidate OOM headroom gate
    # (fleet.route, item 132). None = unknown → the headroom gate is skipped for this candidate
    # (never fabricate a size); the fleet-wide OOM buffer (item 131) still applies.
    size_gb: float | None = None
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
    # KV preset for the iGPU lanes.
    #
    # 2026-04-21: pivoted from TurboQuant (`tbq_35` / `tbq_40`) to `kv8_q80`
    # after Phase 0 of `~/.claude/plans/do-we-have-turbo-distributed-torvalds.md`
    # confirmed that neither the Lemonade-bundled llama.cpp (5dd1025) nor any
    # other local llama-server binary on this machine ships TurboQuant kernels,
    # and that upstream llama.cpp #20969 is still a Discussion (not a merged PR).
    # `q8_0` is ~2x KV compression vs. bf16 and is a first-class cache-type-k/v
    # value in llama.cpp today, so it delivers real compression instead of a
    # silent no-op. Revisit TurboQuant when upstream or a maintained fork lands.
    kv8_q80 = KVQuant(
        scheme="kv8",
        bits=8.0,
        runtime_flag={"llama.cpp": "q8_0", "vllm": "fp8", "sglang": "fp8"},
    )

    entries: list[ModelEntry] = [
        # --- Strix Halo Symphony: 4-lane Gemma 4 ---
        ModelEntry(
            model_id="Gemma-4-E2B-it-GGUF",
            size_gb=2.9,  # measured GGUF on disk: gemma-4-E2B-it-Q4_K_M.gguf (non-fabricated)
            lane=Lane.NPU,
            endpoint="http://localhost:13306",
            runtime_backend="flm",
            task_affinity=frozenset({Task.SENSING, Task.ROUTING, Task.SUMMARIZATION}),
            weight_quant=WeightQuant.INT4,
            kv_quant=KVQuant(),  # AMD Ryzen AI compiler has no TBQ op as of 1.7.1
            # 2026-04-21: raised 8192 → 131072 per HF model card (128K native).
            # Gemma 4 family supports 128K-256K; prior 8192 was an arbitrary default.
            context_window=131072,
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
            size_gb=4.6,  # measured GGUF on disk: gemma-4-E4B-it-Q4_K_M.gguf (non-fabricated)
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # served by Lemonade (lemond :13307)
            task_affinity=frozenset({Task.STRUCTURED, Task.GOVERNANCE}),
            weight_quant=WeightQuant.Q4_K_M,
            kv_quant=kv8_q80,
            # 2026-04-21: raised 16384 → 131072 per HF model card (128K native).
            context_window=131072,
            priority=20,
            reasoning_mode=True,
            notes=(
                "Electric Fire (Knower) — Governance / Steering. "
                "Gemma 4 has native system role support (unlike many reasoning models)."
            ),
        ),
        ModelEntry(
            model_id="LFM2.5-VL-1.6B-Extract-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # vision needs --mmproj (llama-mtmd) — unproven on lemonade
            task_affinity=frozenset({Task.EXTRACTION, Task.VISION}),
            weight_quant=WeightQuant.Q4_K_M,  # actual GGUF is Q4_0 (~696 MB); F16 ~2.34 GB
            context_window=32768,
            priority=25,  # the EXTRACTION/VISION specialist (was none); small VLM, low VRAM
            verified_working=False,  # SERVING proven; ACCURACY proof still pending — see LFM_VL_EXTRACTION_2026-06-06.md
            notes=(
                "LiquidAI image→YAML field-extraction VLM (the seed for Task.EXTRACTION). "
                "SERVING PROVEN 2026-06-06 via the llama-mtmd-cli sidecar (bundled in lemonade "
                "bin/llamacpp/rocm-stable/) with --mmproj mmproj-…-F16.gguf — lemonade `load` has NO "
                "--mmproj flag, so the sidecar (or --llamacpp-args passthrough) is the path. Smoke: a "
                "known-text image → structured YAML echoing the image fields (read 'Cohezion'→'Cohesion', "
                "i.e. genuinely reading pixels). ACCURACY bake-off RAN 2026-06-06 on CORD-v2 (10 img, "
                "pre-registered value-recall): LFM 0.771 vs Qwen2.5-VL-7B baseline 0.864 → honest NULL, "
                "verified_working stays False (LFM serves + is 6.7x smaller but ~9pts less accurate than "
                "the bigger VLM). Re-run on real user docs may differ. License lfm1.0 — verify commercial terms."
            ),
        ),
        ModelEntry(
            model_id="Qwen3-Reranker-0.6B-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # needs --pooling rank (llama-server reranker mode)
            task_affinity=frozenset({Task.RERANK}),
            weight_quant=WeightQuant.Q5_K_M,  # ~0.6B; Q5_K_M GGUF ~520 MB, low VRAM
            context_window=32768,
            priority=25,  # the RERANK specialist (was none); tiny cross-encoder, cheap to host
            verified_working=False,  # /v1/rerank proof NOT yet run — see item 19 / BLEEDING_EDGE_FEED
            notes=(
                "Qwen3-Reranker-0.6B cross-encoder (the seed for Task.RERANK; HF id "
                "Mungert/Qwen3-Reranker-0.6B-GGUF, 21 GGUF variants). SERVING-GATED: llama.cpp "
                "rerankers need `--pooling rank` + a proper convert_hf_to_gguf.py; the known trap is "
                "degenerate near-zero scores (~4.5e-23) for every pair. verified_working flips True "
                "only after a real NON-DEGENERATE /v1/rerank proof passes. Apache-2.0."
            ),
        ),
        ModelEntry(
            model_id="Granite-4.1-3b-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # tool-calling needs template/tool-token alignment
            task_affinity=frozenset({Task.FUNCTION_CALL}),
            weight_quant=WeightQuant.Q4_K_M,  # ~3B; Q4_K_M GGUF ~2 GB, low VRAM
            context_window=131072,
            priority=22,  # the FUNCTION_CALL specialist (was none); small no-thinking tool model
            verified_working=False,  # tool-call proof NOT yet run — see item 21 / BLEEDING_EDGE_FEED
            notes=(
                "IBM Granite-4.1-3b (the seed for Task.FUNCTION_CALL; HF id "
                "ibm-granite/granite-4.1-3b-GGUF, 15 GGUF variants). SAME validated no-thinking, "
                "tool-capable family as Hermes's main Granite-4.1-8B, but $0-local-small. "
                "SERVING-GATED: llama.cpp tool-calling breaks on chat-template / tool-call "
                "special-token mismatch (orchestrator prompt format must match the model template). "
                "verified_working flips True only after a real finish_reason=tool_calls proof with "
                "valid args. Apache-2.0."
            ),
        ),
        ModelEntry(
            model_id="Gemma-4-26B-A4B-it-GGUF",
            size_gb=15.7,  # measured GGUF on disk via measure_gguf_sizes (item 136, non-fabricated)
            lane=Lane.IGPU_UNIFIED,
            endpoint="http://localhost:13308",
            # DECLARED vllm_rocm; today served via Lemonade (llamacpp) when loaded.
            runtime_backend="vllm_rocm",
            task_affinity=frozenset({Task.REASONING, Task.CODE_GEN, Task.GENERAL}),
            weight_quant=WeightQuant.MXFP4,
            kv_quant=kv8_q80,
            # 2026-04-21: raised 32768 → 262144 per HF card (256K native).
            context_window=262144,
            priority=15,
            reasoning_mode=True,
            notes=(
                "Solar Fire (Thinker) — 25.2B total / 3.8B active MoE "
                "(8 active / 128 total experts + 1 shared expert)."
            ),
        ),
        ModelEntry(
            model_id="GLM-OCR-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # vision/OCR needs --mmproj (llama-mtmd) — shares item 18
            task_affinity=frozenset({Task.OCR_DOC}),
            weight_quant=WeightQuant.Q4_K_M,  # GGUF: GLM-OCR-Q8_0 + GLM-OCR-f16 + mmproj-GLM-OCR-Q8_0
            context_window=32768,
            priority=25,  # the OCR_DOC specialist (was none) — the LAST empty Task slot
            verified_working=False,  # mmproj serving proof NOT yet run (shares item 18's path)
            notes=(
                "Official ggml-org OCR/document VLM (the seed for Task.OCR_DOC; HF id verified "
                "ggml-org/GLM-OCR-GGUF, 23,009 dl, GGUF + mmproj-GLM-OCR-Q8_0). Runs via "
                "`llama-server -hf ggml-org/GLM-OCR-GGUF` (mmproj auto-paired). mmproj-GATED: "
                "lemonade --mmproj support UNPROVEN → llama-mtmd sidecar fallback; K1/rule-5 OOM "
                "gate must pass before pinning (size unconfirmed). verified_working flips True only "
                "after a real OCR/doc proof — SHARES item 18's vision-projector experiment."
            ),
        ),
        ModelEntry(
            model_id="Mellum-4b-base-GGUF",
            lane=Lane.IGPU_ROCWMMA,
            endpoint="http://localhost:13307",
            runtime_backend="llamacpp_hip",  # FIM completion via /api/v1/completions (NOT chat)
            task_affinity=frozenset({Task.FIM}),
            weight_quant=WeightQuant.INT8,  # GGUF mellum-4b-base.Q8_0 (≈8-bit); enum has no Q8_0
            context_window=8192,
            priority=25,  # the FIM specialist (was none) — the LAST empty Task slot now filled
            verified_working=False,  # FIM-completion serving proof NOT yet run — see item 28
            notes=(
                "JetBrains Mellum-4b FIM-native BASE model (the seed for Task.FIM; HF id VERIFIED "
                "huggingface_hub.model_info — JetBrains/Mellum-4b-base-gguf, 406 dl, 1 GGUF "
                "mellum-4b-base.Q8_0.gguf, research round 4). Fill-in-the-middle via "
                "/api/v1/completions with <fim_prefix>…<fim_suffix>…<fim_middle> tokens — NOT a "
                "chat model. Q8_0 ≈ 4 GB → load on-demand, do NOT pin (K1/rule-5). "
                "verified_working flips True only after a real FIM-completion serving proof."
            ),
        ),
        ModelEntry(
            model_id="Granite-4.1-8B-GGUF",
            lane=Lane.IGPU_ROCWMMA,  # Granite backend lives on the iGPU; fronted by the router
            endpoint="http://localhost:13305",  # the ALWAYS-UP lemonade router (Hermes-shared)
            runtime_backend="llamacpp_hip",
            task_affinity=frozenset(
                {Task.REASONING, Task.GENERAL}
            ),  # 3b stays FUNCTION_CALL specialist
            weight_quant=WeightQuant.Q4_K_M,
            context_window=131072,
            priority=12,  # preferred LOCAL reasoning/agent-offload pick (below the 26B's 15)
            verified_working=True,  # live-proven 2026-06-06 (V1_OK, reasoning_content=0)
            last_verified_at=datetime(2026, 6, 6),
            notes=(
                "Extends agent availability with $0 local inference: the verified-live, "
                "NO-THINKING, tool-capable Granite-4.1-8B served by the always-up lemonade router "
                ":13305 (the same model Hermes runs). Registered because the registry's other local "
                "REASONING model (Gemma-4-26B-A4B) points at the DOWN :13308 lane — so route(REASONING,"
                " $0) was returning 'all candidates exhausted' and silently escalating to cloud. This "
                "is the local-first target for extend_claude. No thinking-trap (reasoning_content "
                "empty on plain turns); finish_reason=tool_calls on tool turns."
            ),
        ),
        ModelEntry(
            model_id="Gemma-4-31B-it-GGUF",
            lane=Lane.CPU,
            endpoint="http://localhost:13309",
            runtime_backend="cpu",
            task_affinity=frozenset({Task.ARCHITECT, Task.LONG_HORIZON}),
            weight_quant=WeightQuant.Q4_K_M,
            kv_quant=KVQuant(),  # No public AVX-512 TBQ kernels exist (April 2026)
            # 2026-04-21: raised 32768 → 262144 per HF card (256K native, dense).
            context_window=262144,
            priority=40,
            reasoning_mode=True,
            notes=(
                "Safety / System Architect — dense 30.7B on AVX-VNNI. "
                "Uses 1024-token sliding window attention."
            ),
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
            task_affinity=frozenset({Task.CODE_GEN, Task.LONG_HORIZON}),
            weight_quant=WeightQuant.Q4_K_M,
            # 2026-04-21: raised 32768 → 262144 per HF card (256K native, up to 1M
            # via YARN). Prior 32768 was the card's explicit OOM fallback value,
            # not the native context. Added LONG_HORIZON to task_affinity because
            # 256K is "repository-scale understanding" territory per the card.
            context_window=262144,
            priority=30,
            notes=(
                "Code generation specialist. Native 256K context (repository-scale); "
                "YARN extension to 1M. Reduce to ctx=32768 if OOM per model card guidance."
            ),
        ),
        ModelEntry(
            model_id="deepseek-r1:70b",
            lane=Lane.CPU,
            endpoint="http://localhost:11434",
            runtime_backend="",
            task_affinity=frozenset({Task.LONG_HORIZON, Task.REASONING, Task.MATH}),
            weight_quant=WeightQuant.Q4_K_M,
            # 2026-04-21: raised 32768 → 131072 per HF card (128K from base
            # Llama-3.3-70B-Instruct). Added MATH to task_affinity per R1's
            # published strengths. Generation guidance from model card:
            #   temperature=0.6 (0.5-0.7 range to avoid repetition/incoherence)
            #   top_p=0.95, max_tokens=32768
            #   NO system prompts — fold all instructions into the user prompt
            #   enforce `<think>\\n` prefix on response for thorough reasoning
            context_window=131072,
            priority=45,
            reasoning_mode=True,
            notes=(
                "Long-horizon reasoning (R1 distill on Llama-70B, 128K ctx). "
                "Emits <think> blocks. Card recommends: temp=0.6, top_p=0.95, "
                "NO system prompt (fold instructions into user prompt), enforce "
                "<think>\\n prefix on response."
            ),
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

    def audit_liveness(self, check_fleet_fn: Callable[[], object] | None = None) -> LivenessAudit:
        """Reconcile static registry declarations against live health probes.

        Returns a structured report classifying every local-lane model into one
        of four drift categories — useful as an operator CLI (`python -m
        cohezion.inference.registry audit`) and as a CI integration guard.

        `check_fleet_fn` is injectable for tests; defaults to the live prober
        in `cohezion.inference.health`.
        """
        if check_fleet_fn is None:
            from cohezion.inference.health import check_fleet as _check

            check_fleet_fn = _check

        health = check_fleet_fn()
        local_lanes = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}
        items: list[LivenessDrift] = []
        for m in self.models.values():
            if m.lane not in local_lanes:
                continue  # cloud/CLI lanes are handled via try/except on dispatch
            lane_key = m.lane.value
            lane_health = getattr(health, "lanes", {}).get(lane_key)
            live_status = lane_health.status.value if lane_health else "unknown"
            if live_status == "up" and m.verified_working:
                category = "healthy"
            elif live_status != "up" and m.verified_working:
                category = "critical_stale"
            elif live_status == "up" and not m.verified_working:
                category = "unverified_up"
            else:
                category = "lane_down"
            items.append(
                LivenessDrift(
                    model_id=m.model_id,
                    lane=lane_key,
                    endpoint=m.endpoint,
                    live_status=live_status,
                    verified_working=m.verified_working,
                    category=category,
                )
            )
        return LivenessAudit(checked_at=time.time(), items=items)


@dataclass
class LivenessDrift:
    """One row of the liveness audit — a model's static-vs-live reconciliation."""

    model_id: str
    lane: str
    endpoint: str
    live_status: str  # "up" | "down" | "degraded" | "unknown"
    verified_working: bool
    category: str  # "healthy" | "critical_stale" | "unverified_up" | "lane_down"


@dataclass
class LivenessAudit:
    """Structured output of `FleetRegistry.audit_liveness()`."""

    checked_at: float
    items: list[LivenessDrift]

    @property
    def critical_stale(self) -> list[LivenessDrift]:
        """`verified_working=True` but live lane is DOWN — the registry is lying."""
        return [i for i in self.items if i.category == "critical_stale"]

    @property
    def healthy(self) -> list[LivenessDrift]:
        """Live AND historically verified."""
        return [i for i in self.items if i.category == "healthy"]

    @property
    def unverified_up(self) -> list[LivenessDrift]:
        """Live but never flagged — may deserve a `mark_verified` call."""
        return [i for i in self.items if i.category == "unverified_up"]

    @property
    def lane_down(self) -> list[LivenessDrift]:
        """Not live, not claimed — declared topology we can't serve right now."""
        return [i for i in self.items if i.category == "lane_down"]


_registry: FleetRegistry | None = None


def get_registry() -> FleetRegistry:
    """Module singleton accessor."""
    global _registry
    if _registry is None:
        _registry = FleetRegistry()
    return _registry
