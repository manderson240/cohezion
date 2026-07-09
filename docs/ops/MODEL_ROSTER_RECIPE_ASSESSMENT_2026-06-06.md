---
title: "Model Roster & Recipe Assessment — Strix Halo local-AI fleet"
date: 2026-06-06
scope: "Hermes Telegram bot local-first inference + cohezion triune; lemonade 10.6.0 / FLM 0.9.42"
status: "assessment (no disruptive changes applied — gateway-stop + sudo steps flagged for the user)"
---

# Model Roster & Recipe Assessment (2026-06-06)

## 1. Serving architecture — answers to the routing questions

**The NPU lane is ALREADY unlocked — via the omnirouter, not a dedicated port.**
The `:13305` lemonade router serves `llama3.2-1b-FLM` on the XDNA2 NPU on demand (verified: a
completion request returned content). FLM-tagged models (`llama3.2-1b-FLM`, `qwen3-4b-FLM`,
`gemma4-it-e2b-FLM`, …) route to the NPU; GGUF models route to iGPU/CPU. A separate `lemond --port
13306` (harness N1's old "3-node startup") is the LEGACY multi-port model — **not needed**; the
omnirouter subsumes it. (A stray 13306 started during this assessment was cleaned up.)

**Is lemonade an omnirouter? YES.** `:13305` is the omnirouter: one OpenAI-compatible endpoint
multiplexing 28 served models (148 known), auto-loading each on its correct backend (FLM→NPU,
GGUF→iGPU/CPU, diffusion→GPU). What it does NOT do: *task-aware tier SELECTION* (decide WHICH
model/tier for a given task). That is the caller's job.

**Does GAIA give smart routing? PARTIALLY.** GAIA's agent hits `:13305` and lands on the NPU when it
requests an FLM model — but it has no task-aware tier escalation. `inference/gaia_adapter.py` wraps a
GAIA agent as ONE tier inside cohezion's `TieredOrchestrator`. So: GAIA = a convenient NPU-backed tier
target; **cohezion** (`triune_orchestrator` / `CostAwareRouter` / `FleetRoutingSpecialist`) = the
task-aware brain; **Hermes** has its own length-based `smart_model_routing` (cheap_model vs default).

**Do we need two ports (13305 + 13307)? Currently YES, but consolidatable.**
- `:13305` = omnirouter — **Hermes (the bot) uses only this.**
- `:13307` = a second lemonade serving 17 models — **cohezion's `triune_orchestrator` defaults
  `igpu_port=13307`** (the dedicated iGPU FLM node, `deepseek-r1-0528-8b-FLM`). It is load-bearing
  for the triune, NOT for the bot.
- **Recommendation**: the omnirouter can serve every tier, so you *can* consolidate to `:13305` alone
  (repoint `triune_orchestrator` `igpu_port`→13305) and free 13307's memory. **Trade-off**: a
  dedicated 13307 gives the iGPU tier load-stability against the omnirouter's auto-load/evict anomaly
  (harness N1). Keep two for tier stability; consolidate to one for memory + simplicity. For the BOT
  alone, 13307 is unused → it can be stopped without affecting Hermes.

## 2. The roster (28 models served on :13305; checkpoint = HF repo:quant)

### NPU / FLM tier (XDNA2, FastFlowLM) — classification, fast aux, draft
| id | checkpoint | ctx | role |
|---|---|---|---|
| `llama3.2-1b-FLM` | llama3.2:1b | 131072 | routing/classify, fast aux (current Hermes aux) |
| `qwen3-4b-FLM` | qwen3:4b | 40960 | reasoning+tools on NPU |
| `qwen3.5-4b-FLM` | qwen3.5:4b | 262144 | vision+reasoning+tools on NPU |
| `gemma4-it-e2b-FLM` | gemma4-it:e2b | 131072 | **audio + chat-transcription + vision** on NPU |
| `gemma3-4b-FLM` | gemma3:4b | 131072 | vision on NPU |

### iGPU / CPU GGUF tier — chat, reasoning, code
| id | checkpoint | ctx | note |
|---|---|---|---|
| `Granite-4.1-8B-GGUF` | unsloth/granite-4.1-8b-GGUF:Q4_K_M | 131072 | no-thinking, tool-calling — the hermes-skill's robust bot model |
| `Qwen3.6-35B-A3B-NoThinking` | unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL | 262144 | **current Hermes default** (3B-active MoE) |
| `Qwen3.6-35B-A3B-GGUF` / `-ThinkingCoder` | (SAME checkpoint as NoThinking) | 262144 | template variants, NOT different weights |
| `Qwen3.6-35B-A3B-GGUF-Strix-Q4_K_M` | 0xSero/…-Strix:Q4_K_M | 262144 | Strix-tuned quant |
| `Qwen3.6-27B-GGUF` | unsloth/Qwen3.6-27B-GGUF:UD-Q4_K_XL | 262144 | dense 27B |
| `Nemotron-3-Nano-30B-A3B-GGUF` | unsloth/…:UD-Q4_K_XL | 1048576 | 1M ctx, 3B-active |
| `Mellum-4b-base-…Q8_0` | JetBrains/Mellum-4b-base-gguf:Q8_0 | 8192 | **FIM code completion** (Task.FIM) |
| `DeepSeek-Qwen3-8B-GGUF` | unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_1 | 131072 | reasoning |
| `Qwen3-0.6B/8B/14B`, `Jan-v1-4B`, `Bonsai-8B`, `Llama-4-Scout-17B-16E` | (unsloth/various) | 40k–10M | utility / vision / MoE |

### Multimodal & embeddings — **already served (the key finding)**
| id | checkpoint | modality | maps to Task |
|---|---|---|---|
| `SD-Turbo` | stabilityai/sd-turbo:safetensors | **image gen** | **IMAGE_GEN (item 86 — artifact EXISTS)** |
| `kokoro-v1` | mikkoph/kokoro-onnx | **TTS (voices)** | **AUDIO_TTS (item 85 — artifact EXISTS)** |
| `nomic-embed-text-v2-moe-GGUF` | nomic-ai/…:Q8_0 | embeddings 768D | semantic cache (CA1) |
| (vision label) Gemma-4*, Qwen3.6*, Llama-4-Scout, qwen3.5-4b-FLM | — | image **input** | VISION/EXTRACTION/OCR_DOC |

## 3. Recipe ↔ model-card validation (your "recipes must match cards")

The `checkpoint` field IS the HF `repo:quant`, so each recipe is traceable to a card. Findings to act on:
- **`Qwen3.6-35B-A3B-NoThinking` / `-ThinkingCoder` share the BASE `Qwen3.6-35B-A3B-GGUF` checkpoint** —
  the behavior difference is the chat-template / thinking flag in `recipe_options`, NOT different
  weights. The "model card" for all three is the one base Qwen3.6-35B-A3B repo. Correct, but document
  it so the roster isn't read as three distinct models.
- **`Bonsai-8B-gguf:Q1_0`** — a 1-bit quant. Far below the card's intended quality; flag as
  experimental-only, do NOT route real tasks to it.
- **`Llama-4-Scout-17B-16E` ctx=10485760 (10M)** — that is the card's *theoretical* max; serving at 10M
  ctx is memory-impossible on 128 GB (K1/rule-5). Cap the recipe context to a runnable value.
- **`kokoro-v1` = `mikkoph/kokoro-onnx`** — a community ONNX port; the canonical card is
  `hexgrad/Kokoro-82M` (Apache-2.0). VERIFY the port matches the card's voices/license before wiring
  to AUDIO_TTS (item 85). Apache-2.0 base = permissive (unlike Higgs item 93 NC).
- **`SD-Turbo` = `stabilityai/sd-turbo`** — official, but under the **Stability AI Community/Non-
  commercial-ish license** — same human-decision class as Higgs item 93; flag license before
  productizing IMAGE_GEN.
- **FLM models use short `name:tag` refs** (`llama3.2:1b`, `gemma4-it:e2b`) — FLM's own registry, not a
  direct HF card. Cross-reference FLM's model list to the upstream cards for provenance.
- **GGUF quants are predominantly `unsloth/` UD-Q4_K_M / UD-Q4_K_XL** — dynamic quants, card-consistent.

## 4. Dependency status (your "make sure lemonade + deps are updated")
| component | installed | note |
|---|---|---|
| lemonade | **10.6.0** | current per harness N1 (requires FLM ≥0.9.42) |
| FastFlowLM (FLM) | **v0.9.42** | harness N1 notes **v0.9.43 available (MEDIUM risk)** — deb via sudo dpkg; disruptive to the live NPU |
| amd-gaia | 0.19.0 | verified working (strix-halo §7) |
| torch | 2.5.1+rocm6.2 | ROCm 6.2; pinned for gfx1151 stability |
| transformers | 4.57.2 | |
| sentence-transformers | 5.4.1 | NOTE: segfaults on XDNA2 (CA1) — use nomic-embed via lemonade, not this |
**Updates are NOT auto-applied here**: a lemonade/FLM update restarts the fleet that Hermes + the
running loops depend on, and the FLM deb needs sudo — both are user-gated (lanes-up window).

## 5. Recommended bot roster (local-first, $0) — once wired
| Hermes role | model | tier |
|---|---|---|
| `model.default` + `cheap_model` | **Granite-4.1-8B-GGUF** (no-think, tool-robust) OR keep Qwen3.6-35B-A3B-NoThinking | iGPU via 13305 |
| lightweight aux (title/approval/mcp/skills_hub) | `llama3.2-1b-FLM` | **NPU via 13305** |
| vision aux | `Gemma-4-E4B-it-GGUF` / `qwen3.5-4b-FLM` | iGPU/NPU |
| code/FIM | `Mellum-4b` | iGPU |
| embeddings (cache) | `nomic-embed-text-v2-moe-GGUF` | router |
| image (research/showcase) | `SD-Turbo` (license-gated) | GPU |
| TTS/voices | `kokoro-v1` (verify card/license) | GPU |

## 6. Next actions (gated)
- **Multimodal unblock**: items 85 (AUDIO_TTS→kokoro) + 86 (IMAGE_GEN→SD-Turbo) now have served
  artifacts → can move from needs-experiment to "register the ModelEntry + license check" (kokoro
  Apache permissive; SD-Turbo license = human decision like Higgs).
- **Bot local-first**: already mostly there (default = local no-think model, MCP bridge absolute path).
  Refinement (gateway-STOPPED edit): point lightweight aux at a dedicated NPU provider, OR keep the
  omnirouter. Per hermes-skill rule #5, define `lemonade-npu: {api: http://127.0.0.1:13305/v1}` — note
  the NPU IS 13305 now, not 13306.
- **Two-port decision**: keep 13307 for triune iGPU stability, or consolidate to 13305 to free memory.
- **Updates**: FLM 0.9.43 + any lemonade bump are lanes-up + sudo — schedule a window.
