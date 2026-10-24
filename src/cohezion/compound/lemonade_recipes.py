"""Finely crafted Lemonade recipes for the 23-model Strix Halo fleet.

Two layers:
  BASE_RECIPES — tuned recipe_options for built-in models (ctx_size bounded per N3,
    official batch sizes from lemonade-sdk/recipes, ngram speculative decoding).
  USER_VARIANTS — user.* model definitions that expose named personas via the
    Lemonade user model registry (same checkpoint, different recipe_options).

Key sources:
  github.com/lemonade-sdk/recipes — canonical batch/sampling/spec-decode params
  harness.md N3 — ctx_size=0 OOM hazard; heavy models bounded to 16384
  TurboQuant (Google 2026) — KV cache compression: 3-bit is near-lossless
  Model cards: Qwen3/Gemma-4/Bonsai/DeepSeek/Nemotron spec sheets

Strix Halo specifics:
  • llamacpp_backend = "auto" — Lemonade probes device at load time; picks vulkan
    (RDNA 3.5 iGPU) for most GGUF LLMs.  Gemma-4-E2B (tier 0) dropped its old "rocm" pin.
  • Batch size -b 4096 for heavy models — 8× faster prefill vs our prior -b 512.
  • ngram spec-decode — free 1.5-2× throughput on Gemma-4 models, no draft model.
  • All ctx_sizes bounded (≠ 0) to prevent KV-cache OOM hang (harness N3).
"""

from __future__ import annotations

from typing import TypedDict


# ── Shared constants from lemonade-sdk/recipes ───────────────────────────────

# Batch sizes (official recipe defaults, verified against lemonade-sdk/recipes)
_BATCH_HEAVY = "-b 4096 -ub 1024"  # 26B+ models: fills GPU compute units
_BATCH_MEDIUM = "-b 2048 -ub 512"  # 8B-26B range
_BATCH_SMALL = "-b 4096 -ub 2048"  # <4B: maximise throughput, always fast

# Let Lemonade pick the best compute backend (vulkan on Strix Halo iGPU for most)
_BACKEND = "auto"

# ngram speculative decoding — free 1.5-2× throughput on Gemma-4 series
# Proposes 48-64 draft tokens per step from recent n-gram matches; no extra memory.
_NGRAM_SPEC = "--spec-type ngram-mod --spec-ngram-size-n 24 --draft-min 48 --draft-max 64"

# Thinking mode chat template extensions (Qwen3 / Gemma-4 template kwargs)
_PRESERVE_THINKING = "--chat-template-kwargs '{\"preserve_thinking\": true}'"
_DISABLE_THINKING = "--chat-template-kwargs '{\"enable_thinking\": false}'"


# ── TypedDicts ────────────────────────────────────────────────────────────────


class RecipeOptions(TypedDict, total=False):
    ctx_size: int
    llamacpp_args: str
    llamacpp_backend: str


class BaseRecipe(TypedDict, total=False):
    ctx_size: int
    llamacpp_args: str
    llamacpp_backend: str
    role: str


class UserVariant(TypedDict, total=False):
    model_name: str
    checkpoint: str  # single-file checkpoint
    checkpoints: dict[str, str]  # multi-file (main + mmproj)
    labels: list[str]
    recipe: str
    recipe_options: RecipeOptions
    size: float


# ── BASE RECIPES ──────────────────────────────────────────────────────────────
# Applied via POST /api/v1/load {model_name, ctx_size, llamacpp_args,
# llamacpp_backend, save_options: True}.  Persists options across daemon restarts.
#
# ctx_size rationale:
#   Official lemonade-sdk/recipes uses ctx_size=0 (= full trained context).
#   On Strix Halo with 122 GB UMA, ctx_size=0 can trigger a hard OOM hang
#   (harness N3 — KV-cache fills the entire memory aperture).  We bound:
#   • 8192  — tiny routers/embedding; more context wastes SRAM
#   • 16384 — heavy LLMs (>16 GB weights); safe with 8 GB RAM_LOAD_BUFFER
#   • 32768 — MoE models (<5 GB active weights) and code/reasoning models
#              that genuinely need long context

BASE_RECIPES: dict[str, RecipeOptions] = {
    # ── Embedding (no generative KV cache) ───────────────────────────────────
    "nomic-embed-text-v2-moe-GGUF": {
        # nomic-embed-text-v2: 768-dim MoE; max_seq=8192 per model card
        "ctx_size": 8192,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": "-b 2048 -ub 512 -np 4 --pooling mean",
    },
    "Qwen3-Embedding-0.6B-GGUF": {
        # Qwen3-Embedding: 0.6B dense; mean-pooled sentence vectors
        "ctx_size": 4096,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": "-b 2048 -ub 512 -np 4 --pooling mean",
    },
    # ── NPU (FastFlowLM) ──────────────────────────────────────────────────────
    "gemma4-it-e2b-FLM": {
        # Cascade tier 0 (default since 2026-10-24, NPU-first). This saved recipe is the ONLY
        # tier-0 ctx authority: tier-0 callers never /load it, so the router auto-loads it at
        # these options. Without it FLM serves the 131072 context_length. FLM rounds ctx up to
        # a power of two (min 512). 32768 because this one model also serves the router's chat
        # traffic (history + answer); 4096 overflowed a 10-turn chat. Measured 2026-10-24 (FLM
        # 1.0.9, flm-real RSS): 4096 -> 5.93 GB, 16384 -> 6.20 GB, 32768 -> 6.33 GB; a ~17k-token
        # prompt answered in 41 s at 32768, and overflow fails loudly (HTTP 400 "Max length
        # reached!"). NO llamacpp keys: the flm recipe has no llama.cpp backend. MUST stay
        # identical to the entry in scripts/ops/lemonade-recipes.md (test_tier0_model.py pins it).
        "ctx_size": 32768,
    },
    # ── Tiny LLMs (always-warm routing, classification, short QA) ────────────
    "Llama-3.2-1B-Instruct-GGUF": {
        # Opt-in tier 0 via COHEZION_TIER0_MODEL (the default is gemma4-it-e2b-FLM since
        # 2026-10-24). Kept bounded so the override needs no client ctx pin.
        # Llama-3.2-1B KV is 32 KiB/token: 4096 -> 0.125 GB vs 4.0 GB at the 131072 window.
        # -np 1: lemonade divides ctx_size across slots; 4096 split four ways truncates.
        "ctx_size": 4096,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_SMALL} -np 1",
    },
    "Qwen3-0.6B-GGUF": {
        # 0.6B dense Qwen3; ~40K training ctx but 8K is ample for routing tasks
        "ctx_size": 8192,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_SMALL} -np 4",
    },
    "Bonsai-1.7B-gguf": {
        # Fast classification / short extraction; 4 parallel slots
        "ctx_size": 8192,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_SMALL} -np 4",
    },
    "Bonsai-4B-gguf": {
        # Short QA / mid-tier fallback; 2 parallel slots
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_MEDIUM} -np 2",
    },
    # ── Small LLMs ────────────────────────────────────────────────────────────
    "Gemma-4-E2B-it-GGUF": {
        # Opt-in tier 0 via COHEZION_TIER0_MODEL (the default 2026-10-23..24; now the NPU FLM
        # build). As tier 0, this saved recipe is its ONLY ctx authority: tier-0 callers never /load it (GAIA paths pass auto_download=False), so
        # the router auto-loads it at these options. MUST stay identical to the entry in
        # scripts/ops/lemonade-recipes.md, or the two appliers re-stamp each other
        # (tests/inference/test_tier0_model.py pins this).
        # "auto" (the device probe picks Vulkan on this iGPU), not the old "rocm" pin: the
        # capability sweep measured it on Vulkan, and Vulkan also measured faster than ROCm
        # for llama.cpp on this gfx1151 iGPU.
        # -np 1: lemonade divides ctx_size across slots; a thinking model needs the whole
        # 4096 (prompt + CoT + answer) in one slot. KV is 18 KiB/token (oom_guard), so 4096
        # costs ~72 MB. Sampling is the model card's (GGUF general.sampling: 1.0/0.95/64).
        "ctx_size": 4096,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": "--temp 1.0 --top-p 0.95 --top-k 64 -b 2048 -ub 512 -np 1",
    },
    "Bonsai-8B-gguf": {
        # Q1_0 quantization — DO NOT add KV cache quant (--cache-type-k q4_0):
        # that would double-degrade already extremely lossy 1-bit weights.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_MEDIUM} -np 2",
    },
    "DeepSeek-Qwen3-8B-GGUF": {
        # Reasoning model (DeepSeek-R1 distilled to Qwen3-8B).
        # Upgraded to 32768: CoT traces easily span 10K+ tokens;
        # A3B MoE means only ~3B active weights so KV cache budget is safe.
        "ctx_size": 32768,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_MEDIUM} -np 1 {_PRESERVE_THINKING}",
    },
    "Gemma-4-E4B-it-GGUF": {
        # ~4B effective Gemma-4 MoE; 32768 already set and correct
        "ctx_size": 32768,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"{_BATCH_MEDIUM} -np 2",
    },
    # ── Heavy LLMs (N3 bound: ctx_size ≤ 16384 unless MoE with low active params) ──
    "Gemma-4-26B-A4B-it-GGUF": {
        # 26B total / 4B active MoE — vision + tool-calling.
        # ngram speculative decoding: 1.5-2× throughput at zero extra memory cost.
        # temp=1.0 / top-k=64: Gemma-4 recommended sampling (from official recipe).
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": (f"--temp 1.0 --top-p 0.95 --top-k 64 {_BATCH_HEAVY} {_NGRAM_SPEC}"),
    },
    "Qwen3.6-27B-GGUF": {
        # Dense 27B — no MoE, full weight activation.  Single slot.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"--temp 0.7 --top-p 0.8 --top-k 20 {_BATCH_HEAVY}",
    },
    "Gemma-4-31B-it-GGUF": {
        # 31B Gemma-4; ngram spec applies here too
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": (f"--temp 1.0 --top-p 0.95 --top-k 64 {_BATCH_HEAVY} {_NGRAM_SPEC}"),
    },
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": {
        # A3B MoE — 3B active.  Code needs long context (files + completions).
        # ctx_size=32768 is safe: active KV footprint ≈ 3B-model-equivalent.
        "ctx_size": 32768,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"--temp 0.7 --top-p 0.8 {_BATCH_HEAVY}",
    },
    "Nemotron-3-Nano-30B-A3B-GGUF": {
        # NVIDIA Nemotron-3 A3B MoE; Llama-based architecture.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"--temp 0.7 --top-p 0.9 {_BATCH_HEAVY}",
    },
    "Qwen3.5-35B-A3B-GGUF": {
        # A3B MoE previous generation.  Preserve user-set sampling params.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": f"--temp 0.7 --top-p 0.8 --top-k 20 {_BATCH_HEAVY}",
    },
    "Qwen3.6-35B-A3B-GGUF": {
        # A3B MoE current gen — default to NoThinking mode.
        # presence-penalty=2.0 prevents repetition without CoT scaffold.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": (
            f"--temp 1.0 --top-p 1.0 --top-k 40 "
            f"--presence-penalty 2.0 --repeat-penalty 1.0 "
            f"{_BATCH_HEAVY} {_DISABLE_THINKING}"
        ),
    },
    "Qwen3.6-35B-A3B-MTP-GGUF": {
        # MTP (Multi-Token Prediction) variant — speculative multi-token drafting.
        # preserve_thinking=true: this variant is used for deep reasoning chains.
        # temp=0.6 / top-p=0.95: from official lemonade-sdk/recipes ThinkingCoder.
        "ctx_size": 16384,
        "llamacpp_backend": _BACKEND,
        "llamacpp_args": (
            f"--temp 0.6 --top-p 0.95 --top-k 20 "
            f"--presence-penalty 0 --repeat-penalty 1.0 "
            f"{_BATCH_HEAVY} {_PRESERVE_THINKING}"
        ),
    },
}


# ── USER VARIANTS ─────────────────────────────────────────────────────────────
# Named model personas with model_name "user.*" prefix.
# Same checkpoints as built-in models but with purpose-tuned recipe_options.
# Applied by writing JSON to the Lemonade user model registry.
# After registration, load by name: POST /api/v1/load {"model_name": "user.X"}

USER_VARIANTS: list[UserVariant] = [
    # Qwen3.6-35B ThinkingCoder — deep reasoning, CoT preserved
    {
        "model_name": "user.Qwen3.6-35B-A3B-ThinkingCoder",
        "checkpoint": "unsloth/Qwen3.6-35B-A3B-GGUF:Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf",
        "labels": ["coding", "reasoning", "tool-calling"],
        "recipe": "llamacpp",
        "recipe_options": {
            "ctx_size": 16384,
            "llamacpp_backend": _BACKEND,
            "llamacpp_args": (
                f"--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.00 "
                f"--presence-penalty 0 --repeat-penalty 1.0 "
                f"{_BATCH_HEAVY} {_PRESERVE_THINKING}"
            ),
        },
        "size": 22.4,
    },
    # Qwen3.6-35B NoThinking — fast general / tool-calling (thinking OFF)
    {
        "model_name": "user.Qwen3.6-35B-A3B-NoThinking",
        "checkpoint": "unsloth/Qwen3.6-35B-A3B-GGUF:Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf",
        "labels": ["hot", "tool-calling", "vision"],
        "recipe": "llamacpp",
        "recipe_options": {
            "ctx_size": 16384,
            "llamacpp_backend": _BACKEND,
            "llamacpp_args": (
                f"--temp 1.0 --top-p 1.0 --top-k 40 --min-p 0.00 "
                f"--presence-penalty 2.0 --repeat-penalty 1.0 "
                f"{_BATCH_HEAVY} {_DISABLE_THINKING}"
            ),
        },
        "size": 22.4,
    },
    # Qwen3.6-35B-MTP ThinkingCoder — vision + MTP speculative drafting + CoT
    {
        "model_name": "user.Qwen3.6-35B-A3B-MTP-ThinkingCoder",
        "checkpoints": {
            "main": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF:Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf",
            "mmproj": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF:mmproj-F16.gguf",
        },
        "labels": ["vision", "coding", "tool-calling"],
        "recipe": "llamacpp",
        "recipe_options": {
            "ctx_size": 16384,
            "llamacpp_backend": _BACKEND,
            "llamacpp_args": (
                f"--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.00 "
                f"--presence-penalty 0 --repeat-penalty 1.0 "
                f"{_BATCH_HEAVY} {_PRESERVE_THINKING}"
            ),
        },
        "size": 19.7,
    },
    # Gemma-4-26B NoThinking — fastest vision path with ngram spec decode
    {
        "model_name": "user.Gemma-4-26B-A4B-NoThinking",
        "checkpoint": "unsloth/gemma-4-26B-A4B-it-GGUF:UD-Q4_K_M",
        "labels": ["vision", "hot", "tool-calling", "llamacpp"],
        "recipe": "llamacpp",
        "recipe_options": {
            "ctx_size": 16384,
            "llamacpp_backend": _BACKEND,
            "llamacpp_args": (
                f"--temp 1.0 --top-p 0.95 --top-k 64 "
                f"{_BATCH_HEAVY} {_DISABLE_THINKING} {_NGRAM_SPEC}"
            ),
        },
        "size": 16.9,
    },
    # DeepSeek-Qwen3-8B Reasoning — long ctx, thinking preserved
    {
        "model_name": "user.DeepSeek-Qwen3-8B-Reasoning",
        "checkpoint": "unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_1",
        "labels": ["reasoning", "coding"],
        "recipe": "llamacpp",
        "recipe_options": {
            "ctx_size": 32768,
            "llamacpp_backend": _BACKEND,
            "llamacpp_args": (
                f"--temp 0.6 --top-p 0.95 {_BATCH_MEDIUM} -np 1 {_PRESERVE_THINKING}"
            ),
        },
        "size": 5.25,
    },
]
