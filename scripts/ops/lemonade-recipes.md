---
type: config
name: lemonade-fleet-recipes
description: Card-aligned, silicon-aware recipe_options targets for the :13305 fleet
updated: 2026-07-15
router: http://localhost:13305
apply_with: scripts/ops/apply_lemonade_recipes.py
# Global silicon policy (Strix Halo: 128GiB unified, XDNA2 NPU, RDNA3.5 iGPU):
#  - Every llamacpp LLM carries an EXPLICIT ctx_size (N3: absent = inherits global
#    default; explicit = auditable). ctx_size=0 is forbidden everywhere.
#  - KV cache quantized q4_0 on heavy (>=18GB) models — halves KV footprint.
#  - Sampling lives SERVER-SIDE in llamacpp_args, copied from the model card.
#    Cohezion clients must OMIT sampling params to inherit it (see prose below).
#  - verify_card: true means the sampling values are family-lineage defaults that
#    still need confirmation against the actual HF model card (hf-cli).
recipes:
  - model: Qwen3.6-35B-A3B-MTP-GGUF
    role: QA/reasoning lane (resident, MTP speculative decode w/ Qwen3-0.6B draft)
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.8 --top-k 20 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true   # Qwen3-instruct lineage values; confirm unsloth card
  - model: Qwen3-Coder-30B-A3B-Instruct-GGUF
    role: agentic coding (NOT auto-loadable at low headroom — 18.6GB weights)
    ctx_size: 32768     # down from 65536: 64K KV on 12GiB headroom is an OOM hazard
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.8 --top-k 20 --repeat-penalty 1.05 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: false  # documented Qwen3-Coder card values
  - model: Gemma-4-26B-A4B-it-GGUF
    role: BBQ deep-reasoning tier
    ctx_size: 32768
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 1.0 --top-p 0.95 --top-k 64 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true   # replicated from Gemma-4-E4B's existing card args
  - model: Gemma-4-31B-it-GGUF
    role: CPU-tier deep reasoning
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 1.0 --top-p 0.95 --top-k 64 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true
  - model: Gemma-4-E2B-it-GGUF
    role: light structured generation
    ctx_size: 8192
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 1.0 --top-p 0.95 --top-k 64"
    verify_card: true
  - model: Bonsai-1.7B-gguf
    role: fast drafting
    ctx_size: 32768
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.9 --top-k 40"
    verify_card: true   # replicated from Bonsai-8B's existing card args
  - model: Bonsai-4B-gguf
    role: fast drafting
    ctx_size: 32768
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.9 --top-k 40"
    verify_card: true
  - model: Bonsai-27B-gguf
    role: heavy drafting (3.8GB Q1_0 weights but full-size KV — ctx must be explicit)
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.9 --top-k 40 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true
  - model: Bonsai-27B-gguf-Q1_0
    role: heavy drafting (duplicate quant entry)
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.7 --top-p 0.9 --top-k 40 --cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true
  - model: Ornith-1.0-35B-GGUF-Q4_K_M
    role: alt heavy reasoner
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--cache-type-k q4_0 --cache-type-v q4_0"
    verify_card: true   # sampling unknown — args intentionally omit temp until card is read
  - model: Qwen3-8B-GGUF
    role: mid reasoner (thinking mode)
    ctx_size: 16384
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.6 --top-p 0.95 --top-k 20"
    verify_card: false  # documented Qwen3 thinking-mode card values
  - model: DeepSeek-Qwen3-8B-GGUF
    role: distilled reasoner
    ctx_size: 32768
    llamacpp_backend: vulkan
    llamacpp_args: "--temp 0.6 --top-p 0.95"
    verify_card: false  # documented DeepSeek-R1-distill card values
  - model: Qwen3-Embedding-0.6B-GGUF
    role: embedding (alt to nomic)
    ctx_size: 8192
    llamacpp_backend: vulkan
    llamacpp_args: ""
    verify_card: false  # embeddings: no sampling
# FLM (NPU) recipes have no llamacpp surface and are already ctx-bounded:
#   llama3.2-1b-FLM (4096), deepseek-r1-0528-8b-FLM (40960), qwen3.5-4b-FLM (8192) — leave as-is.
# Non-LLM recipes (sd-cpp / whispercpp / kokoro) carry no KV cache — out of scope.
---

# Lemonade Fleet Recipes — card-aligned, silicon-aware

Machine data lives in the frontmatter above; `apply_lemonade_recipes.py` parses it.

## Why server-side sampling

Lemonade applies `--temp/--top-k/--top-p` at model load. A prior session found
Cohezion's client-side `temperature=0.0` default was **overriding** the card
sampling the server was correctly serving (vault memory:
`lemonade-serves-card-sampling-cohezion-fights-it`). The durable rule:

- **Server**: recipe carries the model card's sampling (this manifest).
- **Clients**: omit sampling params entirely to inherit the card.
- **Known tension**: harness invariant TR1 (`_TIER_TEMPERATURE` npu=0.0 /
  igpu=0.1 / cpu=0.3 in `build_reasoning_orchestrator`) deliberately forces
  low temperature for categorical determinism. That is an intentional
  per-call override for short-categorical tasks; do NOT extend it to
  generation-type calls, and do not change TR1 without a harness update.

## Silicon policy (N3 / K1 discipline)

- No `ctx_size=0` anywhere, ever. Absent ctx on a heavy model gets an explicit
  16384 stamp so the hazard map (`GET /api/v1/models`) stays auditable.
- KV quantization (`--cache-type-k/v q4_0`) on ≥18GB-class models: KV, not
  weights, is the footprint driver on unified memory.
- The applier enforces a RAM gate (MemAvailable ≥ weights×1.2 + 8GiB KV
  allowance + 16GiB floor) and refuses to touch currently-loaded models
  unless `--force-reload` — resident models get their new recipe at the next
  natural reload.

## Verification

After any apply run: `curl -s :13305/api/v1/models/<id>` must show the
persisted `recipe_options`. `verify_card: true` entries need their sampling
confirmed against the HF model card (`hf repo …` / card README) before the
flag is flipped — lineage defaults are a starting point, not ground truth.
