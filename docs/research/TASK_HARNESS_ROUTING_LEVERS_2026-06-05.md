---
title: "Task-Aware AND Harness-Aware Routing — Levers (HF/arXiv research)"
date: 2026-06-05
theme: "the right MODEL and the right HARNESS for the right TASK, on a $0 local AMD Strix Halo fleet"
method: "~50-round HF/arXiv research, every HF id + arXiv id verified via huggingface_hub.model_info / WebFetch / WebSearch; classified against Cohezion's calibrated invariants; cost recast to latency/quality (CC2 λ=100 guard)"
classification_key: "NEW = not in our docs | grounded = real source verified (may already be integrated) | needs-experiment = plausible, unproven on our fleet | regression-risk = could conflict with a calibrated invariant"
honesty_policy: "Never fabricate a citation. Unverifiable → UNVERIFIED, omitted from the table. A smaller verified+fleet-runnable set beats a long hype list. Default new claims to needs-experiment, NOT confirmed."
extends: "docs/research/LEVERS_AND_KNOBS_2026-06-05.md (spec-decode/KV-quant/LLMLingua/UCCI/rsLoRA/LightRAG/Unsloth — NOT repeated here)"
---

# Task-Aware AND Harness-Aware Routing — Levers

The existing router (`CostAwareRouter.select_model`) routes by **complexity** only
(simple/medium/complex → tier model). It is **not task-aware**: an extraction job, a
FIM/code-completion, a rerank, and a math proof of the same "complexity" all get the same
tier model. And nothing in the stack picks a **harness** (CoT vs ReAct vs grammar-constrained
vs tool-loop) as a function of task×tier.

Two seams already exist and are the natural wiring targets for everything below:

| Seam | File / symbol | What it gives us |
|---|---|---|
| **Task→model** (declarative) | `inference/registry.py` — `Task` enum + `ModelEntry.task_affinity` + `FleetRegistry.for_task(task)` | A model↔task↔lane map. **`for_task()` already exists.** The `Task` enum is missing EXTRACTION / VISION / EMBEDDING / RERANK / FIM / FUNCTION_CALL / OCR_DOC. |
| **Task→model** (routing brain) | `swarm/cost_aware_router.py` — `select_model(query, max_cost_usd, cache_hit_rate)`; `models/model_registry.py` — `get_best_for_task(task, budget, prefer_fast)` | The cost/quality routing brain. `get_best_for_task` is the *only* task-typed entrypoint today, but it just forwards `task` as a query string to a complexity analyzer — the task type is **discarded**. |
| **Task→harness** | `inference/orchestrator.py` — `pre_dispatch_classifier`; `inference/triune_orchestrator.py` — `PrefillActivationRouter(base_classifier=classify_task)`; `inference/task_classifier.py` | Per-prompt override of tier + quality gate by `output_type`. The place to add scaffold selection. |

> **Drift note (do not assume one unified router):** `config/model_profiles.yaml` lives in a
> *different world* (phi3 / qwen3-coder:32b / deepseek-r1:8b) than `FleetRegistry`
> (Gemma-4 4-lane). `CostAwareRouter` reads the YAML; `fleet.route()` reads the registry.
> Each lever row says **which** seam it targets.

> **CC2 guard (cost recast):** RouteLLM/UCCI-style routing optimizes **dollars**. On a $0
> local fleet, CC2 says local always wins at $0.01 (λ=100). So every "routing" lever here is
> recast as **local-specialist-quality vs local-generalist-quality, with latency as the
> tiebreaker**. Any lever that would *default to cloud* is flagged `regression-risk` vs CC2.

---

## PART A — Task→Model levers (small specialist beats big generalist)

Fleet-runnability is graded honestly in three classes:
- **CHAT-GGUF** — loadable by llama.cpp/lemonade chat lanes today.
- **VLM-GGUF(mmproj)** — loadable by `llama-mtmd`/server *if* the vision projector is passed; **lemonade exposing `--mmproj` is unproven → needs-experiment.**
- **ENCODER** — embedding/rerank model; runs (sentence-transformers/ONNX, or `llama-server --embeddings` for GGUF encoders) but **NOT via the chat lanes** — wires at the `semantic_cache.py` nomic-embed seam, not `for_task`.
- **NOT-LOADABLE** — bespoke arch llama.cpp can't load even if "weights exist".

| # | Lever (model) | Source (HF id / arXiv) | Wins at task | Fleet-runnable? (GGUF / size / license) | Cohezion wiring | Class |
|---|---|---|---|---|---|---|
| A1 | **LFM2.5-VL-1.6B-Extract** | `LiquidAI/LFM2.5-VL-1.6B-Extract-GGUF` ✅ | Image→YAML field **extraction** (the seed) | VLM-GGUF(mmproj). Q4_0 696MB → F16 2.34GB; `mmproj-…-F16.gguf` present. License `lfm1.0` (verify commercial terms). | New `Task.EXTRACTION` + `Task.VISION`; register as `ModelEntry` in `registry.py`; `for_task(EXTRACTION)` | NEW / needs-experiment |
| A2 | **NuExtract-2.0-2B** | `numind/NuExtract-2.0-2B` ✅ (MIT) | Structured **extraction** (text+image→schema). Direct A1 peer, permissive license | image-text-to-text; **no GGUF tag** → likely NOT-LOADABLE on lanes today (verify a community GGUF) | Same `Task.EXTRACTION`; fallback if A1 license blocks commercial | NEW / needs-experiment |
| A3 | **NuExtract-1.5** | `numind/NuExtract-1.5` ✅ (MIT) | Text-only **extraction**, multilingual | text-generation; no official GGUF (a `bartowski/NuExtract-1.5-GGUF` does **not** exist — UNVERIFIED community quant) | `Task.EXTRACTION` text path | NEW / needs-experiment |
| A4 | **Qwen2.5-Coder-1.5B** | `Qwen/Qwen2.5-Coder-1.5B` ✅ + `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` ✅ (apache-2.0) | **FIM / code-completion** (native `<|fim_*|>` tokens) — a fill-in-middle specialist a chat model can't do | CHAT-GGUF. `unsloth/Qwen2.5-Coder-1.5B-Instruct-128K-GGUF` ✅ also exists. ~1.5B → fits NPU/iGPU | New `Task.FIM`; `ModelEntry` on iGPU lane; `for_task(FIM)` | NEW / needs-experiment |
| A5 | **Qwen2.5-Coder-0.5B** | `Qwen/Qwen2.5-Coder-0.5B` ✅ (apache-2.0) | Ultra-cheap FIM for the **NPU** lane | CHAT-GGUF (community quants); 0.5B = NPU-class | `Task.FIM` NPU tier | NEW / needs-experiment |
| A6 | **Qwen2.5-Math-1.5B-Instruct** | `Qwen/Qwen2.5-Math-1.5B-Instruct` ✅ (apache-2.0) | **Math/boxed-answer reasoning** — beats general 1.5B on GSM/MATH | CHAT-GGUF (community quants); 1.5B | `Task.MATH` already in enum → add `ModelEntry` + `for_task(MATH)` | NEW / needs-experiment |
| A7 | **Qwen3-Embedding-0.6B** | `Qwen/Qwen3-Embedding-0.6B` ✅ + `…-0.6B-GGUF` ✅ (apache-2.0) | **Embedding** (MTEB-strong at 0.6B) — candidate to replace/augment nomic-embed for cache+RAG | ENCODER. GGUF runs via `llama-server --embeddings`; 0.6B | **`semantic_cache.py`** encoder seam (NOT `for_task`). ⚠ CA1: 768-D nomic threshold=0.58 is calibrated — a new encoder needs **re-calibration** | NEW / regression-risk (CA1) |
| A8 | **Qwen3-Reranker-0.6B** | `Qwen/Qwen3-Reranker-0.6B` ✅ (apache-2.0, 1.2M dl) | **Reranking** retrieved chunks (cross-encoder) — large quality lift in RAG for ~0.6B | ENCODER (text-ranking); CPU/iGPU. GGUF community quants exist | New `rerank()` stage in `knowledge_graph/graphrag_engine.py` after vector seed | NEW / needs-experiment |
| A9 | **bge-reranker-v2-m3** | `BAAI/bge-reranker-v2-m3` ✅ (apache-2.0, 14M dl) | **Reranking**, multilingual, battle-tested baseline | ENCODER; CPU-fine (~568M). Permissive | Same rerank stage; safer-license alternative to A8 | grounded / needs-experiment |
| A10 | **mxbai-rerank-base-v2** | `mixedbread-ai/mxbai-rerank-base-v2` ✅ (apache-2.0) | **Reranking** — 2025 SOTA-for-size cross-encoder | ENCODER | rerank stage option | NEW / needs-experiment |
| A11 | **jina-reranker-v2-base-multilingual** | `jinaai/jina-reranker-v2-base-multilingual` ✅ | Reranking, fast | ENCODER. **License `cc-by-nc-4.0` → non-commercial** | rerank stage (research only) | grounded / regression-risk (license) |
| A12 | **bge-small-en-v1.5** | `BAAI/bge-small-en-v1.5` ✅ (MIT, 55M dl) | Tiny **embedding** (33M) for cheap cache/RAG on NPU/CPU | ENCODER; trivially small | `semantic_cache.py` lightweight-encoder option (⚠ CA1 recal) | grounded / regression-risk (CA1) |
| A13 | **answerai-colbert-small-v1** | `answerdotai/answerai-colbert-small-v1` ✅ (apache-2.0) | **Late-interaction retrieval** (ColBERT, token-level) — better recall than single-vector for some RAG | ENCODER; small | optional retrieval upgrade in `knowledge_graph/` | NEW / needs-experiment |
| A14 | **Arch-Function-3B** | `katanemo/Arch-Function-3B` ✅ + `Arch-Function-3B.gguf` ✅ | **Function-calling / tool-use** — BFCL-for-size specialist; beats general 3B at tool selection | CHAT-GGUF ✅; 3B fits iGPU. **License `other` (Katanemo) — verify commercial** | New `Task.FUNCTION_CALL`; `ModelEntry`; tool-loop harness consumer | NEW / needs-experiment |
| A15 | **Arch-Function-1.5B** | `katanemo/Arch-Function-1.5B` ✅ | Function-calling at NPU/iGPU size | likely CHAT-GGUF (verify quant); 1.5B. License `other` | `Task.FUNCTION_CALL` smaller tier | NEW / needs-experiment |
| A16 | **Hammer2.1-3b** | `MadeAgents/Hammer2.1-3b` ✅ | Function-calling (BFCL-strong small model) | `other` license; verify GGUF | `Task.FUNCTION_CALL` alt | NEW / needs-experiment |
| A17 | **Hammer2.1-1.5b** | `MadeAgents/Hammer2.1-1.5b` ✅ | Function-calling at 1.5B | **License `cc-by-nc-4.0` → non-commercial** | research-only alt | grounded / regression-risk (license) |
| A18 | **xLAM-2-3b-fc-r** | `Salesforce/xLAM-2-3b-fc-r` ✅ | Function-calling + multi-turn (xLAM line) | **License `cc-by-nc-4.0` → non-commercial** | research-only | grounded / regression-risk (license) |
| A19 | **GOT-OCR2.0** | `stepfun-ai/GOT-OCR2_0` ✅ (apache-2.0) | **OCR / document** parsing (formulas, tables) | image-text-to-text, **bespoke arch — NOT-LOADABLE in llama.cpp** today (transformers/vLLM only) | `Task.OCR_DOC` — but runs as a sidecar service, not a chat lane | NEW / needs-experiment |
| A20 | **dots.ocr** | `rednote-hilab/dots.ocr` ✅ (MIT) | **OCR/doc layout** parsing, multilingual | bespoke VLM → **NOT-LOADABLE on lanes** (sidecar) | `Task.OCR_DOC` sidecar | NEW / needs-experiment |
| A21 | **RolmOCR / olmOCR-7B** | `reducto/RolmOCR` ✅, `allenai/olmOCR-7B-0225-preview` ✅ (apache-2.0) | High-fidelity **document OCR** | 7B VLMs, sidecar/vLLM; too big for lanes alongside Gemma fleet | `Task.OCR_DOC` heavy sidecar (OOM-gate) | grounded / needs-experiment |
| A22 | **SmolVLM-Instruct** | `HuggingFaceTB/SmolVLM-Instruct` ✅ + `ggml-org/SmolVLM-Instruct-GGUF` ✅ (apache-2.0) | Small general **VLM** (captioning, VQA) — apache-licensed VLM if A1's `lfm1.0` blocks | VLM-GGUF(mmproj) ✅ — `ggml-org` ships official mmproj | `Task.VISION` fallback; same `--mmproj` experiment as A1 | grounded / needs-experiment |
| A23 | **InternVL3-2B** | `OpenGVLab/InternVL3-2B` ✅ (apache-2.0) | Strong small **VLM** (doc+chart VQA) | bespoke arch → mostly NOT-LOADABLE on lanes; sidecar | `Task.VISION` sidecar alt | grounded / needs-experiment |
| A24 | **granite-3.3-2b-instruct** | `ibm-granite/granite-3.3-2b-instruct-GGUF` ✅ (apache-2.0) | General mid-small with strong **instruction-following** (good harness *consumer* per Lin et al.) | CHAT-GGUF ✅; 2B | candidate mid-tier harness-consumer model | grounded / needs-experiment |
| A25 | **SmolLM3-3B** | `ggml-org/SmolLM3-3B-GGUF` ✅ (apache-2.0) | Fully-open 3B, native **tool-calling**, 128K via YARN | CHAT-GGUF ✅; ~2GB | general tool-loop consumer on iGPU | grounded / needs-experiment |
| A26 | **nomic-embed-text-v2-moe** | `nomic-ai/nomic-embed-text-v2-moe` ✅ (apache-2.0) | **Embedding** (already our cache encoder) — listed for completeness; CA1-calibrated | ENCODER (already wired, lemonade :13305) | `semantic_cache.py` (current, 768-D, threshold 0.58) | grounded / ALREADY-CALIBRATED |

---

## PART B — Task→Harness levers (right scaffold for task × tier)

Anchored on the **non-monotonic harness thesis** (Lin et al., arXiv:2605.30621 — *already
integrated*, vault `RETRO-2026-06-01-harness-updating-vs-benefit.md`): **harness-benefit is
non-monotonic — mid-tier gains most, weak models can't faithfully follow scaffolds, strong
models gain less.** This maps to a **tier-conditioned harness policy** in
`pre_dispatch_classifier`.

| # | Lever (harness) | Source | Wins at task×tier | Fleet wiring | Class |
|---|---|---|---|---|---|
| B1 | **Tier-conditioned scaffold selection** (NPU→plain CoT/single-shot; iGPU mid→ReAct/reflexion/tool-loop; CPU/cloud→minimal) | arXiv:2605.30621 (Lin et al.) ✅ | Stop wasting ReAct on the 1-2B NPU (it can't follow it) and stop over-scaffolding the strong tier | `orchestrator.py pre_dispatch_classifier` returns a `harness` field alongside tier/gate | **grounded** (paper integrated) / needs-experiment (the *routing rule* is unbuilt) |
| B2 | **Grammar-constrained decoding (GBNF) for weak-tier structured tasks** | llama.cpp GBNF (DeepWiki) ✅; XGrammar arXiv:2411.15100 ✅ (<40µs/token JSON, 3×–100× speedup) | Extraction/classification/structured-output on the **NPU**: forces valid JSON/schema **without** requiring reasoning ability — the harness substitute for weak models | `task_classifier.py` sets `grammar=<gbnf>` for `output_type=structured/categorical`; pass `--grammar`/`json_schema` to lemonade/llama-server. **Pairs directly with A1 extraction** | NEW / needs-experiment |
| B3 | **"Lost in Space" token-optimized grammars** | arXiv:2502.14969 ✅ | Tune the GBNF so constrained decoding doesn't *degrade* quality (whitespace/token-boundary traps) | refinement of B2 grammars | NEW / needs-experiment |
| B4 | **SLM targeted fine-tune for tool-calling beats large general** | arXiv:2512.15943 ✅ ("Small LMs for Efficient Agentic Tool Calling") | Confirms A14–A18: a small tuned tool-caller > large generalist in a tool-loop harness | justifies `Task.FUNCTION_CALL` lane + tool-loop on iGPU | grounded / needs-experiment |
| B5 | **ReflAct (goal-state reflection)** for the mid-tier iGPU | arXiv:2505.15182 ✅ | World-grounded reflection harness; mid-tier is exactly the tier Lin et al. says benefits | a `harness="reflact"` branch for `REASONING`/`LONG_HORIZON` on iGPU only | grounded / needs-experiment |
| B6 | **Scaffold source-code taxonomy** (pick the minimal scaffold that matches the task's control flow) | arXiv:2604.03515 ("Inside the Scaffold") ✅ | A taxonomy to *choose* scaffold by task shape rather than always-ReAct | design input for B1's harness map | grounded / needs-experiment |
| B7 | **Coding-agent harness/context-engineering lessons** | arXiv:2603.05344 ("Building AI Coding Agents for the Terminal") ✅ | Context-compaction + tool-registration patterns for the CODE_GEN tool-loop | informs the iGPU code tool-loop harness | grounded / needs-experiment |

---

## PART C — Task→Model *routing brain* levers (how to choose, on $0 fleet)

| # | Lever | Source | What it does | Fleet wiring (CC2-recast) | Class |
|---|---|---|---|---|---|
| C1 | **Arch-Router-1.5B** (preference-aligned domain×action router) | `katanemo/Arch-Router-1.5B` ✅; arXiv:2506.16655 ✅ | A 1.5B model that maps a query to (domain, action) and routes to the preferred model — **exactly the task-classifier `get_best_for_task` lacks**. SOTA query↔preference match | Replace the keyword `QueryComplexityAnalyzer` with an Arch-Router NPU call that emits a `Task`; feed `FleetRegistry.for_task()`. License `other` (Katanemo) — verify | NEW / needs-experiment |
| C2 | **kNN beats complex learned routers** | arXiv:2505.12601 ✅ | A simple kNN over embedded past queries can match/beat learned routers — cheap, no training, reuses our nomic vectors | a kNN over logged (query-embedding → winning-tier) in `cost_aware_router.py` | NEW / needs-experiment |
| C3 | **IR3DE linear router** | arXiv:2606.06098 ✅ (Jun 2026) | Ridge-regression router → cheap/fast per-prompt routing to domain experts | linear head over nomic-embed → tier; CPU-only, $0 | NEW / needs-experiment |
| C4 | **Meta-learned cost-perf router** | arXiv:2606.06178 ✅ (Jun 2026) | Routes from *implicit* cost-performance preferences via meta-learning | latency-recast objective for `select_model` | NEW / needs-experiment |
| C5 | **Routing-collapse guard** | arXiv:2602.03478 ✅ ("When Routing Collapses") | Learned routers degenerate to one model; a guard/regularizer prevents it | a diversity check in any learned router we add (C1–C4) — falsifiable safety gate | NEW / needs-experiment |
| C6 | **LLMRouterBench / RouterBench eval** | arXiv:2601.07206 ✅; arXiv:2403.12031 ✅ | The benchmark to *measure* any routing change so it can come back negative | the eval harness for C1–C4 (falsifiable-eval-harness skill) | grounded / needs-experiment |
| C7 | **Capability Instruction Tuning (dynamic routing)** | arXiv:2502.17282 ✅ | Tune a model to describe its own capability → dynamic routing paradigm | research input; not a near-term wire | grounded / needs-experiment |

---

## Top 5 to build first (highest leverage, lowest risk, all $0-local, all falsifiable)

1. **Add the missing `Task` enum members + populate `for_task`** (EXTRACTION, VISION, FIM,
   FUNCTION_CALL, RERANK, OCR_DOC). Pure additive in `inference/registry.py`. **No model
   downloaded yet** — this just makes the seam expressible.
   *Falsifiable check:* `for_task(Task.FIM)` returns a non-empty list AND every other
   `for_task` still returns its old set (no regression). Comes back negative if any existing
   `task_affinity` set changed.

2. **Register LFM2.5-VL-1.6B-Extract (A1) and prove `--mmproj` on lemonade.**
   *Falsifiable check (the decisive one):* load `mmproj-LFM2.5-VL-1.6B-Extract-F16.gguf` +
   Q4_K_M on iGPU :13307; run a 10-image field-extraction set at temp=0; **PASS only if** (a)
   lemonade/llama-server actually accepts the mmproj and returns text, and (b) extraction
   accuracy ≥ a big-general-VLM baseline at a fraction of VRAM. If lemonade can't pass mmproj
   → result is an honest NULL and we run it as a `llama-mtmd` sidecar instead.

3. **Grammar-constrained decoding on the NPU for structured/extraction tasks (B2).**
   Wire `task_classifier.py` to emit a GBNF/`json_schema` for `output_type ∈
   {structured, categorical, extraction}`.
   *Falsifiable check:* 3-arm on NPU — (free-form) vs (GBNF-constrained) vs (mid-tier
   unconstrained) on a JSON-extraction set, temp=0, word-boundary scoring. Lever WINS only if
   GBNF-NPU matches mid-tier *valid-JSON rate* at lower latency. Can return False if GBNF
   degrades content quality ("Lost in Space", B3).

4. **Qwen3-Reranker-0.6B (A8) as a rerank stage in `graphrag_engine.py` (A8/A9).**
   *Falsifiable check:* treatment = vector-seed → rerank top-K; baseline = current
   vector-only; recall@k / answer-accuracy on a held-out QA set over the `neurons` graph,
   temp=0. WINS only if rerank lifts accuracy enough to justify the added CPU latency.

5. **Arch-Router-1.5B (C1) as the task classifier feeding `get_best_for_task`.**
   Today `get_best_for_task(task, ...)` *throws the task type away* (forwards it as a query to
   the complexity analyzer). Replace with an NPU Arch-Router call emitting a `Task`, then
   `FleetRegistry.for_task()`.
   *Falsifiable check:* on RouterBench/a labeled task set, Arch-Router task-classification
   accuracy vs the current keyword analyzer; AND end-task quality with task-routed model vs
   complexity-routed. WINS only if both improve. Guard against routing-collapse (C5).

> All five touch **no calibrated invariant** if done additively. The single live
> regression-risk to watch: **A7/A12 (new embedding encoder) vs CA1** — swapping the cache
> encoder requires re-deriving the similarity threshold (CA1 is encoder-dimension-calibrated:
> 0.58@768-D). Do NOT change the encoder without re-running the CA1 calibration experiment.

---

## LFM2.5-VL-1.6B-Extract — verdict

**VERDICT: ADOPT (register in FleetRegistry as the EXTRACTION/VISION specialist) — gated on
one falsifiable lemonade-mmproj experiment.**

- **Verified real.** `LiquidAI/LFM2.5-VL-1.6B-Extract-GGUF` exists; files confirmed via
  `huggingface_hub`:
  `LFM2.5-VL-1.6B-Extract-{Q4_0,Q4_K_M,Q5_K_M,Q6_K,Q8_0,F16}.gguf` **plus**
  `mmproj-LFM2.5-VL-1.6B-Extract-{F16,Q8_0}.gguf` (the vision projector — present, so it is
  genuinely multimodal-runnable in llama.cpp).
- **Size:** Q4_0 **696 MB** → F16 **2.34 GB** (+ ~mmproj). NPU/iGPU-class; OOM-safe alongside
  the Gemma fleet via `ResourceGuard.can_load_model`.
- **License:** `lfm1.0` (LiquidAI's own license) — **verify commercial terms before
  production**; if blocked, fall back to **A2 NuExtract-2.0-2B (MIT)** or **A22 SmolVLM-GGUF
  (apache-2.0)** for the same `Task.EXTRACTION`/`Task.VISION` slot.
- **What it replaces:** a big general VLM for the narrow "image → describe-fields-in-YAML →
  extract" job. SOTA-for-its-size *claim* is unbenchmarked on the card → `needs-experiment`,
  not `confirmed`.
- **Adopt steps:**
  1. Add `Task.EXTRACTION` + `Task.VISION` to `inference/registry.py`.
  2. Register `ModelEntry(model_id="LFM2.5-VL-1.6B-Extract", lane=IGPU_ROCWMMA, …,
     task_affinity=frozenset({Task.EXTRACTION, Task.VISION}))`.
  3. **Lemonade load (if mmproj passthrough works):**
     ```bash
     lemond --port 13310 & sleep 3
     lemonade --port 13310 load LiquidAI/LFM2.5-VL-1.6B-Extract-GGUF
     # if lemonade lacks --mmproj passthrough, run llama.cpp directly:
     ~/.cache/lemonade/bin/llamacpp/vulkan/llama-mtmd-cli \
       -m LFM2.5-VL-1.6B-Extract-Q4_K_M.gguf \
       --mmproj mmproj-LFM2.5-VL-1.6B-Extract-F16.gguf --image <img> -p "<yaml fields>"
     ```
  4. **Pass-gate (Top-5 #2):** ≥ big-VLM extraction accuracy at a fraction of VRAM, temp=0,
     10-image set. Negative result → run as a `llama-mtmd` sidecar service rather than a lane.

---

## Verification ledger (honesty)

- **Verified-real (HF `model_info` or WebFetch):** A1, A2, A3, A4, A5, A6, A7, A8, A9, A10,
  A11, A12, A13, A14, A15, A16, A17, A18, A19, A20, A21, A22, A23, A24, A25, A26; C1; plus
  arXiv ids 2605.30621, 2411.15100, 2502.14969, 2512.15943, 2505.15182, 2604.03515,
  2603.05344, 2506.16655, 2505.12601, 2606.06098, 2606.06178, 2602.03478, 2601.07206,
  2403.12031, 2502.17282 (all returned in targeted searches/fetches).
- **UNVERIFIED / omitted from rows:** `unsloth/Qwen3-Embedding-0.6B-GGUF` (404),
  `bartowski/NuExtract-1.5-GGUF` (404), `lmms-lab/RouteLLM` (404 — RouteLLM is a *framework*,
  not a single HF model), `lightblue/reranker-0.5B-v2` (404), `Qwen/Qwen3-4B-Instruct-2507-GGUF`
  (404). The "Qwen3.5 / Qwen3.6" and "June-2026 SLM" mentions from web search are **directional
  only** and were NOT given rows (no verified HF id).
- **Already-integrated (so `grounded`, not `NEW`):** the harness-updating thesis (B1's source,
  arXiv:2605.30621) — vault `RETRO-2026-06-01-harness-updating-vs-benefit.md`; the
  A-Evolve mapping — `RETRO-2026-06-01c-a-evolve-framework-mapping.md`.
- **Calibrated-invariant contact:** A7/A12 (cache encoder) vs **CA1**; A26 IS CA1. CC2 (λ=100)
  is respected — every routing lever is latency/quality-recast, none defaults to cloud.

---

## Routing Principles (standing user directives, 2026-06-05)

Hard constraints governing all routing/calibration work in this repo:

1. **Quality > speed > electricity.** QUALITY/task-fitness dominates selection; latency and watts
   are **tiebreakers among equal-quality candidates, NEVER overrides**. Embodied: the task-aware
   selector ranks `(priority/fitness, then watts)`; `feynman_path_weight` makes energy/cost
   exponential penalties on a quality multiplicand. Guard: `tests/models/test_model_registry.py::
   test_quality_beats_electricity_no_watts_override`. Calibrate `LAMBDA_ENERGY`/`_LANE_WATTS`
   small enough that a better-fit heavier lane still wins. A faster/cheaper-but-worse answer is a
   regression, not an optimization.

2. **Smart-router objective = quality + electricity + cost (latency tiebreak).** On the $0 local
   fleet, dollars are uniform → electricity (watts→joules) is the real cost signal: NPU ~2 W >
   iGPU ~35 W > CPU ~55 W among equal-quality options (CC2-safe energy term in `feynman_path_weight`).

3. **Agentic, self-improving local silicon — "always working to improve itself."** The fleet is
   not a passive backend: the autoresearch + compound-engineering loops are the self-improvement
   vehicle and should run continuously on local silicon ($0), with harness-updating roles on the
   cheap tier (arXiv 2605.30621). New routing/capability gains feed BACK into those loops (task-aware
   specialists + quality-first selection make self-improvement more effective) — build the feedback,
   not a parallel daemon.
