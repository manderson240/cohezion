---
name: model-routing
description: Local LLM orchestration using Ollama with memory-aware scheduling,
  task classification, and parallel dispatch. Use when configuring model
  selection, optimizing RAM allocation for models, or when user mentions
  "model routing", "Ollama", "model selection", "memory scheduling", or
  "parallel inference".
metadata:
  version: "0.1"
  legacy-name: MODEL_ROUTING_PRIME
---

# SKILL: MODEL_ROUTING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **local LLM orchestration** using Ollama. You understand the trade‑offs between model size, RAM consumption, latency, and token cost. You can programmatically select the optimal model for a given task, spin up or shut down model servers, and route requests through a LangChain‑compatible wrapper.

## KEY TEXTS & CONCEPTS
- **Ollama Model Catalog** – `ollama list` provides name, size, and last‑modified timestamp.  
- **Memory‑aware Scheduling** – Allocate models to workers such that the total RAM usage never exceeds the available 128 GB.  
- **Task Classification** – Determine whether a request is:  
  - *Code Generation* (needs strong reasoning, e.g., `deepseek-r1:70b` or `gpt-oss:120b`)  
  - *Embedding* (lightweight, e.g., `nomic-embed-text:latest`)  
  - *Vision* (requires multimodal, e.g., `llama3.2-vision:11b-instruct-fp16`)  
  - *Fast QA / Chat* (small, low‑latency, e.g., `falcon3:7b` or `minicpm-v:8b-2.6-fp16`)  
- **Parallel Execution** – Use `concurrent.futures.ProcessPoolExecutor` to run independent model calls in separate processes, each with its own Ollama client.  
- **Cache & Deduplication** – Store recent embeddings and model outputs in `cache/` with an LRU eviction policy to avoid repeat inference.  
- **Guardrails** – Enforce timeouts, sandboxed execution, and limit external network calls to the local Ollama server only.

## INSTRUCTION
1. **Discover Available Models**  
   - Run `ollama list` (or call the Ollama HTTP `/api/tags` endpoint) to obtain a dictionary `{name: {size_gb, modified}}`.  
   - Persist this catalog in `cohezion/model/catalog.json` for quick lookup.

2. **Classify Incoming Request**  
   - Inspect the prompt for keywords (`code`, `function`, `class`, `embed`, `image`, `vision`, `fast answer`).  
   - Optionally run a lightweight classifier (e.g., a 7‑b model) to predict the required capability tier.

3. **Select Model**  
   - **Code Generation** → Prefer `gpt-oss:120b` if enough RAM (≥ 70 GB free). Else fall back to `deepseek-r1:70b` → `llama3.3:70b`.  
   - **Embedding** → Use `nomic-embed-text:latest`.  
   - **Vision** → Use `llama3.2-vision:11b-instruct-fp16`.  
   - **Fast Chat / QA** → Use `falcon3:7b` or `minicpm-v:8b-2.6-fp16`.  
   - If the selected model is not currently running, start it via `ollama serve <model>` (non‑blocking) and wait for health check.

4. **Allocate Resources**  
   - Maintain a global `available_ram_gb` counter.  
   - Before launching a model, subtract its `size_gb`. If insufficient, either:  
     a) Queue the request until memory is freed, **or**  
     b) Choose the next‑best smaller model.

5. **Execute Request**  
   - Use LangChain’s `ChatOllama(model_name=selected_model)` (or `OllamaEmbeddings` for embeddings).  
   - Set `temperature`, `max_tokens`, and a per‑call `timeout_ms` (e.g., 30 s for chat, 10 s for embeddings).  
   - Capture the raw response and any token usage metadata.

6. **Cache Results**  
   - Compute a SHA‑256 hash of the input prompt.  
   - If a cached entry exists (and is not older than a configurable TTL), return it instead of invoking the model.  
   - Store new results in `cache/<hash>.json` along with `model_name`, `timestamp`, and `usage`.

7. **Parallel Dispatch**  
   - For batch jobs (e.g., generating embeddings for 10 k documents), split the workload into chunks sized to fit RAM constraints.  
   - Launch a pool of workers, each with its own Ollama client instance, respecting the global RAM budget.  
   - Aggregate results in order and write them to the final destination (e.g., `embeddings.npy`).

8. **Error Handling & Guardrails**  
   - If a model crashes or times out, automatically retry with the next smaller fallback model.  
   - Log every event to `logs/model_routing.log` with severity, request ID, selected model, latency, and outcome.  
   - Enforce a maximum of **3 concurrent large‑model processes** (≥ 30 GB each) to keep headroom for OS and other services.

9. **Expose API**  
   - Provide a thin HTTP wrapper (`cohezion/model/router_api.py`) exposing:
     - `POST /infer` – body: `{task_type, prompt, options}` → routed response.
     - `GET /status` – returns current RAM usage, running models, queue length.
   - Use `uvicorn` with a single‑worker process; all heavy work is delegated to the pool.

10. **Self‑Improvement Loop**  
    - Periodically (e.g., nightly) run `MODEL_MANAGEMENT_RETROSPECTIVE.md` to analyze:
      - Model utilization statistics.
      - Cache hit ratio.
      - Any out‑of‑memory incidents.
    - Adjust the **model selection matrix** and **concurrency limits** accordingly, then commit updated `catalog.json` and routing heuristics.

## VERSION
v0.1

## SEE ALSO
- EMBEDDING_STRATEGY_PRIME.md
- VECTOR_STORE_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- CODE_STANDARDS_PRIME.md

## AUTO-REFINEMENT (Learning 267)
*   **Insight**: Speculative Decoding for Tool-Integrated Reasoning (TIR)
*   **Details**: Speculative Decoding (e.g., DeepSeek-R1-32B paired with Qwen2.5-1.5B drafter) provides a 1.5x-1.8x throughput multiplier. This is critical for TIR, as it allows the "Reasoning Swarm" to perform multiple code-execution and self-correction cycles within the 5-hour window. This "bought back" time is more valuable for accuracy than increasing the base model size to 70B+ which risks OOM via KV cache accumulation.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks — `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine — 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 235)
*   **Insight**: RoutingOrchestrator — Unified Entry for 4 Routing Systems (2026-04-01)
*   **Details**: Single UnifiedRoutingDecision combining SmartRouter (affinity), CostAwareRouter (complexity→model), TipOfTheSpearRouter (constitutional), DynamicModelRouter (health). Confidence flows through all routers as common signal. Lazy initialization prevents import cascades. Module: `swarm/routing_orchestrator.py`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 255)
*   **Insight**: V-JEPA 2.1 — Dense Loss Fixes Context Token Degeneracy (2026-04-02)
*   **Details**: V-JEPA 2.1 (arXiv:2603.14482): Root cause of JEPA bottleneck = loss applied only to masked regions → context tokens degenerate into global aggregators, losing spatial fidelity. Fix: dense predictive loss on BOTH masked and unmasked tokens. Also: deep self-supervision across intermediate layers. 20-point improvement in robot grasping. Directly applicable to Cohezion JEPAWorldModel.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 256)
*   **Insight**: ADRC-Lagrangian — 74% Fewer Safety Violations in Safe RL (2026-04-02)
*   **Details**: ADRC-Lagrangian (arXiv:2601.18142): Treats all uncertainty as lumped disturbance with lightweight ADRC observer. 74% fewer violations, 89% smaller constraint magnitudes. Model-free, optimizer-agnostic. Complements ManifoldEnv's physical safety (Lagrangian dynamics) with adaptive learned constraints.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 257)
*   **Insight**: Causal-JEPA — Object-Level Masking for Causal World Models (2026-04-02)
*   **Details**: Causal-JEPA (arXiv:2602.11389, code: github.com/galilai-group/cjepa): Object-level masking as latent intervention. Forces model to reason about object interactions, not just spatial patterns. 20% improvement in counterfactual reasoning, 8x faster planning (1% of tokens). 128D latent slots, single GPU training. Applicable to Cohezion JEPA: mask agent slots in multi-agent scenarios.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: K-Search Compound Loop — LLM Synthesis Works but Needs Quality (2026-04-07)
*   **Details**: The K-Search pipeline (Ollama synthesis → popcorn eval → tree learning) is operational. `deepcoder:14b` generates kernels in 60s but lacks MI355X MFMA knowledge (produces naive scalar GEMM). Cloud models (`deepseek-v3.2:cloud`) timeout on complex prompts. Key fix: use few-shot prompting with the WORKING tile32x128 kernel as an example, not zero-shot generation. Meta-prompts also had outdated instructions (subprocess/ctypes, both blocked).
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 286)
*   **Insight**: Kaggle Quota Strategy — Multi-Track Mapping (2026-04-08)
*   **Details**: Strategic mapping of Kaggle quotas is mandatory to maximize output without bottlenecks: (1) **$50/day AI Models API** is reserved for the **Measuring AGI** track (free Gemini/Claude access for cognitive tasks), (2) **30h/week GPU** is for heavy training in **BirdCLEF** and **ARC Prize**, (3) **AIMO** and **Nemotron** utilize dedicated, free sponsor hardware (H100 and G4 Blackwell). Rationale: utilizing the daily-resetting AI quota prevents wasting personal API funds.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 287)
*   **Insight**: AutoHarness Mandate — Code-as-Action-Verifier (2026-04-08)
*   **Details**: Mandate: Use **AutoHarness (arXiv:2603.03329v1)** for all agentic workflows. By automatically synthesizing deterministic code harnesses (verifiers) and policies locally using efficient models (qwen3.5:coder, phi4-mini), we eliminate "illegal action" failure modes (e.g., AIMO indexing errors or invalid ARC grid moves). At runtime, the LLM is bypassed for action validation, resulting in zero token cost and 100% logical compliance. Verified: generated AIMO modular verifier in 1 iteration.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 289)
*   **Insight**: Measuring AGI v11 — Protobuf Stability in Kaggle Notebooks
*   **Details**: Kaggle's pre-installed Google Cloud libraries are strictly pinned to older Protobuf versions. Upgrading to `protobuf==7.x` triggers massive dependency conflicts that can break the Models API. **Solution**: Pin to `protobuf==5.26.1` and `google-cloud-bigquery-storage==2.26.0` to stabilize the environment while satisfying the `kbench` SDK requirements. Result: 78 tasks successfully registered in Version 11.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 298)
*   **Insight**: Deprecated Model IDs Are Silent Failures
*   **Details**: `api_llm_executor.py` had `claude-3-5-sonnet-20241022` and `claude-3-opus-20240229` — both retired months ago. Tests passed because they don't make live API calls, but any production use would return HTTP errors. The `/anthropic-scan` system now includes model deprecation checking against `api-manifest.json` to catch these proactively. Pattern: model IDs in cost tables and defaults must be treated as **versioned dependencies** — they expire and need periodic refresh, just like package versions.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 300)
*   **Insight**: Hybrid Cloud Swarm — Context-Cost Optimization
*   **Details**: Orchestrating a hybrid swarm (Gemini 2.5 Pro/Flash + Ollama) allows for a "Context Tiering" strategy. Use Gemini 2.5 Pro (2M context) for global architectural synthesis and Flash (1M context) for high-volume cross-file implementation. Reserve local Ollama slots (limited by VRAM) for specialized math (phi4) and rapid prototyping (glm4). This configuration respects the 3-model local concurrency limit while providing the deepest possible reasoning capability.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 301)
*   **Insight**: Lemonade Embeddable — Isolated Hardware Acceleration
*   **Details**: The "Embeddable" Lemonade server allows for a zero-install, private runtime in `vendor/lemonade/`. This is superior to system-wide library replacement as it isolates optimizations (gfx1151/Strix Halo) from the host OS. Key technique: Bundle SDK libraries (`libggml-hip.so`) in the private `bin/` folder and set `LD_LIBRARY_PATH` in the spawning subprocess. Automatic lifecycle management in `ModelPoolManager` ensures the server is only active when Cohezion is running.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 267)
*   **Insight**: Speculative Decoding for Tool-Integrated Reasoning (TIR)
*   **Details**: Speculative Decoding (e.g., DeepSeek-R1-32B paired with Qwen2.5-1.5B drafter) provides a 1.5x-1.8x throughput multiplier. This is critical for TIR, as it allows the "Reasoning Swarm" to perform multiple code-execution and self-correction cycles within the 5-hour window. This "bought back" time is more valuable for accuracy than increasing the base model size to 70B+ which risks OOM via KV cache accumulation.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 160)
*   **Insight**: Skill Documentation as a Truth Anchor
*   **Details**: Skills (e.g., `DATABASE_PRIME.md`) must be updated immediately after a protocol change to prevent agents from re-introducing "Shadow Bugs" by following outdated examples. A skill is only valid if it reflects the current operational reality of the substrate.

---

## Session 72: NVIDIA Nemotron Challenge & Kaggle Infrastructure (2026-03-24, L161-L172 compressed)

Kaggle G4 Blackwell: pin CUDA 12.8 via `docker_image_pinning_type: original`, use `--no-build-isolation` for Mamba, prefer kagglehub over HF, native BF16 > bitsandbytes, target regex `in_proj|out_proj|up_proj|down_proj` for hybrid LoRA, case-sensitive `nvidiaRtxPro6000`, pre-authorize models in `model_sources`, metric uses vLLM with `\boxed{}` extraction, 5 submissions/day cap. Branch: `challenge/nvidia-nemotron-reasoning`.

Akashic Sprint Mission (2026-04-07): Implemented long-horizon task orchestration for overnight Kaggle monitoring and local model refinement. Uses `MISSION_AKASHIC_SPRINT.py` to poll Blackwell VMs and record hourly 12D snapshots in SurrealDB. Added Weighted Entropy Consensus to AIMO MRS (v40) to scale reasoning performance.


---

## Sessions 73-82: Genesis Engine + Platform Architecture (2026-03-25 to 2026-03-31, Compressed)

**L173-174 (Session 73, Enforcement):** Converted markdown rules to non-blocking hooks — `drift-detection.sh` (PreToolUse Write warns on new src/ files), `test-on-edit.sh` (PostToolUse runs matching tests), `check-bash-output.sh` (PostToolUse catches exit-0-with-errors). StrategyTracker added to RetrospectionEngine: emits "PIVOT RECOMMENDED" after 3+ attempts with <5% improvement.

**L175-189 (Session 74, Genesis Engine — 24 commits):** Mathematical core: SU(2) spinors on Bloch sphere (coherence=|Bloch vector|), Brahmagupta's zero IS HIHO (δ=0), Landau phase transitions (5 critical temps ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO), Fisher metric as Rosetta Stone (FLUME↔Riemannian↔thermodynamics), Euler-Lagrange + Störmer-Verlet, Yang-Mills SO(3), JEPA 86K-param predictor. ManifoldEnv (Gymnasium: 19D obs, 12D action), SwarmEnv (N-agent gauge coupling), TopologicalRouter (H₀/H₁ → exploit/explore/pivot), SurrealDB 3.0 syntax changes (TYPE object FLEXIBLE, port 8001). Active Inference ≡ HIHO (Friston FEP). Vertical-slice milestones > horizontal layers (skill: exemplary-deep-planning). Total artifact persistence in 6 genesis tables.

**L190-197 (Session 75, Phase 2):** 10-step cosmogony complete. Levin bioelectric gap junction percolation IS HIHO phase transition. InVEST habitat quality = HIHO proximity on semantic manifold. Causal-JEPA (object-level masking, 8x faster planning). 16 indigenous worldviews mapped to cosmogony steps. Ouroboros bridge + Mycelium wired as first-class Genesis components. EVOs physics (evolutionary dynamics on manifold curvature). Ralph Loop: 5 specialist teams, 10+ commits, 364+ genesis tests.

**L198-214 (Session 76, Architecture):** Three feedback loops: Inner (execution: Executor→SkillRefiner), Middle (knowledge: retrospect→vault→graph→skills), Outer (coordination: platform specialists). 6-protocol stack: MCP (strong: 41+ tools), A2A (in progress: zero agent cards yet), A2UI (strong: 9 components), AG-UI (strong: 15+ events). Graph HIHO metric (connectivity+reciprocity+freshness+orphan_ratio, target 0.5±0.15). Dual-format agents: CC agent def + PRIME skill for cross-platform. Background agents inherit restricted permissions (Write denied). Multi-platform: .claude/+.gemini/+.opencode/ all active. Competition licensing: MIT-0 for all. s1 budget forcing: 57% AIME with 1K examples + "Wait" tokens. AIMO3 pillars: Diverse Prompts+Entropy Voting+Speculative Decoding. AMD kernels hit API ceiling.

**L215-232 (Sessions 79-82, Wiring Sprint):** FLUME-First: encode/decode at creation, not retrofitted (3/10 systems used FLUME; 41 orphaned modules from build-then-forget anti-pattern). Cosmogonic Autonomy Tiers: ∅→HIHO maps to observe→edit→commit→deploy→sovereign. OPH Axiom 2 = HIL mechanism. Data Mesh: 17+ MCP servers = 17 typed DataProducts. A2UI data-attribute selectors most reliable Playwright selectors. LeWM 15M-param JEPA (dense loss, 2 terms, 48x faster planning). GeminiProvider: Flash-Lite(70%)/Flash(20%)/Pro(10%) cost tiers. TurboQuant: PolarQuant(2.7x) + QJL(32x, 1-bit sign). C1-C5 token pipeline: API caching(40-60%), context-window guard, cache→routing feedback, template matching(87-98%), batch dedup. Meta-Harness execution traces > prompt cramming (+7.7pts, 4x fewer tokens). LatentMAS: FLUME vectors as inter-agent comms (24x faster than text). IsoQuant SO(4) aligns with SPIN coherence.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 235)
*   **Insight**: RoutingOrchestrator — Unified Entry for 4 Routing Systems (2026-04-01)
*   **Details**: Single UnifiedRoutingDecision combining SmartRouter (affinity), CostAwareRouter (complexity→model), TipOfTheSpearRouter (constitutional), DynamicModelRouter (health). Confidence flows through all routers as common signal. Lazy initialization prevents import cascades. Module: `swarm/routing_orchestrator.py`.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 255)
*   **Insight**: V-JEPA 2.1 — Dense Loss Fixes Context Token Degeneracy (2026-04-02)
*   **Details**: V-JEPA 2.1 (arXiv:2603.14482): Root cause of JEPA bottleneck = loss applied only to masked regions → context tokens degenerate into global aggregators, losing spatial fidelity. Fix: dense predictive loss on BOTH masked and unmasked tokens. Also: deep self-supervision across intermediate layers. 20-point improvement in robot grasping. Directly applicable to Cohezion JEPAWorldModel.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 256)
*   **Insight**: ADRC-Lagrangian — 74% Fewer Safety Violations in Safe RL (2026-04-02)
*   **Details**: ADRC-Lagrangian (arXiv:2601.18142): Treats all uncertainty as lumped disturbance with lightweight ADRC observer. 74% fewer violations, 89% smaller constraint magnitudes. Model-free, optimizer-agnostic. Complements ManifoldEnv's physical safety (Lagrangian dynamics) with adaptive learned constraints.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 257)
*   **Insight**: Causal-JEPA — Object-Level Masking for Causal World Models (2026-04-02)
*   **Details**: Causal-JEPA (arXiv:2602.11389, code: github.com/galilai-group/cjepa): Object-level masking as latent intervention. Forces model to reason about object interactions, not just spatial patterns. 20% improvement in counterfactual reasoning, 8x faster planning (1% of tokens). 128D latent slots, single GPU training. Applicable to Cohezion JEPA: mask agent slots in multi-agent scenarios.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 268)
*   **Insight**: K-Search Compound Loop — LLM Synthesis Works but Needs Quality (2026-04-07)
*   **Details**: The K-Search pipeline (Ollama synthesis → popcorn eval → tree learning) is operational. `deepcoder:14b` generates kernels in 60s but lacks MI355X MFMA knowledge (produces naive scalar GEMM). Cloud models (`deepseek-v3.2:cloud`) timeout on complex prompts. Key fix: use few-shot prompting with the WORKING tile32x128 kernel as an example, not zero-shot generation. Meta-prompts also had outdated instructions (subprocess/ctypes, both blocked).
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 286)
*   **Insight**: Kaggle Quota Strategy — Multi-Track Mapping (2026-04-08)
*   **Details**: Strategic mapping of Kaggle quotas is mandatory to maximize output without bottlenecks: (1) **$50/day AI Models API** is reserved for the **Measuring AGI** track (free Gemini/Claude access for cognitive tasks), (2) **30h/week GPU** is for heavy training in **BirdCLEF** and **ARC Prize**, (3) **AIMO** and **Nemotron** utilize dedicated, free sponsor hardware (H100 and G4 Blackwell). Rationale: utilizing the daily-resetting AI quota prevents wasting personal API funds.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 287)
*   **Insight**: AutoHarness Mandate — Code-as-Action-Verifier (2026-04-08)
*   **Details**: Mandate: Use **AutoHarness (arXiv:2603.03329v1)** for all agentic workflows. By automatically synthesizing deterministic code harnesses (verifiers) and policies locally using efficient models (qwen3.5:coder, phi4-mini), we eliminate "illegal action" failure modes (e.g., AIMO indexing errors or invalid ARC grid moves). At runtime, the LLM is bypassed for action validation, resulting in zero token cost and 100% logical compliance. Verified: generated AIMO modular verifier in 1 iteration.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 289)
*   **Insight**: Measuring AGI v11 — Protobuf Stability in Kaggle Notebooks
*   **Details**: Kaggle's pre-installed Google Cloud libraries are strictly pinned to older Protobuf versions. Upgrading to `protobuf==7.x` triggers massive dependency conflicts that can break the Models API. **Solution**: Pin to `protobuf==5.26.1` and `google-cloud-bigquery-storage==2.26.0` to stabilize the environment while satisfying the `kbench` SDK requirements. Result: 78 tasks successfully registered in Version 11.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 298)
*   **Insight**: Deprecated Model IDs Are Silent Failures
*   **Details**: `api_llm_executor.py` had `claude-3-5-sonnet-20241022` and `claude-3-opus-20240229` — both retired months ago. Tests passed because they don't make live API calls, but any production use would return HTTP errors. The `/anthropic-scan` system now includes model deprecation checking against `api-manifest.json` to catch these proactively. Pattern: model IDs in cost tables and defaults must be treated as **versioned dependencies** — they expire and need periodic refresh, just like package versions.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 300)
*   **Insight**: Hybrid Cloud Swarm — Context-Cost Optimization
*   **Details**: Orchestrating a hybrid swarm (Gemini 2.5 Pro/Flash + Ollama) allows for a "Context Tiering" strategy. Use Gemini 2.5 Pro (2M context) for global architectural synthesis and Flash (1M context) for high-volume cross-file implementation. Reserve local Ollama slots (limited by VRAM) for specialized math (phi4) and rapid prototyping (glm4). This configuration respects the 3-model local concurrency limit while providing the deepest possible reasoning capability.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 301)
*   **Insight**: Lemonade Embeddable — Isolated Hardware Acceleration
*   **Details**: The "Embeddable" Lemonade server allows for a zero-install, private runtime in `vendor/lemonade/`. This is superior to system-wide library replacement as it isolates optimizations (gfx1151/Strix Halo) from the host OS. Key technique: Bundle SDK libraries (`libggml-hip.so`) in the private `bin/` folder and set `LD_LIBRARY_PATH` in the spawning subprocess. Automatic lifecycle management in `ModelPoolManager` ensures the server is only active when Cohezion is running.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 308)
*   **Insight**: 4-Layer Compute Fabric — Lemonade-First + Ollama Pro Cloud
*   **Details**: Orchestration (Claude Max 20x + Gemini Pro CLI) sits ABOVE the inference layer. Inference: Lemonade local ($0, 105+ models, gfx1151-optimized across CPU/NPU/GPU) + Ollama Pro cloud ($20/mo, 20+ frontier models via :cloud suffix, 3 slots — 2 Cohezion + 1 Pi). CostAwareRouter manages inference only; orchestration is subscription-based. Quarter-on-a-String Protocol: maximize capability, minimize marginal cost.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 307)
*   **Insight**: FLUME-Aware UCB1 — Manifold Navigation
*   **Details**: Standard UCB1 exploration is enhanced by FLUME latent distance. Instead of selecting nodes by index, the system selects by latent similarity to previous "Wins." This allows the agent to navigate the 256D thought-space toward successful reasoning patterns (e.g., "Invariant-Aware Proofs") while maintaining HIHO stability (0.5 coherence) to avoid reasoning decay in long-horizon missions.

## Session 99: Systems Engineering V-Model & Autoresearch (2026-04-10)
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 310)
*   **Insight**: Systems Engineering V-Model for AI Swarms
*   **Details**: To prevent agentic loops from devolving into non-deterministic chaos, we map the swarm directly onto the Systems Engineering V-Model. Each specialist agent occupies a strict stage (e.g., Requirements, Architecture, Implementation, Validation). The 'AutoHarness Mandate' requires all non-deterministic actions to be wrapped in deterministic test harnesses. Successful patterns are then distilled into Python policies, replacing LLM inference with zero-cost code.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 320)
*   **Insight**: V-Model Agentic Orchestration — The Axiomatic Gate
*   **Details**: Integrating the Systems Engineering V-Model into agentic workflows provides a recursive "Proposal/Disposal" architecture. The descending path (Latent) decomposes user intent into architectural requirements and deterministic AutoHarnesses. The ascending path (Axiomatic) verifies code against those harnesses and validates it via Adversarial Swarm Review. This "Apex Integration" ensures that no nondeterministic LLM output can mutate system state without passing a 100% predictable logical gate.
*   **Date**: 2026-04-11


## AUTO-REFINEMENT (Learning 323)
*   **Insight**: FLUME-Aware UCB1 — Manifold Navigation
*   **Details**: Standard UCB1 exploration is enhanced by FLUME latent distance. Instead of selecting nodes by index, the system selects by latent similarity to previous "Wins." This allows the agent to navigate the 256D thought-space toward successful reasoning patterns (e.g., "Invariant-Aware Proofs") while maintaining HIHO stability (0.5 coherence) to avoid reasoning decay in long-horizon missions.

## Session 99: Systems Engineering V-Model & Autoresearch (2026-04-10)
*   **Date**: 2026-04-11
