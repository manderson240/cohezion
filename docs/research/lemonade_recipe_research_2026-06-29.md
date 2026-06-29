# Lemonade Recipe Research — 2026-06-29

## Goal
Produce finely-tuned *model recipes* (capability profiles + inference parameters) for the Cohezion local fleet served by the Lemonade OmniRouter on port 13305.

## Method
1. Probed `http://localhost:13305/v1/models` to enumerate downloaded/available models, labels, backends, and recipe options.
2. Ran a small set of non-streaming `/v1/chat/completions` prompts against a subset of text models to capture TTFT, generation rate, and thinking/reasoning overhead.
3. Curated `src/cohezion/inference/lemonade_recipes.py` with empirical + model-card-derived recipes.
4. Extended `src/cohezion/inference/model_card_harness.py` to consume the recipe registry.
5. Added `tests/inference/test_lemonade_recipes.py` with source-level mocks for all I/O.

## Models discovered live

31 models were returned by the Lemonade API.  The text-generation subset relevant to recipes:

| Model ID | Recipe | Downloaded | Context window | Labels |
|---|---|---|---|---|
| `llama3.2-1b-FLM` | `flm` | yes | 131072 (loaded ctx=4096) | — |
| `gemma3-4b-FLM` | `flm` | yes | 262144 (loaded ctx=8192) | vision, reasoning, tool-calling |
| `gemma4-it-e2b-FLM` | `flm` | yes | 262144 (loaded ctx=4096) | — |
| `qwen3.5-4b-FLM` | `flm` | yes | 262144 (loaded ctx=8192) | vision, reasoning, tool-calling |
| `deepseek-r1-0528-8b-FLM` | `flm` | yes | 40960 | reasoning |
| `Gemma-4-E2B-it-GGUF` | `llamacpp` | yes | 131072 (loaded ctx=4096) | tool-calling, vision |
| `Gemma-4-E4B-it-GGUF` | `llamacpp` | yes | 131072 (loaded ctx=8192) | tool-calling, vision |
| `Gemma-4-26B-A4B-it-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=16384) | hot, tool-calling, vision |
| `Gemma-4-31B-it-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=16384) | hot, tool-calling, vision |
| `DeepSeek-Qwen3-8B-GGUF` | `llamacpp` | yes | 131072 (loaded ctx=16384) | reasoning, tool-calling |
| `DeepSeek-R1-0528-Qwen3-8B-Q4_1` | — | — | 32768 | — |
| `Qwen3-0.6B-GGUF` | `llamacpp` | yes | 40960 (loaded ctx=8192) | reasoning, tool-calling |
| `Qwen3-8B-GGUF` | `llamacpp` | yes | 4096 (loaded ctx=4096) | reasoning, tool-calling |
| `Qwen3.5-35B-A3B-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=16384) | vision, tool-calling |
| `Qwen3.6-27B-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=16384) | vision, tool-calling |
| `Qwen3.6-35B-A3B-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=16384) | vision, tool-calling, hot |
| `Qwen3.6-35B-A3B-ThinkingCoder` | `llamacpp` | yes | 262144 (loaded ctx=16384) | coding, custom, tool-calling, vision |
| `Qwen3.6-35B-A3B-NoThinking` | `llamacpp` | yes | 262144 (loaded ctx=16384) | custom, hot, tool-calling, vision |
| `Qwen3-Coder-30B-A3B-Instruct-GGUF` | `llamacpp` | yes | 262144 (loaded ctx=32768) | coding, tool-calling, hot |
| `Bonsai-1.7B-gguf` | `llamacpp` | yes | 32768 | llamacpp, tool-calling |
| `Bonsai-4B-gguf` | `llamacpp` | yes | 32768 | llamacpp, tool-calling |
| `Bonsai-8B-gguf` | `llamacpp` | yes | 65536 (loaded ctx=16384) | llamacpp, tool-calling |
| `Nemotron-3-Nano-30B-A3B-GGUF` | `llamacpp` | yes | 1048576 | tool-calling |
| `Llama-4-Scout-17B-16E-Instruct-GGUF-Q4_K_M` | `llamacpp` | yes | 10485760 | custom, vision, tool-calling |

Other downloaded models (image/tts/embed/whisper) are outside the scope of text recipes and are ignored by the recipe registry.

## Empirical probe highlights

Probes used 5 short prompts (short answer, code, math, summarization, structured JSON) with `temperature=0.5`, non-streaming, `max_tokens` 300-500.  Measurements are approximate (n≈1-5, no warm-up averaging).

| Model | TTFT (ms) | Tokens/sec | Reasoning chars (typical) |
|---|---|---|---|
| `llama3.2-1b-FLM` | ~1400 | ~45 | 0 |
| `Gemma-4-E2B-it-GGUF` | ~3600-6700 | ~35 | 650-1800 |
| `Gemma-4-E4B-it-GGUF` | ~3400-9000 | ~28 | 440-1800 |
| `DeepSeek-Qwen3-8B-GGUF` | ~7500-13000 | ~15-20 | 700-1500 |
| `Qwen3-0.6B-GGUF` | ~350-1100 | ~70-90 | 0-450 |
| `Qwen3.5-35B-A3B-GGUF` | ~5000-19000 | ~15-25 | 450-1100 |
| `Gemma-4-26B-A4B-it-GGUF` | ~3300-15000 | ~20-30 | 360-1700 |
| `Gemma-4-31B-it-GGUF` | ~5000-47000 | ~10-15 | 150-1400 |
| `qwen3.5-4b-FLM` | not probed (live) | estimated | estimated |

Key observations:
* **FLM/NPU models** have the lowest TTFT and highest sustained throughput; best for sensing, routing, and quick structured decisions.
* **Gemma-4-E4B** emits substantial thinking traces (≈2260 tokens on code tasks).  This matches the existing harness constant and is now encoded in its recipe.
* **DeepSeek-Qwen3-8B** is slow on this machine (Vulkan backend, large load time) but produces strong reasoning traces; it should be a CPU-lane reasoning fallback, not a latency-sensitive default.
* **Qwen3.5-35B-A3B** shows high variance — TTFT spikes when the model is cold.  It benefits from keeping the weights resident.
* **Gemma-4-31B** is very slow on AVX-VNNI for code prompts; better suited to long-horizon architect tasks with small output budgets.

## Recipe architecture decisions

`src/cohezion/inference/lemonade_recipes.py` introduces:

* `ModelRecipe` — dataclass containing capabilities, lane affinity, sampling parameters, task scores, system prompts, output budgets, and empirical metrics.
* `CapabilityProfile` — 0-1 scores for reasoning, coding, creativity, instruction following, long-context, multilingual.
* `OutputBudgets` — headroom tokens per output type.  The harness adds thinking overhead for thinking-mode models.
* `EmpiricalMetrics` — TTFT, tokens/sec, thinking-overhead tokens, and an `estimated` flag.
* `LEMONADE_RECIPES` — curated registry of 23 text models.
* `get_recipe(model_id)` — exact lookup.
* `best_model_for_task(task, lane, prefer_downloaded)` — score-based selection.
* `get_inference_params(model_id, output_type, task_type)` — OpenAI-compatible payload fragment.
* `probe_live_models(port)` / `discover_from_live_models(models)` — live discovery helpers.

The design keeps `model_card_harness.py` backward-compatible: legacy prefix/heuristic logic is used for unregistered models, and recipe-aware paths are used for thinking models and Qwen3 family models.

## Trade-offs

1. **Empirical vs. estimated metrics.**  Most recipes include at least one measured data point, but large models were only probed once.  Values marked `estimated=True` should be replaced by a formal 20-prompt benchmark run.
2. **Task scores are hand-tuned.**  They are grounded in labels and model-card claims but have not been validated against a downstream task corpus.
3. **Context-window tension.**  Lemonade reports large native context windows, but `recipe_options.ctx_size` is what the lane actually loads.  Recipes store the native window; callers must respect the live `ctx_size` when constructing prompts.
4. **Thinking-mode budget.**  For Gemma-4, the recipe budgets `code=600` plus the measured 2260-token overhead.  This is larger than the old fixed `_OUTPUT_TYPE_MAX_TOKENS["code"]=600`, which could truncate the answer.  The harness now uses the recipe for thinking models and legacy defaults for non-thinking models.

## Gaps for future research

* Add streaming-based TTFT/throughput measurements to populate `observed_ttft_ms_p50` and `observed_tokens_per_sec` in `registry.py` from the same recipe data.
* Validate task scores against the existing Cohezion task classifier corpus.
* Add recipe-aware quality gating in `fleet.route()` so a model is only chosen when its recipe score exceeds a threshold.
* Investigate why `Gemma-4-31B-it-GGUF` is 2-4x slower than `Gemma-4-26B-A4B-it-GGUF` on code prompts and whether KV8 or thread-count tuning helps.
* Run a structured-json correctness sweep for each recipe to set `output_budgets.structured` per model.
* Extend recipes to multimodal models once `image_tier.py` consumes recipe data.

## Files created/modified

* Created `src/cohezion/inference/lemonade_recipes.py`
* Modified `src/cohezion/inference/model_card_harness.py`
* Created `tests/inference/test_lemonade_recipes.py`
* Created `docs/research/lemonade_recipe_research_2026-06-29.md`
